"""Unit tests for archive YAML parsing and create-only import planning."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.xsd.iri import Iri

from oldap_tools.archive import (
    ArchiveImportPlan,
    apply_archive_import,
    prepare_archive_import,
    read_archive_yaml,
)


VALID_YAML = """\
archive:
  version: 1
  language: de
  units:
    - id: bmg
      level: Fonds
      title:
        de: Archiv BMG
        en: BMG Archive
      identifier: BMG
      date:
        start: "1911"
        end: "2026"
      children:
        - id: bmg-stamm
          level: Subfonds
          title: Stamm
          position: 1
"""


class ArchiveYamlTest(unittest.TestCase):
    """Verify normalization rules without requiring GraphDB."""

    def _yaml_file(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self.addCleanup(Path(handle.name).unlink, missing_ok=True)
        with handle:
            handle.write(content)
        return Path(handle.name)

    def test_reads_recursive_tree_and_builds_stable_project_iris(self) -> None:
        definition = read_archive_yaml(self._yaml_file(VALID_YAML), "fasnacht")

        self.assertEqual([unit.unit_id for unit in definition.units], ["bmg", "bmg-stamm"])
        self.assertEqual(str(definition.units[0].iri), "fasnacht:bmg")
        self.assertIsNone(definition.units[0].parent_iri)
        self.assertEqual(definition.units[1].parent_iri, Iri("fasnacht:bmg"))
        self.assertEqual(definition.units[1].title, LangString("Stamm@de"))

    def test_accepts_external_parent_on_top_level_unit(self) -> None:
        content = VALID_YAML.replace("      level: Fonds", "      level: Fonds\n      parent: fasnacht:archive-group", 1)

        definition = read_archive_yaml(self._yaml_file(content), "fasnacht")

        self.assertEqual(definition.units[0].parent_iri, Iri("fasnacht:archive-group"))

    def test_rejects_parent_on_nested_unit(self) -> None:
        content = VALID_YAML.replace("          level: Subfonds", "          level: Subfonds\n          parent: fasnacht:other")

        with self.assertRaisesRegex(ValueError, "must not define"):
            read_archive_yaml(self._yaml_file(content), "fasnacht")

    def test_rejects_duplicate_ids(self) -> None:
        content = VALID_YAML.replace("id: bmg-stamm", "id: bmg")

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            read_archive_yaml(self._yaml_file(content), "fasnacht")

    def test_rejects_invalid_unit_id(self) -> None:
        content = VALID_YAML.replace("id: bmg-stamm", "id: invalid/id")

        with self.assertRaisesRegex(ValueError, "valid NCName"):
            read_archive_yaml(self._yaml_file(content), "fasnacht")

    def test_rejects_existing_target_resource(self) -> None:
        definition = read_archive_yaml(self._yaml_file(VALID_YAML), "fasnacht")
        factory = Mock()
        factory.read.return_value = Mock()

        with self.assertRaisesRegex(ValueError, "never overwritten"):
            prepare_archive_import(factory, "fasnacht", definition)

    def test_preflight_accepts_visible_archive_unit_as_external_parent(self) -> None:
        content = VALID_YAML.replace(
            "      level: Fonds",
            "      level: Fonds\n      parent: fasnacht:archive-group",
            1,
        )
        definition = read_archive_yaml(self._yaml_file(content), "fasnacht")
        parent = Mock()
        parent.__class__.name = "shared:ArchiveUnit"
        factory = Mock()

        def read(iri: Iri):
            if iri == Iri("fasnacht:archive-group"):
                return parent
            raise OldapErrorNotFound(str(iri))

        factory.read.side_effect = read

        plan = prepare_archive_import(factory, "fasnacht", definition)

        self.assertEqual(plan.external_parent_iris, (Iri("fasnacht:archive-group"),))

    def test_apply_rolls_back_created_units_after_failure(self) -> None:
        definition = read_archive_yaml(self._yaml_file(VALID_YAML), "fasnacht")
        deleted: list[Iri] = []

        class FakeArchiveUnit:
            def __init__(self, *, iri: Iri, **values):
                self.iri = iri
                self.values = values

            def create(self) -> None:
                if self.iri == Iri("fasnacht:bmg-stamm"):
                    raise RuntimeError("simulated failure")

        class ExistingUnit:
            def __init__(self, iri: Iri):
                self.iri = iri

            def delete(self) -> None:
                deleted.append(self.iri)

        factory = Mock()
        factory.createObjectInstance.return_value = FakeArchiveUnit
        factory.read.side_effect = lambda iri: ExistingUnit(iri)
        plan = ArchiveImportPlan("fasnacht", definition.units)

        with self.assertRaisesRegex(RuntimeError, "were rolled back"):
            apply_archive_import(factory, plan)

        self.assertEqual(deleted, [Iri("fasnacht:bmg")])


if __name__ == "__main__":
    unittest.main()
