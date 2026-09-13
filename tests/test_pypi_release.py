"""Release prerequisite tests: no registry uploads or Docker builds."""

import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts import ensure_pypi_release as release


class ReleasePrerequisiteTests(unittest.TestCase):
    def setUp(self):
        # Keep fixtures independent of the repository's next version bump.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        (root / "pyproject.toml").write_text(
            '[tool.poetry]\nname="oldap-tools"\nversion="0.3.13"\n'
        )
        replacement = patch.object(release, "ROOT", root)
        replacement.start()
        self.addCleanup(replacement.stop)

    def test_only_404_means_missing(self):
        for code in (404, 403, 429, 500):
            with (
                self.subTest(code=code),
                patch.object(
                    release,
                    "urlopen",
                    side_effect=HTTPError("https://pypi.org", code, "error", {}, None),
                ),
            ):
                if code == 404:
                    self.assertFalse(release.release_exists("0.3.13"))
                else:
                    with self.assertRaises(RuntimeError):
                        release.release_exists("0.3.13")

    def test_network_error_does_not_publish(self):
        with (
            patch.object(release, "urlopen", side_effect=URLError("offline")),
            patch.object(release.subprocess, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                release.ensure_release("0.3.13")
            run.assert_not_called()

    def test_existing_release_skips_build_and_publish(self):
        response = io.BytesIO(
            b'{"info":{"version":"0.3.13"},"urls":[{"packagetype":"bdist_wheel","yanked":false}]}'
        )
        with (
            patch.object(release, "urlopen", return_value=response),
            patch.object(release.subprocess, "run") as run,
        ):
            release.ensure_release("0.3.13")
            run.assert_not_called()

    def test_missing_release_builds_only_fresh_artifacts_then_waits(self):
        with (
            patch.object(release, "release_exists", side_effect=[False, False, True]),
            patch.object(release.subprocess, "run") as run,
            patch.object(release.time, "sleep"),
        ):
            release.ensure_release("0.3.13")
            build, publish = [call.args[0] for call in run.call_args_list]
            self.assertEqual(build[:3], ["poetry", "build", "--output"])
            self.assertEqual(publish, ["poetry", "publish", "--dist-dir", build[3]])
            self.assertNotEqual(build[3], "dist")

    def test_failed_build_never_publishes(self):
        with (
            patch.object(release, "release_exists", return_value=False),
            patch.object(
                release.subprocess,
                "run",
                side_effect=release.subprocess.CalledProcessError(1, "build"),
            ) as run,
        ):
            with self.assertRaises(release.subprocess.CalledProcessError):
                release.ensure_release("0.3.13")
            self.assertEqual(run.call_count, 1)

    def test_version_mismatch_stops_before_network_or_publication(self):
        with (
            patch.object(release, "release_exists") as exists,
            patch.object(release.subprocess, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                release.ensure_release("0.0.0")
            exists.assert_not_called()
            run.assert_not_called()
