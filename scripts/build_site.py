#!/usr/bin/env python3
"""Build the static GitHub Pages site into _site/."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA = ROOT / "data"
OUTPUT = ROOT / "_site"


def build() -> Path:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    shutil.copytree(WEB, OUTPUT)
    data_output = OUTPUT / "data"
    data_output.mkdir(parents=True, exist_ok=True)
    for filename in ("who_bmi_0_5.tsv", "who_bmi_5_19.tsv"):
        source = DATA / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, data_output / filename)
    (OUTPUT / ".nojekyll").write_text("", encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    target = build()
    print(f"Built static site: {target}")
