#!/usr/bin/env python3
"""Re-inline the landing photo-stack images into index.html.

The three overlapping photos beside "Where every project stands" are served
as base64 data URIs so the landing page paints without a network round trip
and without a public storage bucket. assets/landing/photo-{1,2,3}.jpg are the
sources of truth; LAND_P1/P2/P3 in index.html are generated copies.

Swap the JPEGs, run this, commit both.

    python3 tools/inline-landing-photos.py
"""

import base64
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

# photo-N.jpg fills LAND_PN. ph1 is the front card of the stack, ph3 the back.
SLOTS = [("LAND_P1", "photo-1.jpg"), ("LAND_P2", "photo-2.jpg"), ("LAND_P3", "photo-3.jpg")]

# The green "REPLACE ME" images the repo ships with. Inlining one is not an
# error -- the page still renders -- but it is almost never what was meant.
PLACEHOLDERS = {
    "1ff20afb2a37059f1b05a10fc3fae62f",
    "e458bfa7ed95c583724fb132895e51aa",
    "ff395ab9a1718be891bca10fe63799b5",
}


def main():
    page = PAGE.read_text(encoding="utf-8")
    changed, warned = [], []

    for const, filename in SLOTS:
        source = ROOT / "assets" / "landing" / filename
        if not source.is_file():
            sys.exit(f"missing source image: {source.relative_to(ROOT)}")

        raw = source.read_bytes()
        if not raw.startswith(b"\xff\xd8\xff"):
            sys.exit(f"{filename} is not a JPEG -- convert it before inlining")
        if hashlib.md5(raw).hexdigest() in PLACEHOLDERS:
            warned.append(filename)

        uri = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
        pattern = re.compile(rf'^const {const} = "[^"]*";$', re.M)
        if not pattern.search(page):
            sys.exit(f"could not find the {const} declaration in index.html")

        updated = pattern.sub(f'const {const} = "{uri}";', page, count=1)
        if updated != page:
            changed.append(f"{filename} -> {const}")
        page = updated

    PAGE.write_text(page, encoding="utf-8")

    for filename in warned:
        print(f"warning: {filename} is still the REPLACE ME placeholder")
    print("\n".join(changed) if changed else "already up to date")


if __name__ == "__main__":
    main()
