"""Tests for resumable sequential batch orchestration and reports."""

from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import yaml

from oldap_tools.data_batch import execute_batch_import, write_batch_report
from oldap_tools.data_import import (
    DataImportPreflight,
    DataImportPreflightError,
    DataResourcePreflight,
)
from oldap_tools.data_yaml import loads_data_document


BATCH_DATA = """\
data:
  version: 1
  project: chama
  resources:
    - iri: First
      class: chama:Thing
      properties:
        schema:name:
          - value: First
            language: en
    - iri: Second
      class: chama:Thing
      properties:
        schema:name:
          - value: Second
            language: en
"""


class BatchImportTest(unittest.TestCase):
    """Verify sequential behavior independently of a live OLDAP project."""

    def _plan(self) -> DataImportPreflight:
        return DataImportPreflight(
            project="chama",
            resources=(
                DataResourcePreflight("chama:First", "chama:Thing", 1, 0),
                DataResourcePreflight("chama:Second", "chama:Thing", 1, 0),
            ),
        )

    @patch("oldap_tools.data_batch.prepare_data_import")
    @patch("oldap_tools.data_batch.prepare_document_media", return_value=())
    def test_preflight_rejects_forward_dependency_order(
        self, _prepare_media, prepare_import
    ) -> None:
        prepare_import.return_value = DataImportPreflight(
            project="chama",
            resources=(
                DataResourcePreflight(
                    "chama:First",
                    "chama:Thing",
                    1,
                    1,
                    reference_iris=("chama:Second",),
                ),
                DataResourcePreflight("chama:Second", "chama:Thing", 1, 0),
            ),
        )

        with self.assertRaisesRegex(DataImportPreflightError, "must appear earlier"):
            execute_batch_import(
                object(),
                object(),
                loads_data_document(BATCH_DATA),
                apply=False,
                api_base="http://api.test",
                media_base="http://media.test",
                user="tester",
                password="secret",
            )

    @patch("oldap_tools.data_batch.create_data_resource")
    @patch("oldap_tools.data_batch.prepare_data_import")
    @patch("oldap_tools.data_batch.prepare_document_media", return_value=())
    def test_apply_processes_every_preflighted_resource_in_order(
        self, _prepare_media, prepare_import, create_resource
    ) -> None:
        prepare_import.return_value = self._plan()
        create_resource.side_effect = ["chama:First", "chama:Second"]

        _plan, execution = execute_batch_import(
            object(),
            object(),
            loads_data_document(BATCH_DATA),
            apply=True,
            api_base="http://api.test",
            media_base="http://media.test",
            user="tester",
            password="secret",
        )

        self.assertTrue(execution.succeeded)
        self.assertEqual(
            [result.metadata_status for result in execution.resources],
            ["created", "created"],
        )
        self.assertEqual(create_resource.call_count, 2)

    @patch("oldap_tools.data_batch.create_data_resource")
    @patch("oldap_tools.data_batch.prepare_data_import")
    @patch("oldap_tools.data_batch.prepare_document_media", return_value=())
    def test_apply_stops_at_first_failure_and_marks_remainder(
        self, _prepare_media, prepare_import, create_resource
    ) -> None:
        prepare_import.return_value = self._plan()
        create_resource.side_effect = RuntimeError("write failed")

        _plan, execution = execute_batch_import(
            object(),
            object(),
            loads_data_document(BATCH_DATA),
            apply=True,
            api_base="http://api.test",
            media_base="http://media.test",
            user="tester",
            password="secret",
        )

        self.assertFalse(execution.succeeded)
        self.assertEqual(execution.resources[0].metadata_status, "failed")
        self.assertEqual(execution.resources[1].metadata_status, "not_started")
        self.assertEqual(create_resource.call_count, 1)

    @patch("oldap_tools.data_batch.prepare_data_import")
    @patch("oldap_tools.data_batch.prepare_document_media", return_value=())
    def test_dry_run_and_json_yaml_reports_are_machine_readable(
        self, _prepare_media, prepare_import
    ) -> None:
        prepare_import.return_value = self._plan()
        _plan, execution = execute_batch_import(
            object(),
            object(),
            loads_data_document(BATCH_DATA),
            apply=False,
            api_base="http://api.test",
            media_base="http://media.test",
            user="tester",
            password="secret",
        )

        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "report.json"
            yaml_path = Path(directory) / "report.yaml"
            write_batch_report(json_path, execution)
            write_batch_report(yaml_path, execution)
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
            yaml_payload = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        self.assertTrue(json_payload["batch_import"]["succeeded"])
        self.assertEqual(
            yaml_payload["batch_import"]["resources"][0]["metadata_status"],
            "would_create",
        )


if __name__ == "__main__":
    unittest.main()
