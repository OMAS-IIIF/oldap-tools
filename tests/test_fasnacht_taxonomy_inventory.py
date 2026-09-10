from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from oldap_tools.fasnacht_taxonomy_inventory import (
    build_inventory_report,
    build_list_node_query,
    build_taxonomy_usage_query,
    load_mapping,
    validate_mapping_coverage,
    validate_mapping_targets,
    write_inventory_report,
)


FASNACHT_DIR = Path(__file__).parents[1] / "fasnacht"
MAPPING_PATH = FASNACHT_DIR / "TaxonomyPhase1Mapping.yaml"


def binding(**values: str) -> dict[str, dict[str, str]]:
    return {key: {"type": "uri" if value.startswith("http") else "literal", "value": value} for key, value in values.items()}


class FasnachtTaxonomyInventoryTest(unittest.TestCase):
    def test_mapping_covers_all_active_source_taxonomies(self) -> None:
        mapping = load_mapping(MAPPING_PATH)
        validate_mapping_coverage(mapping, {
            "ObjectTaxonomy": FASNACHT_DIR / "ObjectTaxonomy-PrePhase2.yaml",
            "CarnivalEventTaxonomy": FASNACHT_DIR / "CarnivalEventTaxonomy-PrePhase2.yaml",
            "CarnivalTopicsTaxonomy": FASNACHT_DIR / "CarnivalTopicsTaxonomy.yaml",
            "OrganisationTaxonomy": FASNACHT_DIR / "OrganisationTaxonomy.yaml",
        })
        validate_mapping_targets(mapping, {
            "ObjectTaxonomy": FASNACHT_DIR / "ObjectTaxonomy.yaml",
            "CarnivalEventTaxonomy": FASNACHT_DIR / "CarnivalEventTaxonomy.yaml",
            "CarnivalPracticeTaxonomy": FASNACHT_DIR / "CarnivalPracticeTaxonomy.yaml",
        })
        self.assertEqual(mapping["CarnivalEventTaxonomy"]["HistorischAnderes"].source_state, "legacy")
        self.assertEqual(mapping["OrganisationTaxonomy"]["Stamm"].source_state, "legacy")

    def test_usage_query_is_read_only_and_includes_orphan_prefix_scan(self) -> None:
        query = build_taxonomy_usage_query(
            "http://fasnacht.digital/ns/",
            ["ObjectTaxonomy", "CarnivalEventTaxonomy"],
        )
        self.assertIn("SELECT", query)
        self.assertIn("STRSTARTS", query)
        self.assertIn("http://fasnacht.digital/ns/ObjectTaxonomy#", query)
        self.assertNotIn("INSERT", query)
        self.assertNotIn("DELETE", query)

    def test_list_query_derives_virtual_node_id_from_iri(self) -> None:
        query = build_list_node_query(
            "http://fasnacht.digital/ns/",
            ["ObjectTaxonomy"],
        )
        self.assertIn("STRAFTER", query)
        self.assertIn("http://fasnacht.digital/ns/ObjectTaxonomy#", query)
        self.assertNotIn("oldapListNodeId", query)

    def test_report_marks_only_unreferenced_empty_year_events_for_deletion(self) -> None:
        mapping = load_mapping(MAPPING_PATH)
        namespace = "http://fasnacht.digital/ns/"
        report = build_inventory_report(
            project_id="fasnacht",
            namespace=namespace,
            mapping=mapping,
            node_bindings=[],
            usage_bindings=[],
            event_outgoing_bindings=[
                binding(event="http://example.org/1920", name="Fasnacht 1920", property="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", value=f"{namespace}CarnivalEvent"),
                binding(event="http://example.org/1921", name="Fasnacht 1921", property="https://schema.org/description", value="Documented event"),
                binding(event="http://example.org/1922", name="Fasnacht 1922", property="https://schema.org/name", value="Fasnacht 1922"),
            ],
            event_incoming_bindings=[
                binding(event="http://example.org/1922", source="http://example.org/media", property=f"{namespace}archiveMediaObjectOf"),
            ],
            generated_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        )
        events = {item["name"]: item for item in report["events"]["items"]}
        self.assertTrue(events["Fasnacht 1920"]["deletionCandidate"])
        self.assertTrue(events["Fasnacht 1920"]["reviewCandidate"])
        self.assertFalse(events["Fasnacht 1921"]["deletionCandidate"])
        self.assertTrue(events["Fasnacht 1921"]["reviewCandidate"])
        self.assertFalse(events["Fasnacht 1922"]["deletionCandidate"])
        self.assertFalse(events["Fasnacht 1922"]["reviewCandidate"])
        self.assertEqual(events["Fasnacht 1922"]["mediaReferenceCount"], 1)

    def test_report_exposes_unknown_referenced_nodes(self) -> None:
        mapping = load_mapping(MAPPING_PATH)
        namespace = "http://fasnacht.digital/ns/"
        report = build_inventory_report(
            project_id="fasnacht",
            namespace=namespace,
            mapping=mapping,
            node_bindings=[],
            usage_bindings=[binding(
                listId="ObjectTaxonomy",
                node=f"{namespace}ObjectTaxonomy#Legacy",
                nodeId="Legacy",
                resource="http://example.org/object",
                property="http://purl.org/dc/terms/type",
                resourceClass=f"{namespace}ArchiveObject",
                resourceName="Legacy object",
            )],
            event_outgoing_bindings=[],
            event_incoming_bindings=[],
        )
        object_list = next(item for item in report["taxonomyLists"] if item["listId"] == "ObjectTaxonomy")
        legacy = next(item for item in object_list["nodes"] if item["nodeId"] == "Legacy")
        self.assertEqual(legacy["mappingMode"], "unmapped")
        self.assertFalse(legacy["presentInList"])
        self.assertEqual(legacy["usageCount"], 1)

    def test_report_writer_rejects_ambiguous_extension(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "json"):
                write_inventory_report(Path(directory) / "report.txt", {"version": 1})


if __name__ == "__main__":
    unittest.main()
