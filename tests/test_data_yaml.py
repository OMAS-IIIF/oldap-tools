"""Tests for the versioned OLDAP instance-data document and CLI."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from oldap_tools.cli import app
from oldap_tools.data_batch import BatchImportExecution, BatchResourceResult
from oldap_tools.data_import import (
    DataImportExecution,
    DataImportPreflight,
    DataResourcePreflight,
)
from oldap_tools.data_yaml import DataValidationError, loads_data_document


VALID_YAML = """\
data:
  version: 1
  project: chama
  resources:
    - iri: IMG_1520
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: Stationsgebäude in Chama
            language: DE
        dcterms:creator:
          - iri: chama:LukasRosenthaler
        chama:publicDisplayPermission:
          - value: true
      permissions:
        oldap:Unknown: DATA_VIEW
"""


class DataYamlTest(unittest.TestCase):
    """Validate parsing invariants without requiring an OLDAP connection."""

    def setUp(self) -> None:
        self.runner = CliRunner()

    def _data_file(self, source: str = VALID_YAML) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with handle:
            handle.write(source)
        return Path(handle.name)

    def test_parses_explicit_literal_reference_and_permission_values(self) -> None:
        document = loads_data_document(VALID_YAML)

        self.assertEqual(document.version, 1)
        self.assertEqual(document.project, "chama")
        resource = document.resources[0]
        self.assertEqual(resource.iri, "IMG_1520")
        self.assertEqual(resource.resource_class, "chama:CataloguedPhotograph")
        self.assertEqual(resource.properties["schema:name"][0].language, "de")
        self.assertEqual(
            resource.properties["dcterms:creator"][0].iri,
            "chama:LukasRosenthaler",
        )
        self.assertIs(resource.properties["chama:publicDisplayPermission"][0].value, True)
        self.assertEqual(resource.permissions, {"oldap:Unknown": "DATA_VIEW"})

    def test_parses_local_copy_and_external_iiif_reference_media(self) -> None:
        local = loads_data_document(
            VALID_YAML.replace(
                "      permissions:",
                "      media:\n"
                "        source:\n"
                "          type: file\n"
                "          path: ../../assets/photo.heic\n"
                "        handling: copy\n"
                "        ingest_profile: image-iiif\n"
                "      permissions:",
            )
        ).resources[0].media
        self.assertIsNotNone(local)
        self.assertEqual(local.source.path, "../../assets/photo.heic")
        self.assertEqual(local.ingest_profile, "image-iiif")

        external = loads_data_document(
            VALID_YAML.replace(
                "      permissions:",
                "      media:\n"
                "        source:\n"
                "          type: iiif-image\n"
                "          info_url: https://example.org/iiif/3/image/info.json\n"
                "        handling: reference\n"
                "      permissions:",
            )
        ).resources[0].media
        self.assertEqual(external.source.source_type, "iiif-image")
        self.assertEqual(external.handling, "reference")

    def test_rejects_ambiguous_or_unimplemented_media_workflows(self) -> None:
        media = (
            "      media:\n"
            "        source:\n"
            "          type: file\n"
            "          path: photo.wav\n"
            "        handling: copy\n"
            "        ingest_profile: audio-access\n"
            "      permissions:"
        )
        with self.assertRaisesRegex(DataValidationError, "reserved but not implemented"):
            loads_data_document(VALID_YAML.replace("      permissions:", media))

        with self.assertRaisesRegex(DataValidationError, "must use handling 'copy'"):
            loads_data_document(
                VALID_YAML.replace(
                    "      permissions:",
                    media.replace("handling: copy", "handling: reference").replace(
                        "        ingest_profile: audio-access\n", ""
                    ),
                )
            )

        with self.assertRaisesRegex(DataValidationError, "must be relative"):
            loads_data_document(
                VALID_YAML.replace(
                    "      permissions:",
                    media.replace("photo.wav", "/tmp/photo.wav").replace(
                        "audio-access", "image-iiif"
                    ),
                )
            )

    def test_accepts_json_with_the_same_semantics(self) -> None:
        document = loads_data_document(
            json.dumps(
                {
                    "data": {
                        "version": 1,
                        "project": "chama",
                        "resources": [
                            {
                                "iri": "IMG_1520",
                                "class": "chama:CataloguedPhotograph",
                                "properties": {
                                    "schema:name": [{"value": "Chama station"}]
                                },
                            }
                        ],
                    }
                }
            )
        )

        self.assertEqual(document.resources[0].iri, "IMG_1520")

    def test_refuses_ambiguous_and_duplicate_content(self) -> None:
        with self.assertRaisesRegex(DataValidationError, "exactly one"):
            loads_data_document(
                VALID_YAML.replace(
                    "- iri: chama:LukasRosenthaler",
                    "- iri: chama:LukasRosenthaler\n            value: Lukas",
                )
            )
        with self.assertRaisesRegex(DataValidationError, "Duplicate mapping key"):
            loads_data_document(VALID_YAML.replace("version: 1", "version: 1\n  version: 1"))

    def test_refuses_unknown_keys_invalid_permissions_and_duplicate_resources(self) -> None:
        with self.assertRaisesRegex(DataValidationError, "unknown keys: title"):
            loads_data_document(
                VALID_YAML.replace(
                    "class: chama:CataloguedPhotograph",
                    "class: chama:CataloguedPhotograph\n      title: Station",
                )
            )
        with self.assertRaisesRegex(DataValidationError, "must be one of"):
            loads_data_document(VALID_YAML.replace("DATA_VIEW", "READ"))
        resource_block = VALID_YAML.split("    - iri: IMG_1520", maxsplit=1)[1]
        with self.assertRaisesRegex(DataValidationError, "duplicate identities"):
            loads_data_document(VALID_YAML + "    - iri: IMG_1520" + resource_block)

    def test_refuses_non_integer_versions_and_reserved_properties(self) -> None:
        with self.assertRaisesRegex(DataValidationError, "integer 1"):
            loads_data_document(VALID_YAML.replace("version: 1", "version: 1.0"))
        with self.assertRaisesRegex(DataValidationError, "use permissions instead"):
            loads_data_document(
                VALID_YAML.replace(
                    "schema:name:",
                    "oldap:attachedToRole:\n          - value: forbidden\n        schema:name:",
                )
            )

    def test_repository_img_1520_example_is_valid(self) -> None:
        example = Path(__file__).parents[1] / "examples/data/chama-img-1520.yaml"

        result = self.runner.invoke(app, ["data", "validate", "--inf", str(example)])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("1 resource(s), project chama", result.output)

    def test_repository_batch_example_is_valid(self) -> None:
        example = (
            Path(__file__).parents[1]
            / "examples/data/batch-external-images.example.yaml"
        )

        result = self.runner.invoke(app, ["data", "validate", "--inf", str(example)])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("2 resource(s), project chama", result.output)

    def test_repository_chama_photo_batch_is_valid(self) -> None:
        example = (
            Path(__file__).parents[1]
            / "examples/data/chama-photographs-batch-01.yaml"
        )

        result = self.runner.invoke(app, ["data", "validate", "--inf", str(example)])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("9 resource(s), project chama", result.output)

    def test_validate_cli_is_offline_and_reports_a_summary(self) -> None:
        source = self._data_file()

        result = self.runner.invoke(app, ["data", "validate", "--inf", str(source)])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("valid OLDAP data version 1", result.output)
        self.assertIn("1 resource(s), project chama", result.output)

    def test_connected_commands_still_require_credentials(self) -> None:
        result = self.runner.invoke(app, ["project", "load"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Connected commands require --user", result.output)
        self.assertNotIn("OLDAP password:", result.output)

    @patch("oldap_tools.cli.run_data_import")
    def test_import_command_reports_read_only_plan(self, run_import) -> None:
        source = self._data_file()
        plan = DataImportPreflight(
            project="chama",
            resources=(
                DataResourcePreflight(
                    iri="chama:IMG_1520",
                    resource_class="chama:CataloguedPhotograph",
                    property_count=3,
                    reference_count=1,
                ),
            ),
        )
        run_import.return_value = DataImportExecution(plan=plan)

        result = self.runner.invoke(
            app,
            [
                "--user",
                "tester",
                "--password",
                "secret",
                "data",
                "import",
                "--dry-run",
                "--inf",
                str(source),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("no data was written", result.output)
        self.assertIn("would create chama:IMG_1520", result.output)
        self.assertFalse(run_import.call_args.kwargs["apply"])

    @patch("oldap_tools.cli.run_data_import")
    def test_import_command_reports_create_only_apply(self, run_import) -> None:
        source = self._data_file()
        plan = DataImportPreflight(
            project="chama",
            resources=(
                DataResourcePreflight(
                    iri="chama:IMG_1520",
                    resource_class="chama:CataloguedPhotograph",
                    property_count=3,
                    reference_count=1,
                ),
            ),
        )
        run_import.return_value = DataImportExecution(
            plan=plan,
            created_iris=("chama:IMG_1520",),
        )

        result = self.runner.invoke(
            app,
            [
                "--user",
                "tester",
                "--password",
                "secret",
                "data",
                "import",
                "--apply",
                "--inf",
                str(source),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Created 1 resource(s)", result.output)
        self.assertIn("created chama:IMG_1520", result.output)
        self.assertTrue(run_import.call_args.kwargs["apply"])

    @patch("oldap_tools.cli.run_batch_import")
    def test_import_command_reports_resumable_batch_apply(self, run_batch) -> None:
        source = self._data_file()
        plan = DataImportPreflight(
            project="chama",
            resources=(
                DataResourcePreflight(
                    iri="chama:IMG_1520",
                    resource_class="chama:CataloguedPhotograph",
                    property_count=3,
                    reference_count=1,
                ),
            ),
        )
        run_batch.return_value = (
            plan,
            BatchImportExecution(
                project="chama",
                mode="apply",
                succeeded=True,
                resources=(
                    BatchResourceResult(
                        "chama:IMG_1520", "existing_verified", "existing_verified"
                    ),
                ),
            ),
        )

        result = self.runner.invoke(
            app,
            [
                "--user",
                "tester",
                "--password",
                "secret",
                "data",
                "import",
                "--apply",
                "--batch",
                "--inf",
                str(source),
            ],
        )

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Batch apply completed", result.output)
        self.assertIn("metadata=existing_verified", result.output)
        self.assertTrue(run_batch.call_args.kwargs["apply"])

    def test_validate_cli_returns_a_concise_path_aware_error(self) -> None:
        source = self._data_file(VALID_YAML.replace("language: DE", "language: 7"))

        result = self.runner.invoke(app, ["data", "validate", "--inf", str(source)])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Data validation failed", result.output)
        self.assertIn("data.resources[0].properties.schema:name[0].language", result.output)


if __name__ == "__main__":
    unittest.main()
