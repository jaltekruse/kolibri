#!/usr/bin/env node
// Line-based browser driver for a running Kolibri dev server, built on playwright-core.
// Reads one command per line from stdin (pipe a heredoc, or run under tmux for a REPL).
// See SKILL.md for the command list. Piped scripts stop at the first failing command.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';

const RUN_DIR = process.env.RUN_DIR || '/tmp/kolibri-run';
const BASE = process.env.KOLIBRI_URL || 'http://127.0.0.1:8000';
const SHOTS = path.join(RUN_DIR, 'shots');
const require = createRequire(path.join(RUN_DIR, 'pw', 'package.json'));
const { chromium } = require('playwright-core');

fs.mkdirSync(SHOTS, { recursive: true });
const interactive = process.stdin.isTTY;
const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
let errors = [];
page.on('console', msg => msg.type() === 'error' && errors.push(msg.text()));
page.on('pageerror', err => errors.push(`pageerror: ${err.message}`));
page.on('response', r => r.status() >= 500 && errors.push(`HTTP ${r.status()} ${r.url()}`));
// Commands like click/fill look inside this element when set (see `scope`)
let scope = null;

const root = () => scope || page;
// "a\nb" in a script line becomes a real line break
const unescape = text => text.replace(/\\n/g, '\n');
// "Name = value" -> ["Name", "value"]
const splitPair = rest => {
  const i = rest.indexOf(' = ');
  if (i === -1) throw new Error('expected "<name> = <value>"');
  return [rest.slice(0, i), unescape(rest.slice(i + 3))];
};
// "button Save" -> getByRole('button', { name: 'Save', exact: true });
// "link ~Save" matches names containing "Save" (card links carry more than their title)
const byRole = rest => {
  const [role, ...words] = rest.split(' ');
  const name = words.join(' ');
  const exact = !name.startsWith('~');
  return root()
    .getByRole(role, { name: exact ? name : name.slice(1), exact })
    .first();
};

