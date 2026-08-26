"""Tests for explicit, text-preserving automatic resource IRI preparation."""

import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from typer.testing import CliRunner

from oldap_tools.cli import app
from oldap_tools.data_prepare import prepare_data_file, prepare_data_source
from oldap_tools.data_yaml import (
    DataValidationError,
    load_data_document,
    loads_data_document,
)
from oldap_tools.media_ingest import prepare_document_media


AUTO_YAML = """\
# This comment and the human-authored formatting must survive preparation.
data:
  version: 1
  project: chama
  resources:
    - iri: auto  # first independent camera file
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: First photograph
            language: en
        shared:originalName:
          - value: DC_0015.HEIC
    - iri: auto  # same original filename, different photograph
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: Second photograph
            language: en
        shared:originalName:
          - value: DC_0015.HEIC
"""


class DataPrepareTest(unittest.TestCase):
    """Ensure automatic identity is explicit, unique, and resumable."""

    def setUp(self) -> None:
        self.runner = CliRunner()

    @staticmethod
    def _uuid_factory():
        values = iter((UUID(int=1), UUID(int=2)))
        return lambda: next(values)

    def test_multiple_auto_resources_with_same_filename_receive_unique_iris(self) -> None:
        raw = loads_data_document(AUTO_YAML)
        self.assertEqual(raw.auto_iri_count, 2)

        prepared_source = prepare_data_source(
            AUTO_YAML,
            uuid_factory=self._uuid_factory(),
        )
        prepared = loads_data_document(prepared_source)

        self.assertEqual(prepared.auto_iri_count, 0)
        self.assertEqual(
            [resource.iri for resource in prepared.resources],
            [
                "resource_00000000000000000000000000000001",
                "resource_00000000000000000000000000000002",
            ],
        )
        self.assertEqual(
            [
                resource.properties["shared:originalName"][0].value
                for resource in prepared.resources
            ],
            ["DC_0015.HEIC", "DC_0015.HEIC"],
        )
        self.assertIn("# This comment", prepared_source)
        self.assertIn("# first independent camera file", prepared_source)

    def test_json_preparation_keeps_json_syntax(self) -> None:
        payload = {
            "data": {
                "version": 1,
                "project": "chama",
                "resources": [
                    {
                        "iri": "auto",
                        "class": "chama:Place",
                        "properties": {"schema:name": [{"value": "A place"}]},
                    }
                ],
            }
        }

        prepared = prepare_data_source(
            json.dumps(payload),
            uuid_factory=lambda: UUID(int=3),
        )

        parsed = json.loads(prepared)
        self.assertEqual(
            parsed["data"]["resources"][0]["iri"],
            "resource_00000000000000000000000000000003",
        )

    def test_file_preparation_refuses_in_place_and_implicit_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inf = Path(directory) / "incoming.yaml"
            out = Path(directory) / "prepared.yaml"
            inf.write_text(AUTO_YAML, encoding="utf-8")

            with self.assertRaisesRegex(DataValidationError, "must differ"):
                prepare_data_file(inf, inf)

            count = prepare_data_file(
                inf,
                out,
                uuid_factory=self._uuid_factory(),
            )
            self.assertEqual(count, 2)
            with self.assertRaisesRegex(DataValidationError, "already exists"):
                prepare_data_file(inf, out)

    def test_prepare_cli_writes_the_authoritative_output_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inf = Path(directory) / "incoming.yaml"
            out = Path(directory) / "prepared.yaml"
            inf.write_text(AUTO_YAML, encoding="utf-8")

            result = self.runner.invoke(
                app,
                ["data", "prepare", "--inf", str(inf), "--out", str(out)],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Prepared 2 resource IRI(s)", result.output)
            self.assertTrue(out.is_file())
            self.assertEqual(loads_data_document(out.read_text()).auto_iri_count, 0)

    def test_same_filenames_in_different_directories_get_distinct_asset_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "camera-a" / "DC_0015.HEIC"
            second = root / "camera-b" / "DC_0015.HEIC"
            first.parent.mkdir()
            second.parent.mkdir()
            first.write_bytes(b"first independent photograph")
            second.write_bytes(b"second independent photograph")
            digests = [
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            ]
            resources = []
            for index, (relative_path, digest) in enumerate(
                (("camera-a/DC_0015.HEIC", digests[0]),
                 ("camera-b/DC_0015.HEIC", digests[1])),
                start=1,
            ):
                resources.append(
                    f"""\
    - iri: auto
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: Photograph {index}
            language: en
        dcterms:type:
          - iri: dcmitype:StillImage
        shared:mediaAccessMode:
          - value: local
        shared:originalName:
          - value: DC_0015.HEIC
        shared:originalMimeType:
          - value: image/heic
        shared:checksum:
          - value: {digest}
        shared:protocol:
          - value: custom
      media:
        source:
          type: file
          path: {relative_path}
        handling: copy
        ingest_profile: image-iiif
"""
                )
            inf = root / "incoming.yaml"
            out = root / "prepared.yaml"
            inf.write_text(
                "data:\n  version: 1\n  project: chama\n  resources:\n"
                + "".join(resources),
                encoding="utf-8",
            )
            prepare_data_file(
                inf,
                out,
                uuid_factory=self._uuid_factory(),
            )

            plans = prepare_document_media(load_data_document(out))

            self.assertEqual([plan.original_name for plan in plans], ["DC_0015.HEIC"] * 2)
            self.assertEqual(len({plan.asset_id for plan in plans}), 2)
            self.assertEqual([plan.checksum for plan in plans], digests)


if __name__ == "__main__":
    unittest.main()
