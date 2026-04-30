"""Pick three random words from words.txt for RainHawk feature inspiration.

Prints exactly three lines to stdout, one word each. Source: EFF large
diceware wordlist (7776 common English words, public domain).

Usage:
    python scripts/pick_words.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

WORDS_PATH = Path(__file__).parent / "words.txt"
PICK = 3


def main() -> None:
    words = [
        line.strip()
        for line in WORDS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(words) < PICK:
        sys.exit(f"words.txt has {len(words)} entries; need at least {PICK}")
    for word in random.sample(words, PICK):
        print(word)


if __name__ == "__main__":
    main()
