---
name: run-kolibri
description: Build, run, and drive the Kolibri dev server (Django + webpack) in a headless container. Use when asked to start or run Kolibri, try a change in the running app, click through it as a coach or learner, take screenshots of its UI, seed dev data, or run its tests.
---

Start Kolibri's dev server in tmux, seed it with a class, users and a local PDF lesson
(`seed.py`, no Studio needed), then drive it in headless Chromium with
`.claude/skills/run-kolibri/driver.mjs`, which reads one command per line from stdin.
Learners answer lesson questions in the Free Math editor, a separate app that the
`lesson_responses` plugin serves in an iframe once it has been built and copied in.

All paths are relative to the repo root. Everything the run creates (Kolibri home,
logs, screenshots, the Playwright install) goes under `$RUN_DIR`.

## Prerequisites

Python deps via `uv`, Node 22 + `pnpm`, `tmux`, `git-lfs`, and a Chromium for Playwright
(preinstalled at `/opt/pw-browsers` in Claude cloud containers; `PLAYWRIGHT_BROWSERS_PATH`
already points there).

## Setup

```bash
uv sync --group dev --all-packages
pnpm install --frozen-lockfile        # fails behind some proxies: see Troubleshooting
git lfs pull --include="kolibri/plugins/qti_viewer/frontend/components/__fixtures__/*"

export RUN_DIR=/tmp/kolibri-run
mkdir -p "$RUN_DIR/pw" && (cd "$RUN_DIR/pw" && npm init -y >/dev/null \
  && PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm install --no-audit --no-fund playwright-core@1.56.1)
```

`playwright-core@1.56.1` matches the preinstalled `chromium-1194`; it lives outside the
repo so it never touches the pnpm workspace.

Build Free Math (about two minutes) and copy it into the plugin's git-ignored static files.
Without this the questions panel shows an empty frame and
`/en/lesson_responses/free_math/` answers 404:

```bash
git clone -b claude/charming-mayer-nke2fo https://github.com/jaltekruse/free-math2 "$RUN_DIR/free-math"
(cd "$RUN_DIR/free-math/frontend" && npm ci --ignore-scripts \
  && PUBLIC_URL=. GENERATE_SOURCEMAP=false CI=false npx react-scripts build)
.venv/bin/python kolibri/plugins/lesson_responses/vendor_free_math.py "$RUN_DIR/free-math/frontend/build"
```

`--ignore-scripts` skips building the native `canvas` package, which only Free Math's
own tests use. Re-run the last two commands after changing Free Math; the dev server
picks up the new files without a restart.

## Database and dev data

Every shell that runs `kolibri` needs this environment:

```bash
export RUN_DIR=/tmp/kolibri-run KOLIBRI_HOME=/tmp/kolibri-run/home KOLIBRI_RUN_MODE=dev
export PATH="$PWD/.venv/bin:$PATH" DJANGO_SETTINGS=kolibri.deployment.default.settings.dev
```

Then migrate, provision the device and seed (about a minute on a fresh home):

```bash
kolibri manage migrate --settings=$DJANGO_SETTINGS
kolibri manage provisiondevice --settings=$DJANGO_SETTINGS -- \
  --facility "Riverside School" --superusername admin --superuserpassword admin \
  --preset formal --language_id en --noinput
kolibri manage shell --settings=$DJANGO_SETTINGS -- \
  -c "exec(open('.claude/skills/run-kolibri/seed.py').read())" 2>/dev/null \
  | grep '^{' | tee "$RUN_DIR/ids.json"
```

Seeded users: `admin`/`admin` (superuser), `coach`/`coach` (coach of "Biology 101"),
learners `ada` and `grace` (no password needed). `ids.json` holds `class_id`,
`lesson_id`, `contentnode_id` and `content_id` of the "Photosynthesis" lesson's PDF.
Re-running `seed.py` only prints the ids.

## Run the server

