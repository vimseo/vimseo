from __future__ import annotations

import pathlib

if __name__ == "__main__":
    content = pathlib.Path("README.md").read_text()
    content = content.replace("/docs/images", "images")
    pathlib.Path("README_tmp.md").write_text(content)
