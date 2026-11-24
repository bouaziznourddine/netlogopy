"""Switch the links of README.md between relative and absolute forms.

    python tools/readme_links.py relative   # in the repository (GitHub, mirrors)
    python tools/readme_links.py absolute   # before building the package for PyPI

Relative paths work on GitHub and in any copy of the repository (an anonymised
mirror for review, a fork, a local clone).  PyPI shows the README outside the
repository, so the publishing workflow makes the paths absolute before it
builds the package; the file in the repository stays relative.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "https://github.com/bouaziznourddine/netlogopy"
RAW = "https://raw.githubusercontent.com/bouaziznourddine/netlogopy/main/"
BLOB = REPO + "/blob/main/"
TREE = REPO + "/tree/main/"

# README.md and the folder whose README shows its own files
FILES = {"README.md": "", "Examples/README.md": "Examples/"}


def to_relative(text: str, folder: str) -> str:
    up = "../" * folder.count("/")
    text = text.replace(RAW, up)
    for prefix in (BLOB, TREE):
        text = re.sub(re.escape(prefix) + r"([^)\s\"]*)",
                      lambda m: (m.group(1)[len(folder):] if m.group(1).startswith(folder) else up + m.group(1))
                      or ".", text)
    return text


def to_absolute(text: str, folder: str) -> str:
    def image(m):
        path = m.group(2)
        return m.group(1) + RAW + resolve(folder, path) + m.group(3)

    def link(m):
        path = m.group(2)
        target = resolve(folder, path)
        base = TREE if not Path(target).suffix else BLOB
        return m.group(1) + base + target + m.group(3)

    text = re.sub(r'(src=")((?!https?:|#)[^"]+)(")', image, text)
    text = re.sub(r"(!\[[^\]]*\]\()((?!https?:|#)[^)\s]+)(\))", image, text)
    text = re.sub(r'(href=")((?!https?:|#|mailto:)[^"]+)(")', link, text)
    text = re.sub(r"((?<!!)\[[^\]]*\]\()((?!https?:|#|mailto:)[^)\s]+)(\))", link, text)
    return text


def resolve(folder: str, path: str) -> str:
    parts = (folder + path).split("/")
    out = []
    for part in parts:
        if part == "..":
            out.pop()
        elif part not in ("", "."):
            out.append(part)
    return "/".join(out)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "relative"
    convert = {"relative": to_relative, "absolute": to_absolute}[mode]
    files = FILES if mode == "relative" else {"README.md": ""}   # PyPI only shows README.md
    for name, folder in files.items():
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        new = convert(text, folder)
        if new != text:
            path.write_text(new, encoding="utf-8")
            print(f"{name}: links made {mode}")


if __name__ == "__main__":
    main()