async function login(username, password = '') {
  // Sign out whoever is signed in, or the sign-in page redirects straight to their app
  await page.context().clearCookies();
  await page.goto(`${BASE}/en/auth/#/signin`, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Username').fill(username);
  await page.getByRole('button', { name: /Next|Sign in/ }).click();
  const signedIn = page.waitForURL(url => !url.toString().includes('/auth/'), {
    timeout: 60000,
  });
  // Learners in the seeded (formal) facility sign in without a password
  const passwordBox = page.getByLabel('Password');
  const needsPassword = await Promise.race([
    passwordBox.waitFor({ timeout: 15000 }).then(() => true),
    signedIn.then(() => false),
  ]).catch(() => false);
  if (needsPassword) {
    await passwordBox.fill(password);
    await page.getByRole('button', { name: /Sign in/ }).click();
  }
  await signedIn;
  if (page.url().includes('/learn')) {
    // A learner's first visit opens a "Welcome to Kolibri!" modal that blocks clicks
    const welcome = page.getByRole('button', { name: 'Continue' });
    if (await welcome.waitFor({ timeout: 10000 }).then(() => true, () => false)) {
      await welcome.click();
    }
  }
}

const commands = {
  // login <username> [password]
  login: rest => login(...rest.split(' ')),
  // nav <path>, e.g. nav /en/coach/#/<class_id>/lessons/<lesson_id>
  nav: rest => page.goto(`${BASE}${rest}`, { waitUntil: 'domcontentloaded' }),
  // click <role> <accessible name>, e.g. click button Save
  click: rest => byRole(rest).click({ timeout: 30000 }),
  // click-text <visible text>, for links/buttons without a usable role
  'click-text': rest =>
    root().getByText(rest, { exact: true }).filter({ visible: true }).first().click(),
  // fill <textbox accessible name> = <text>   (\n for line breaks)
  fill: rest => {
    const [name, value] = splitPair(rest);
    return root().getByRole('textbox', { name, exact: true }).first().fill(value);
  },
  // wait <visible text>
  wait: rest => root().getByText(rest).first().waitFor({ timeout: 90000 }),
  // wait-role <role> <accessible name>
  'wait-role': rest => byRole(rest).waitFor({ timeout: 90000 }),
  // scope <data-testid> | scope -   (narrow click/fill/wait to an element, or reset)
  scope: rest => {
    scope = rest === '-' ? null : page.getByTestId(rest).first();
  },
  // scope-role <role> [name]   (e.g. scope-role dialog, to act inside an open modal)
  'scope-role': rest => {
    scope = rest.includes(' ') ? byRole(rest) : page.getByRole(rest).first();
  },
  // scope-text <text>   (narrow to the innermost [data-testid] element containing this text)
  'scope-text': rest => {
    scope = page.locator('[data-testid]').filter({ hasText: rest }).last();
  },
  // frame <iframe title>   (act inside an iframe, e.g. the Free Math editor; scope - to leave)
  frame: rest => {
    scope = page.frameLocator(`iframe[title="${rest}"]`);
  },
  // dismiss   (closes a modal if one opens within 10s, like "Resource completed")
  dismiss: async () => {
    const dialog = page.getByRole('dialog').first();
    if (await dialog.waitFor({ timeout: 10000 }).then(() => true, () => false)) {
      await dialog.getByRole('button', { name: 'Close', exact: true }).first().click();
      await dialog.waitFor({ state: 'detached', timeout: 10000 });
    }
  },
  // click-css <css selector>   (for elements with no role, like a math field)
  'click-css': rest => root().locator(rest).first().click({ timeout: 30000 }),
  // type <text>   (types into whatever has focus; \n presses Enter)
  type: rest => page.keyboard.type(unescape(rest), { delay: 30 }),
  // press <key>   (e.g. press Enter, press Tab)
  press: rest => page.keyboard.press(rest),
  // value <textbox accessible name>   (print what a textbox holds)
  value: async rest =>
    console.log(JSON.stringify(await root().getByRole('textbox', { name: rest }).first().inputValue())),
  // text <data-testid>   (print an element's text)
  text: async rest => console.log(JSON.stringify(await page.getByTestId(rest).first().innerText())),
  // ss <name>   (full-page screenshot to $RUN_DIR/shots/<name>.png)
  ss: async rest => {
    await page.waitForTimeout(800);
    const file = path.join(SHOTS, `${rest || 'screenshot'}.png`);
    await page.screenshot({ path: file, fullPage: true });
    console.log(file);
  },
  // viewport <width> <height>
  viewport: rest => {
    const [width, height] = rest.split(' ').map(Number);
    return page.setViewportSize({ width, height });
  },
  reload: () => page.reload({ waitUntil: 'domcontentloaded' }),
  url: () => console.log(page.url()),
  // eval <js expression>
  eval: async rest => console.log(JSON.stringify(await page.evaluate(rest))),
  // errors   (console errors, page errors and 5xx responses since the last call)
  errors: () => {
    console.log(errors.length ? errors.join('\n') : 'no errors');
    errors = [];
  },
  sleep: rest => page.waitForTimeout(Number(rest)),
};

let failed = false;
const rl = readline.createInterface({ input: process.stdin, terminal: false });
if (interactive) process.stdout.write('ready> ');
for await (const raw of rl) {
  const line = raw.trim();
  if (!line || line.startsWith('#')) continue;
  if (line === 'quit') break;
  const [name] = line.split(' ', 1);
  const rest = line.slice(name.length + 1);
  // The terminal already echoes commands typed into the REPL
  if (!interactive) console.log(`> ${line}`);
  try {
    if (!commands[name]) throw new Error(`unknown command: ${name}`);
    await commands[name](rest);
  } catch (error) {
    failed = true;
    console.log(`ERROR: ${error.message.split('\n').slice(0, 4).join(' | ')}`);
    await page.screenshot({ path: path.join(SHOTS, 'error.png'), fullPage: true }).catch(() => {});
    console.log(`screenshot of failure: ${path.join(SHOTS, 'error.png')}`);
    if (!interactive) break;
  }
  if (interactive) process.stdout.write('ready> ');
}
await browser.close();
process.exit(failed ? 1 : 0);
