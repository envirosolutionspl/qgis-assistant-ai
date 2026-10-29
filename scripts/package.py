"""Build the installable ZIP of GIS Assistant AI.

Packs the ``gis_assistant_ai`` folder into
``dist/gis_assistant_ai-<version>.zip``, with the version taken from
``metadata.txt``. Byte-code, translation sources and editor leftovers are
left out. The ZIP is installed in QGIS under *Plugins -> Manage and Install
Plugins -> Install from ZIP*.

Usage::

    python scripts/package.py
"""

import configparser
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = "gis_assistant_ai"
SKIPPED_DIRS = {"__pycache__"}
SKIPPED_SUFFIXES = {".pyc", ".pyo", ".bak", ".orig", ".swp", ".ts"}


def version():
    """Read the plugin version.

    :returns: the ``version`` entry of ``metadata.txt``.
    """
    metadata = configparser.ConfigParser(interpolation=None)
    metadata.read(ROOT / PLUGIN / "metadata.txt", encoding="utf-8")
    return metadata["general"]["version"]


def files():
    """List the files that go into the ZIP.

    :returns: sorted paths under the plugin folder.
    """
    found = []
    for path in sorted((ROOT / PLUGIN).rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or SKIPPED_DIRS & set(relative.parts):
            continue
        if path.suffix in SKIPPED_SUFFIXES or path.name.startswith("."):
            continue
        found.append(path)
    return found


def build(dest=None):
    """Write the ZIP.

    :param dest: folder for the ZIP; ``dist`` in the repository by default.
    :returns: path of the ZIP file.
    """
    dest = Path(dest) if dest is not None else ROOT / "dist"
    target = dest / "{}-{}.zip".format(PLUGIN, version())
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files():
            archive.write(path, path.relative_to(ROOT).as_posix())
    return target


if __name__ == "__main__":
    print(build())
