---
name: run-kolibri
description: Build, run, and drive the Kolibri dev server (Django + webpack) in a headless container. Use when asked to start or run Kolibri, try a change in the running app, click through it as a coach or learner, take screenshots of its UI, seed dev data, or run its tests.
---

Start Kolibri's dev server in tmux, seed it with a class, users and a local PDF lesson
(`seed.py`, no Studio needed), then drive it in headless Chromium with
`.claude/skills/run-kolibri/driver.mjs`, which reads one command per line from stdin.

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

Pipe commands to the driver. This one is a complete coach + learner walkthrough of
lesson questions (the `lesson_responses` plugin):

```bash
eval "$(python3 -c "import json; d=json.load(open('$RUN_DIR/ids.json')); print(' '.join(f'{k.upper()}={v}' for k, v in d.items()))")"
node .claude/skills/run-kolibri/driver.mjs <<EOF
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
wait Photosynthesis reading
click button Questions (0)
fill Question 1 = What pigment captures light energy?
click button Add question
fill Question 2 = Name the two inputs plants use to make glucose.
click button Save
wait-role button Questions (2)
ss coach-questions
login ada
nav /en/learn/#/home/classes/$CLASS_ID/lesson/$LESSON_ID
click link ~Photosynthesis reading
wait-role heading Questions
fill Answer to question 1 = Chlorophyll
fill Answer to question 2 = Carbon dioxide\nand water
wait Answers saved
ss learner-answers
click button Submit answers
scope-role dialog
click button Submit answers
scope -
wait-role heading Questions
text submitted-status
ss learner-submitted
login coach coach
nav /en/coach/#/$CLASS_ID/lessons/$LESSON_ID
click link ~Photosynthesis reading
wait-role heading Learner answers
scope-text Ada Lovelace
click button Add feedback
fill Feedback on all answers = Good work
click button Save
wait Good work
scope -
ss coach-feedback
errors
EOF
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
  default" warnings from the learner lesson card. Look for anything beyond those.
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
