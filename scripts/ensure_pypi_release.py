"""Make prerequisite: publish this version only if PyPI explicitly reports 404.

Build in a temporary distribution directory so stale local artifacts cannot be
uploaded. Network/registry errors stop the Docker build; they never trigger a
publication. Poetry's existing PyPI credentials are used without reading them here.
"""

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
import tomllib
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def release_exists(version: str) -> bool:
    """Return False only for a missing release, and reject unusable releases."""
    request = Request(
        f"https://pypi.org/pypi/oldap-tools/{quote(version, safe='')}/json",
        headers={"Accept": "application/json", "Cache-Control": "no-cache"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            metadata = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return False
        raise RuntimeError(
            f"PyPI check failed (HTTP {error.code}); nothing published."
        ) from error
    except (URLError, TimeoutError, ValueError) as error:
        raise RuntimeError(
            "PyPI could not be checked; stop and retry later."
        ) from error
    if (
        not isinstance(metadata, dict)
        or metadata.get("info", {}).get("version") != version
    ):
        raise RuntimeError("PyPI returned unexpected release metadata.")
    if not any(
        file.get("packagetype") in ("sdist", "bdist_wheel")
        and not file.get("yanked", False)
        for file in metadata.get("urls", [])
    ):
        raise RuntimeError(
            "PyPI release exists but has no usable files; inspect it manually."
        )
    return True


def ensure_release(version: str) -> None:
    """Check tag/package agreement, publish if missing, then wait for visibility."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["poetry"]
    if project["name"] != "oldap-tools" or project["version"] != version:
        raise RuntimeError(
            f"Docker tag version {version!r} differs from package version {project['version']!r}. "
            "Align the release version/tag before building."
        )
    if release_exists(version):
        print(f"oldap-tools {version} is already available on PyPI.", flush=True)
        return
    print(
        f"oldap-tools {version} is missing on PyPI; building and publishing first.",
        flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="oldap-tools-release-") as output:
        subprocess.run(["poetry", "build", "--output", output], cwd=ROOT, check=True)
        subprocess.run(
            ["poetry", "publish", "--dist-dir", output], cwd=ROOT, check=True
        )
    for attempt in range(10):
        if release_exists(version):
            print(f"oldap-tools {version} is now available on PyPI.", flush=True)
            return
        if attempt < 9:
            time.sleep(3)
    raise RuntimeError(
        "Published version is not visible yet. Retry make docker-build shortly."
    )


def main() -> None:
    """Provide a concise failed-prerequisite message to Make."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        ensure_release(args.version)
    except (RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release prerequisite failed: {error}\n")


if __name__ == "__main__":
    main()
