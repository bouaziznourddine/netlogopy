#!/usr/bin/env python
"""Keep the NetLogo code in sync with netlogopy/base.nls (the single source).

base.nls holds the procedures that netlogopy calls from Python. This script
copies them into:
  * netlogopy/netlogopy.nlogo  -- below the "; >>> netlogopy procedures" marker
                                  of its Code tab (the part above is kept);
  * every Examples/**/base.nls -- a full copy of the file.

Usage:
    python tools/sync_nlogo.py           # update the files
    python tools/sync_nlogo.py --check   # exit 1 if a file is out of date
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_NLS = ROOT / "netlogopy" / "base.nls"
MODEL = ROOT / "netlogopy" / "netlogopy.nlogo"
MARKER = "; >>> netlogopy procedures"
SECTION = "@#$#@#$#@"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def base_procedures(base_text: str) -> str:
    """Procedures of base.nls: what follows the marker and its comment lines."""
    lines = base_text.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith(MARKER)) + 1
    while start < len(lines) and lines[start].startswith(";"):
        start += 1
    return "\n".join(lines[start:]).strip("\n")


def synced_model(model_text: str, procedures: str) -> str:
    """Model text with the generated block replaced by `procedures`."""
    code, separator, rest = model_text.partition("\n" + SECTION)
    if not separator:
        raise ValueError("{} has no Code section separator".format(MODEL))
    lines = code.split("\n")
    marker = next(i for i, line in enumerate(lines) if line.startswith(MARKER))
    new_code = "\n".join(lines[:marker + 1]) + "\n\n" + procedures
    return new_code + separator + rest


def example_copies() -> list:
    return sorted((ROOT / "Examples").glob("**/base.nls"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="only report files that are out of date")
    args = parser.parse_args(argv)

    base_text = read(BASE_NLS)
    targets = [(MODEL, synced_model(read(MODEL), base_procedures(base_text)))]
    targets += [(path, base_text) for path in example_copies()]

    stale = [(path, text) for path, text in targets if read(path) != text]
    for path, text in stale:
        if args.check:
            print("out of date: {}".format(path.relative_to(ROOT)))
        else:
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            print("updated: {}".format(path.relative_to(ROOT)))
    if args.check and stale:
        print("Run: python tools/sync_nlogo.py")
        return 1
    if not stale:
        print("NetLogo code is in sync with base.nls.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