```bash
tmux new-session -d -s kolibri "cd $PWD && export KOLIBRI_HOME=$KOLIBRI_HOME KOLIBRI_RUN_MODE=dev PATH=$PATH && pnpm devserver 2>&1 | tee $RUN_DIR/devserver.log"
timeout 600 bash -c 'until curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ | grep -q 302; do sleep 5; done'
timeout 600 bash -c "until grep -q \"Completed 'kolibri.plugins.coach.app'\" $RUN_DIR/devserver.log; do sleep 5; done"
```

Django serves on `:8000` and auto-reloads Python changes. The webpack watcher rebuilds a
changed frontend file in about 15 seconds; the first full build takes about a minute.

## Drive it (agent path)

Pipe commands to the driver. This one is a complete walkthrough of lesson questions
(the `lesson_responses` plugin): the coach writes two questions, a learner shows their
work in Free Math and submits it, and the coach grades it in Free Math's class view:

```bash
eval "$(python3 -c "import json; d=json.load(open('$RUN_DIR/ids.json')); print(' '.join(f'{k.upper()}={v}' for k, v in d.items()))")"
node .claude/skills/run-kolibri/driver.mjs <<EOF
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
wait Photosynthesis reading
click button Questions (0)
fill Question 1 = Solve 2x + 4 = 10 for x.
click button Add question
fill Question 2 = Simplify 3(x + 2) - x.
click button Save
wait-role button Questions (2)
ss coach-questions
login ada
nav /en/learn/#/home/classes/$CLASS_ID/lesson/$LESSON_ID
click link ~Photosynthesis reading
wait-role heading Questions
dismiss
frame Math editor for your answers
wait Problem 1
click-css .mq-editable-field
type 2x+4=10
press Shift+Enter
sleep 500
type 2x=6
press Shift+Enter
sleep 500
type x=3
click button Problem 2
wait Simplify
click-css .mq-editable-field
type 3x+6-x
scope -
wait Answers saved
ss learner-work
click button Submit answers
scope-role dialog
click button Submit answers
scope -
text submitted-status
ss learner-submitted
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
click link ~Photosynthesis reading
wait-role heading Learner answers
frame Math editor for grading learner answers
wait Problem 1
click-css .problem-grade-input
type 5
click-css textarea
type Check your last step.
wait All grades saved
scope -
ss coach-graded
login ada
nav /en/learn/#/home/classes/$CLASS_ID/lesson/$LESSON_ID
click link ~Photosynthesis reading
frame Math editor for your answers
wait Check your last step.
scope -
ss learner-graded
errors
EOF
```

A lesson can also hold **web pages**: a page from another website shown next to Free
Math, with problems numbered as the coach lists them (`21-27 by 3` is 21, 24 and 27).
Cloud containers cannot reach real websites, so serve a stand-in page from a second
local port, which the browser treats as another site:

```bash
mkdir -p "$RUN_DIR/site" && printf '%s\n' '<!doctype html><title>Practice</title>' \
  '<h1>Two-step equations</h1><ol start="21"><li>2x + 4 = 10</li><li>3x - 5 = 7</li>' \
  '<li>5x + 1 = 16</li><li>4x - 8 = 0</li></ol>' > "$RUN_DIR/site/practice.html"
tmux new-session -d -s site "cd $RUN_DIR/site && python3 -m http.server 8090 --bind 127.0.0.1"
node .claude/skills/run-kolibri/driver.mjs <<EOF
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
wait-role heading Web pages
click button Add web page
scope-role dialog
fill Title = Two-step equations practice
fill Web address = http://127.0.0.1:8090/practice.html
fill Instructions = Solve every third problem, starting at 21.
fill Problem numbers = 21-27 by 3
click button Save
scope -
wait-role link Two-step equations practice
login grace
nav /en/learn/#/home/classes/$CLASS_ID/lesson/$LESSON_ID
click link Two-step equations practice
frame Two-step equations practice
wait 2x + 4 = 10
scope -
frame Math editor for your answers
wait Problem 21
click-css .mq-editable-field
type x=3
scope -
wait Answers saved
ss learner-web-page
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
click link Two-step equations practice
frame Math editor for grading learner answers
wait Problem 21
scope -
ss coach-web-page-report
errors
EOF
tmux kill-session -t site
```

