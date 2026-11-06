"""
Copy a Free Math build into this plugin's static files, for the math editor that
learners answer lesson questions in and coaches grade with.

Free Math (https://github.com/jaltekruse/free-math2, GPLv3) is a separate React app;
its embedded mode is on the claude/charming-mayer-nke2fo branch for now. Build it with
a relative public URL, then point this script at the build folder:

    cd free-math2/frontend
    npm ci --ignore-scripts
    PUBLIC_URL=. GENERATE_SOURCEMAP=false CI=false npx react-scripts build
    python kolibri/plugins/lesson_responses/vendor_free_math.py free-math2/frontend/build

Only the files the editor loads are copied. Its index.html becomes embed.html, without
the Google Analytics and Google API scripts: Kolibri runs offline and its Content
Security Policy blocks inline and third party scripts.
"""

import argparse
import os
import re
import shutil
import sys

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(PLUGIN_DIR, "static", "lesson_responses", "free_math")

# Paths relative to the build folder, files or whole folders
INCLUDED_PATHS = (
    "static",
    "lib/jquery.js",
    "lib/underscore.js",
    "lib/kas.js",
    "lib/i18n.js",
    "lib/mathjax",
    "lib/cropper.min.css",
    "lib/tui-image-editor.min.css",
    "lib/tui-color-picker.min.css",
    "expect.min.js",
    "katexA11.js",
    "kas.min.js",
    "katex.min.css",
    "katex.min.js",
    "build/mathquill_2199664.css",
    "build/mathquill_2199664.min.js",
    "build/font",
    "build/fonts",
    "fonts",
    "images",
    "Symbola.ttf",
    "Symbola.woff",
    "Symbola.woff2",
    "acknowledgements.html",
)

INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>.*?</script>", re.DOTALL)
REMOTE_SCRIPT = re.compile(r"<script[^>]*\bsrc=\"https?://[^\"]*\"[^>]*>\s*</script>")
REMOTE_LINK = re.compile(r"<link[^>]*\bhref=\"https?://[^\"]*\"[^>]*>")


def make_embed_html(index_html):
    html = INLINE_SCRIPT.sub("", index_html)
    html = REMOTE_SCRIPT.sub("", html)
    html = REMOTE_LINK.sub("", html)
    if re.search(r"(src|href)=\"https?://", html) or INLINE_SCRIPT.search(html):
        raise ValueError(
            "index.html still loads remote or inline scripts, update vendor_free_math.py"
        )
    return html


def vendor(build_dir):
    with open(os.path.join(build_dir, "index.html"), encoding="utf-8") as f:
        embed_html = make_embed_html(f.read())
    if os.path.exists(TARGET_DIR):
        shutil.rmtree(TARGET_DIR)
    for relative_path in INCLUDED_PATHS:
        source = os.path.join(build_dir, relative_path)
        target = os.path.join(TARGET_DIR, relative_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.isdir(source):
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    with open(os.path.join(TARGET_DIR, "embed.html"), "w", encoding="utf-8") as f:
        f.write(embed_html)


def main():
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("build_dir", help="Free Math's frontend/build folder")
    args = parser.parse_args()
    vendor(args.build_dir)
    sys.stdout.write(f"Copied Free Math to {TARGET_DIR}\n")


if __name__ == "__main__":
    main()
