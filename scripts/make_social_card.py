#!/usr/bin/env python3
"""Render the social preview card for each repository in the organisation.

Every repository here shows GitHub's default preview when its link is pasted
anywhere: the grey card with an avatar and a line of metadata. The site has had
a generated card since August; the repositories, which are what people actually
link to, had none.

The cards are drawn in the site's visual language, from one generator, so seven
repositories cannot drift into seven different looks. What each card says comes
from REPOS below rather than from the GitHub API: the card is a decision about
what to lead with, not a mirror of the description field, and a generator that
silently redraws whenever someone edits a description is one nobody can review.

Output is not byte-reproducible -- the cards are drawn with whatever fonts the
machine has, and a Linux runner has neither Georgia nor Calibri -- so --check
verifies that every repository has a card of the right size, not that it renders
to identical bytes.

    python scripts/make_social_card.py               # write cards/<repo>.png
    python scripts/make_social_card.py --check       # verify they are present
    python scripts/make_social_card.py --only glia

Pillow is the only dependency, and only for regenerating: the cards are
committed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# GitHub renders a repository social preview at 1280x640 and crops anything
# else. The site card is 1200x630, the Open Graph default; these are for
# repositories, so they follow GitHub.
W, H = 1280, 640

ROOT = Path(__file__).resolve().parent.parent
MARK_PATH = ROOT / "assets" / "mark.png"
OUT_DIR = ROOT / "cards"

INK = (10, 11, 14)
LINE = (34, 38, 48)
PAPER = (248, 249, 251)
PAPER_DIM = (154, 161, 173)
PAPER_FAINT = (124, 134, 151)
ACCENT = (165, 176, 255)
GOLD = (216, 182, 120)

FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts"), Path("/Library/Fonts")]
SERIF = ["georgiab.ttf", "Georgia_Bold.ttf", "DejaVuSerif-Bold.ttf", "LiberationSerif-Bold.ttf"]
SANS = ["calibri.ttf", "arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]
MONO = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"]

# What each card leads with: the one sentence that should survive being read on
# a phone, not the repository description verbatim.
REPOS: dict[str, dict[str, str]] = {
    "decisionrl": {
        "line": "Reinforcement learning for the decisions a business\nmakes thousands of times a day.",
        "command": 'pip install "decisionrl[torch]"',
        "meta": "Python 3.9+",
        "licence": "MIT",
    },
    "praxis": {
        "line": "A legal assistant for Russian law whose citations\nare checked, not asserted.",
        "command": "docker compose up app",
        "meta": "Python 3.12 \u00b7 FastAPI",
        "licence": "Apache-2.0",
    },
    "mlango": {
        "line": "Know what your new model version broke\nbefore you promote it.",
        "command": 'pip install "mlango[sklearn]"',
        "meta": "Python 3.10+",
        "licence": "MIT",
    },
    "glia": {
        "line": "A glass-box library for LLM agents.\nNo hidden control flow.",
        "command": "pip install glia-agents",
        "meta": "Python 3.10+ \u00b7 zero dependencies",
        "licence": "MIT",
    },
    "stadion": {
        "line": "A proving ground where an agent is scored against\nthe classical method and the exact optimum.",
        "command": "pip install stadion-rl",
        "meta": "Python 3.10+",
        "licence": "MIT",
    },
    "lemma": {
        "line": "\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0439 \u043a\u0443\u0440\u0441: \u0434\u043e\u0440\u043e\u0436\u043d\u0430\u044f \u043a\u0430\u0440\u0442\u0430 \u0432 ML, DL \u0438 RL \u2014\n\u0441 \u043d\u0443\u043b\u044f \u0438 \u0434\u043e \u0447\u0442\u0435\u043d\u0438\u044f \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0439.",
        "command": "drobyshevdev.github.io/lemma",
        "meta": "27 \u043c\u043e\u0434\u0443\u043b\u0435\u0439 \u00b7 \u043d\u043e\u0443\u0442\u0431\u0443\u043a\u0438 \u0432 CI",
        "licence": "CC BY 4.0",
    },
    "research": {
        "line": "Open reading notes. Every note names\nwhat it rests on.",
        "command": "drobyshevdev.github.io/research",
        "meta": "Notes \u00b7 EN / RU",
        "licence": "CC BY 4.0",
    },
}


def load_font(candidates: list[str], size: int) -> ImageFont.ImageFont:
    """First font that exists, falling back to Pillow's built-in.

    The cards are committed, so a machine without these fonts never has to
    render one; the fallback exists so --check can run anywhere.
    """
    for directory in FONT_DIRS:
        if not directory.is_dir():
            continue
        for name in candidates:
            direct = directory / name
            if direct.is_file():
                try:
                    return ImageFont.truetype(str(direct), size)
                except OSError:
                    pass
            for path in directory.rglob(name):
                try:
                    return ImageFont.truetype(str(path), size)
                except OSError:
                    continue
    return ImageFont.load_default()


def paste_mark(img: Image.Image, x: int, y: int, size: int) -> None:
    if not MARK_PATH.is_file():
        return
    mark = Image.open(MARK_PATH).convert("RGB").resize((size, size), Image.LANCZOS)
    img.paste(mark, (x, y))


def render(name: str, spec: dict[str, str]) -> Image.Image:
    img = Image.new("RGB", (W, H), INK)

    # The same top-left wash as the site card and the site hero.
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    for i in range(60, 0, -1):
        radius = i * 13
        t = i / 60
        colour = tuple(int(INK[c] + (ACCENT[c] - INK[c]) * 0.10 * (1 - t)) for c in range(3))
        gd.ellipse([-radius + 130, -radius + 40, radius + 130, radius + 40], fill=colour)
    img = Image.blend(img, glow, 0.9)

    f_name = load_font(SERIF, 76)
    f_line = load_font(SANS, 31)
    f_mono = load_font(MONO, 25)
    f_brand = load_font(SANS, 30)

    pad = 88
    paste_mark(img, pad, 66, 50)
    d = ImageDraw.Draw(img)
    d.text((pad + 68, 74), "DrobyshevDev", font=f_brand, fill=PAPER_DIM)

    d.text((pad, 168), name, font=f_name, fill=PAPER)

    y = 282
    for row in spec["line"].split("\n"):
        d.text((pad, y), row, font=f_line, fill=PAPER_DIM)
        y += 44

    command = spec["command"]
    box_width = int(d.textlength(command, font=f_mono)) + 36
    d.rounded_rectangle([pad, 430, pad + box_width, 484], radius=8, outline=LINE, width=1)
    d.text((pad + 18, 444), command, font=f_mono, fill=ACCENT)

    d.line([(pad, 536), (W - pad, 536)], fill=LINE, width=1)
    d.text((pad, 562), spec["meta"], font=f_mono, fill=PAPER_FAINT)
    licence = spec["licence"]
    d.text((W - pad - d.textlength(licence, font=f_mono), 562), licence, font=f_mono, fill=GOLD)
    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the cards exist and are sized right")
    parser.add_argument("--only", help="render one repository")
    args = parser.parse_args()

    names = [args.only] if args.only else list(REPOS)
    unknown = [name for name in names if name not in REPOS]
    if unknown:
        print(f"  unknown repository: {', '.join(unknown)}", file=sys.stderr)
        return 2

    if args.check:
        problems = []
        for name in names:
            path = OUT_DIR / f"{name}.png"
            if not path.is_file():
                problems.append(f"{name}: no card at {path.relative_to(ROOT)}")
                continue
            with Image.open(path) as card:
                if card.size != (W, H):
                    problems.append(f"{name}: card is {card.size[0]}x{card.size[1]}, not {W}x{H}")
        for problem in problems:
            print(f"  {problem}")
        if problems:
            return 1
        print(f"  {len(names)} cards present, all {W}x{H}.")
        return 0

    OUT_DIR.mkdir(exist_ok=True)
    for name in names:
        path = OUT_DIR / f"{name}.png"
        render(name, REPOS[name]).save(path, optimize=True)
        print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