Screenshots land in `$RUN_DIR/shots/<name>.png` (the driver prints each path); a failing
command saves `$RUN_DIR/shots/error.png` and, when piped, stops the script with exit
code 1. Look at the screenshots - a page can render its shell while every request fails.

| command | what it does |
|---|---|
| `login <user> [password]` | Signs out, then signs in through the real sign-in page; handles password-less learners and dismisses the first-visit welcome modal |
| `nav <path>` | Opens `http://127.0.0.1:8000<path>` (hash routes like `/en/coach/#/...`) |
| `click <role> <name>` | Clicks the first element with that ARIA role and exact accessible name; `~<text>` matches names containing it |
| `click-text <text>` | Clicks visible text, for elements with no usable role |
| `fill <textbox name> = <text>` | Fills a textbox by accessible name; `\n` becomes a line break |
| `wait <text>` / `wait-role <role> <name>` | Waits up to 90s for it to appear |
| `scope-role <role> [name]` / `scope-text <text>` / `scope <data-testid>` / `scope -` | Narrows click/fill/wait to an element (`scope-role dialog` for a modal; `scope-text` picks the innermost `[data-testid]` element containing the text, e.g. one learner's card), or resets |
| `frame <iframe title>` | Narrows click/fill/wait to the page inside an iframe, e.g. `frame Math editor for your answers`; `scope -` leaves it |
| `click-css <selector>` | Clicks the first element matching a CSS selector, for elements with no role, like Free Math's `.mq-editable-field` |
| `type <text>` / `press <key>` | Types into whatever has focus / presses a key such as `Shift+Enter` |
| `dismiss` | Clicks Close on a modal if one opens within 10 seconds, like "Resource completed" |
| `text <data-testid>` / `value <textbox name>` | Prints an element's text / a textbox's value |
| `ss <name>` | Full-page screenshot |
| `viewport <w> <h>` | Resizes, e.g. `viewport 390 844` for a phone |
| `reload`, `url`, `eval <js>`, `sleep <ms>` | As named |
| `errors` | Console errors, page errors and 5xx responses since the last call |

For a REPL, run the driver in tmux and send one command at a time. A bare `ready>` as
the last line means the previous command finished:

```bash
tmux new-session -d -s drv "RUN_DIR=$RUN_DIR node .claude/skills/run-kolibri/driver.mjs"
timeout 60 bash -c 'until tmux capture-pane -t drv -p | grep -q "ready>"; do sleep 0.5; done'
drv() {
  tmux send-keys -t drv "$1" Enter
  timeout 120 bash -c 'until tmux capture-pane -t drv -p | grep -v "^\s*$" | tail -1 | grep -qE "^ready> ?$"; do sleep 0.5; done'
  tmux capture-pane -t drv -p | grep -v '^\s*$' | tail -4
}
drv 'login admin admin'
drv 'url'
tmux kill-session -t drv
```

## Stop

```bash
tmux kill-session -t kolibri
kolibri stop        # the Django server outlives the tmux session; this stops it
```

## Test

```bash
pytest kolibri/plugins/lesson_responses kolibri/core/lessons -p no:cacheprovider -q
pnpm test-jest kolibri/plugins/learn kolibri/plugins/coach
prek run --files $(git diff --name-only HEAD)   # lint what you changed; never --all-files
```

## Gotchas

- **Free Math lives in an iframe** and talks to the Kolibri page with `postMessage`
  (protocol in Free Math's `src/Embedded.js`). Use `frame` to act inside it; `errors`
  includes errors from inside the frame.
- **Typing into Free Math's math fields**: click the field, then `type`. `Shift+Enter`
  adds a blank step and focuses it a moment later, so `sleep 500` before typing again or
  the keys land in the old step. `Control+a` does not select a whole math field.
- **Lesson web pages are framed from other websites**, which may refuse it (with
  `X-Frame-Options` or CSP `frame-ancestors`); the frame then shows the browser's error
  and learners use "Open page in a new tab". The `frame <page title>` command reaches
  into it only while it loads.
- **A learner's first view of the seeded one-page PDF opens "Resource completed"**, a
  modal over the questions panel, a few seconds after load. `dismiss` closes it.

- **`page.goto` never reaches `load`** - some asset request on Kolibri pages never
  settles in headless Chromium. The driver navigates with `waitUntil: 'domcontentloaded'`
  and then waits for an element; do the same in any new script.
- **The webpack error overlay covers the whole page** and swallows every click while
  any bundle fails to compile. The QTI viewer's `__fixtures__` are Git LFS files; without
  the `git lfs pull` above they are pointer stubs and the overlay never goes away.
  `grep "ERROR in" $RUN_DIR/devserver.log` shows what is failing.
- **Dev mode validates API output against serializers** (`DEBUG`); a field a serializer
  doesn't declare turns into a 500 with `OutputValidationError` in the server log, even
  though production would serve it. Check `errors` after every flow.
- **Learners in a formal facility sign in with no password**; the sign-in page goes
  straight from username to the app. `login` handles both cases.
- **First learner visit opens a "Welcome to Kolibri!" modal** over the home page, a few
  seconds after load. `login` waits for it and clicks Continue.
- **Card titles have a `visuallyhidden` duplicate** that Playwright treats as visible, so
  text locators resolve to the hidden span and never become clickable. Click cards by
  role, matching part of the name: `click link ~<title>`.
- **KDS tooltips can cover their own button.** A `KIconButton` with `:tooltip` in a table
  row showed its tooltip over the button on hover, so the click never landed.
- **`KButton appearance="basic-link"` renders an `<a>` with no `href`**, which has no
  button role: `click button ...` cannot find it. Flat buttons are real buttons.
- **`errors` always shows some noise**: a `400` from `/api/auth/session/` (the app checks
  for a session before sign-in) and `objectSpecs` "Must be either required or have a
  default" warnings from the learner lesson card, and on coach lesson pages
  `[vuex] unknown local action type: fetchLessonsSizes`. Look for anything beyond those.
- **The sign-in page redirects a signed-in user** straight back to their app, so a second
  `login` would never find the username box. `login` clears cookies first.
- **No Studio access** - content import from Studio is blocked here, so `seed.py` writes a
  PDF into content storage and creates the channel rows directly.

## Troubleshooting

- **`pnpm install` fails with `ERR_PNPM_FETCH_403` for
  `codeload.github.com/learningequality/aphrodite`**: the session's GitHub policy refuses
  tarball downloads of repos not attached to the session (KDS depends on this fork). Plain
  `git` reads still work, so build the identical tarball locally, point that one lockfile
  line at it, install, and restore the lockfile:

  ```bash
  SHA=fdc8d7be8912a5cf17f74ff10f124013c52c3e32
  git clone --depth 1 https://github.com/learningequality/aphrodite "$RUN_DIR/aphrodite"
  git -C "$RUN_DIR/aphrodite" fetch --depth 1 origin $SHA && git -C "$RUN_DIR/aphrodite" checkout -q $SHA
  git -C "$RUN_DIR/aphrodite" archive --format=tar.gz --prefix=aphrodite-$SHA/ HEAD > "$RUN_DIR/aphrodite.tgz"
  sed -i "s#    resolution: {tarball: https://codeload.github.com/learningequality/aphrodite/tar.gz/$SHA}#    resolution: {tarball: file:$RUN_DIR/aphrodite.tgz}#" pnpm-lock.yaml
  pnpm install --frozen-lockfile && git checkout -- pnpm-lock.yaml
  ```
- **`GET /` returns 500, log says `no such table: silk_request`**: the database was
  migrated without the dev settings, which add Django Silk. Run the `migrate` command
  above with `--settings=$DJANGO_SETTINGS`.
- **`GET /` redirects to `/en/setup/`**: the device isn't provisioned. Note the `--`
  before `provisiondevice`'s own options.
- **`WebpackError: Error accessing stats file '...main_stats.json'`** in the server log
  right after startup: the webpack watcher hasn't finished its first build. Wait for the
  coach bundle as above.
- **Port 8000 still answers after `tmux kill-session`**: the Django server keeps running;
  `kolibri stop` (with the same `KOLIBRI_HOME`) stops it.
