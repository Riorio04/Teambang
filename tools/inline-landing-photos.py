#!/usr/bin/env python3
"""Downscale the landing photo-stack images and inline them into index.html.

The three overlapping photos beside "Where every project stands" are served
as base64 data URIs so the landing page paints without a network round trip
and without a public storage bucket. assets/landing/photo-{1,2,3}.jpg are the
sources of truth; LAND_P1/P2/P3 in index.html are generated copies.

Base64 costs a third again in size and lands in the initial HTML, so a
straight-from-the-camera photo would hold up first paint for everyone. The
cards render 172px tall, so anything past BOX is invisible anyway: sources
larger than that are downscaled in place before being inlined.

Drop new JPEGs into assets/landing/, run this, commit both.

    python3 tools/inline-landing-photos.py
"""

import base64
import hashlib
import io
import pathlib
import re
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "index.html"

# photo-N.jpg fills LAND_PN. ph1 is the front card of the stack, ph3 the back.
SLOTS = [("LAND_P1", "photo-1.jpg"), ("LAND_P2", "photo-2.jpg"), ("LAND_P3", "photo-3.jpg")]

# Roughly 2x the largest the cards are ever drawn, so they stay sharp on
# retina screens without paying for detail nobody sees.
BOX = (720, 480)
QUALITY = 82

# The green "REPLACE ME" images the repo ships with. Inlining one is not an
# error -- the page still renders -- but it is almost never what was meant.
PLACEHOLDERS = {
    "1ff20afb2a37059f1b05a10fc3fae62f",
    "e458bfa7ed95c583724fb132895e51aa",
    "ff395ab9a1718be891bca10fe63799b5",
}


def shrink(raw):
    """Return raw downscaled to fit BOX, or None if it already fits."""
    image = Image.open(io.BytesIO(raw))
    if image.width <= BOX[0] and image.height <= BOX[1]:
        return None

    image = image.convert("RGB")
    image.thumbnail(BOX, Image.LANCZOS)
    buffer = io.BytesIO()
    # No exif= argument, so camera metadata (location included) is dropped.
    image.save(buffer, "JPEG", quality=QUALITY, optimize=True, progressive=True)
    return buffer.getvalue()


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

        smaller = shrink(raw)
        if smaller is not None:
            was = Image.open(io.BytesIO(raw)).size
            now = Image.open(io.BytesIO(smaller)).size
            source.write_bytes(smaller)
            changed.append(
                f"{filename}: {was[0]}x{was[1]} {len(raw) // 1024}KB"
                f" -> {now[0]}x{now[1]} {len(smaller) // 1024}KB"
            )
            raw = smaller

        uri = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
        pattern = re.compile(rf'^const {const} = "[^"]*";$', re.M)
        if not pattern.search(page):
            sys.exit(f"could not find the {const} declaration in index.html")

        updated = pattern.sub(lambda _: f'const {const} = "{uri}";', page, count=1)
        if updated != page:
            changed.append(f"{filename} -> {const}")
        page = updated

    PAGE.write_text(page, encoding="utf-8")

    for filename in warned:
        print(f"warning: {filename} is still the REPLACE ME placeholder")
    print("\n".join(changed) if changed else "already up to date")


if __name__ == "__main__":
    main()
