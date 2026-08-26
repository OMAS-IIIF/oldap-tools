"""Tests for portable media-source preflight and integrity validation."""

from pathlib import Path
import hashlib
import tempfile
import unittest
from unittest.mock import patch

from oldap_tools.data_yaml import load_data_document
from oldap_tools.media_ingest import (
    MediaIngestError,
    attach_media_copy,
    prepare_document_media,
)


class MediaIngestPreflightTest(unittest.TestCase):
    """Exercise filesystem media checks without OLDAP or HTTP services."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.asset = self.root / "photo.heic"
        self.asset.write_bytes(b"representative HEIC bytes")
        self.digest = hashlib.sha256(self.asset.read_bytes()).hexdigest()

    def _document(self, *, checksum: str | None = None):
        yaml_path = self.root / "record.yaml"
        yaml_path.write_text(
            f"""\
data:
  version: 1
  project: chama
  resources:
    - iri: Photo1
      class: chama:CataloguedPhotograph
      properties:
        dcterms:type:
          - iri: dcmitype:StillImage
        shared:mediaAccessMode:
          - value: local
        shared:originalName:
          - value: photo.heic
        shared:originalMimeType:
          - value: image/heic
        shared:checksum:
          - value: {checksum or self.digest}
        shared:protocol:
          - value: custom
      media:
        source:
          type: file
          path: photo.heic
        handling: copy
        ingest_profile: image-iiif
""",
            encoding="utf-8",
        )
        return load_data_document(yaml_path)

    def test_prepares_relative_file_with_verified_identity(self) -> None:
        plan = prepare_document_media(self._document())[0]

        self.assertEqual(plan.resource_iri, "chama:Photo1")
        self.assertEqual(plan.asset_id, "Photo1")
        self.assertEqual(plan.source_path, self.asset.resolve())
        self.assertEqual(plan.checksum, self.digest)
        self.assertEqual(plan.ingest_profile, "image-iiif")

    def test_rejects_checksum_mismatch_before_network_or_write(self) -> None:
        with self.assertRaisesRegex(MediaIngestError, "checksum mismatch"):
            prepare_document_media(self._document(checksum="0" * 64))

    @patch("oldap_tools.media_ingest._request_json")
    def test_uploads_and_verifies_oldap_and_iiif_delivery(self, request_json) -> None:
        plan = prepare_document_media(self._document())[0]
        delivered = {
            "shared:assetId": "Photo1",
            "shared:originalName": "photo.heic",
            "shared:originalMimeType": "image/heic",
            "shared:checksum": self.digest,
            "shared:mediaAccessMode": "local",
            "shared:protocol": "iiif",
            "shared:derivativeName": "master.tif",
            "shared:path": "chama/image/catalogue",
            "shared:serverUrl": "http://media.test/iiif/3/",
            "token": "capability",
        }
        request_json.side_effect = [
            {"shared:assetId": None},
            {"attachedToExistingResource": True},
            delivered,
            {
                "id": "http://media.test/iiif/3/Photo1",
                "width": 2000,
                "height": 1000,
            },
        ]

        result = attach_media_copy(
            plan,
            api_base="http://api.test",
            media_base="http://media.test",
            token="access",
        )

        self.assertTrue(result.imported_now)
        self.assertEqual(result.iiif_info_url, "http://media.test/iiif/3/Photo1/info.json")
        self.assertEqual((result.width, result.height), (2000, 1000))
        upload = request_json.call_args_list[1]
        self.assertEqual(upload.args, ("POST", "http://media.test/upload"))
        self.assertEqual(upload.kwargs["data"]["existingResourceIri"], "chama:Photo1")
        self.assertEqual(upload.kwargs["data"]["targetFormat"], "tiff")
        self.assertEqual(upload.kwargs["files"]["file"][0:3:2], ("photo.heic", "image/heic"))


if __name__ == "__main__":
    unittest.main()
