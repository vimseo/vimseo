from __future__ import annotations

import pathlib

if __name__ == "__main__":
    content = pathlib.Path("README.md").read_text()
    content = content.replace("/docs/images", "images")
    content = content.replace(
        "[Contributing](https://vimseo.github.io/vimseo/latest/contributing/)",
        "[Contributing](contributing.md)",
    )
    # The home page of a version links to the pages of this version, not of latest.
    content = content.replace("https://vimseo.github.io/vimseo/latest/", "")
    pathlib.Path("README_tmp.md").write_text(content)
