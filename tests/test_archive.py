"""Tests for the thin oldap-tools archive CLI integration."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from oldap_tools import archive as archive_adapter
from oldap_tools.cli import app


VALID_YAML = """\
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title: Archiv BMG
      children:
        - id: bmg-stamm
          level: Subfonds
          title: Stamm
"""


class ArchiveAdapterTest(unittest.TestCase):
    """Verify compatibility commands without duplicating oldaplib domain tests."""

    def setUp(self) -> None:
        self.runner = CliRunner()

    def _yaml_file(self) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with handle:
            handle.write(VALID_YAML)
        return Path(handle.name)

    def test_adapter_uses_canonical_oldaplib_implementation(self) -> None:
        document = archive_adapter.read_archive_yaml(self._yaml_file(), "fasnacht")

        self.assertEqual(document.units[0].unit_id, "bmg")
        self.assertEqual(
            archive_adapter.loads_archive_yaml.__module__,
            "oldaplib.src.archive_yaml",
        )
        self.assertEqual(
            archive_adapter.prepare_archive_import.__module__,
            "oldaplib.src.archive_import",
        )

    def test_archive_validate_command_is_offline(self) -> None:
        source = self._yaml_file()

        result = self.runner.invoke(
            app,
            ["archive", "validate", "--inf", str(source)],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(f"{source} is valid", result.output)

    @patch("oldap_tools.cli.load_archive")
    def test_archive_load_keeps_dry_run_as_default(self, load_archive: Mock) -> None:
        source = self._yaml_file()
        unit = Mock(iri="fasnacht:bmg", level="Fonds", parent_iri=None)
        load_archive.return_value = Mock(units=(unit,))

        result = self.runner.invoke(
            app,
            [
                "--user",
                "tester",
                "--password",
                "secret",
                "archive",
                "load",
                "fasnacht",
                "--inf",
                str(source),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(load_archive.call_args.kwargs["dry_run"])
        self.assertIn("Would create 1 archive unit", result.output)


if __name__ == "__main__":
    unittest.main()
