from __future__ import annotations

import pathlib

if __name__ == "__main__":
    content = pathlib.Path("README.md").read_text()
    content = content.replace("/docs/images", "images")
    content = content.replace(
        "[Contributing](https://vimseo.github.io/vimseo/contributing/)",
        "[Contributing](contributing.md)",
    )
    pathlib.Path("README_tmp.md").write_text(content)
