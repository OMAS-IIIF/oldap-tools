from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import unittest

from oldap_tools.fasnacht_taxonomy_inventory import MappingRule
from oldap_tools.fasnacht_taxonomy_migration import (
    build_data_reference_update,
    build_flat_list_replacement_update,
    build_migration_plan,
    build_practice_model_cutover_update,
    load_phase2_decisions,
)


class FasnachtTaxonomyMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = "http://fasnacht.digital/ns/"
        self.mapping = {
            "ObjectTaxonomy": {
                "Laterne": MappingRule(
                    "ObjectTaxonomy", "Laterne", "ObjectTaxonomy", ("Laterne",), "exact"
                ),
                "Undetermined": MappingRule(
                    "ObjectTaxonomy", "Undetermined", "ObjectTaxonomy", (), "review"
                ),
            },
        }

    def _inventory(self, name: str = "Fasnachtsplakette 1957") -> dict:
        return {
            "project": "fasnacht",
            "namespace": self.namespace,
            "taxonomyLists": [{
                "listId": "ObjectTaxonomy",
                "nodes": [
                    {
                        "nodeId": "Laterne",
                        "iri": f"{self.namespace}ObjectTaxonomy#Laterne",
                        "usageCount": 1,
                        "usages": [{
                            "resource": "urn:uuid:lantern",
                            "property": "http://purl.org/dc/terms/type",
                            "name": "Laterne",
                            "classes": [f"{self.namespace}ArchiveObject"],
                        }],
                    },
                    {
                        "nodeId": "Undetermined",
                        "iri": f"{self.namespace}ObjectTaxonomy#Undetermined",
                        "usageCount": 1,
                        "usages": [{
                            "resource": "urn:uuid:badge",
                            "property": "http://purl.org/dc/terms/type",
                            "name": name,
                            "classes": [f"{self.namespace}ArchiveObject"],
                        }],
                    },
                ],
            }],
        }

    def _decisions(self) -> dict:
        rule = load_phase2_decisions(
            Path(__file__).parents[1] / "fasnacht" / "TaxonomyPhase2LocalDecisions.yaml"
        )["review_match_rules"][0]
        return {
            "version": 1,
            "status": "local-rehearsal",
            "included_lists": ("ObjectTaxonomy",),
            "approved_modes": frozenset({"exact", "broader"}),
            "target_properties": {"ObjectTaxonomy": "http://purl.org/dc/terms/type"},
            "review_match_rules": (replace(rule, expected_count=1),),
        }

    def test_build_plan_resolves_review_and_keeps_exact_reference_unchanged(self) -> None:
        plan = build_migration_plan(
            inventory=self._inventory(),
            mapping=self.mapping,
            decisions=self._decisions(),
            generated_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
        )

        self.assertTrue(plan["readyToApply"])
        self.assertEqual(1, plan["summary"]["actionableReferenceCount"])
        self.assertEqual(1, plan["summary"]["unchangedReferenceCount"])
        self.assertEqual("Plakette", plan["actions"][0]["targetNodeIris"][0].split("#")[-1])

    def test_changed_title_fails_closed(self) -> None:
        plan = build_migration_plan(
            inventory=self._inventory(name="Unbekanntes Objekt"),
            mapping=self.mapping,
            decisions=self._decisions(),
        )

        self.assertFalse(plan["readyToApply"])
        self.assertEqual(1, plan["summary"]["unresolvedReferenceCount"])
        self.assertEqual(1, plan["summary"]["ruleCountErrorCount"])

    def test_overlapping_review_rules_are_rejected(self) -> None:
        decisions = self._decisions()
        decisions["review_match_rules"] = decisions["review_match_rules"] * 2
        with self.assertRaisesRegex(ValueError, "Multiple Phase-2 review rules"):
            build_migration_plan(
                inventory=self._inventory(),
                mapping=self.mapping,
                decisions=decisions,
            )

    def test_non_archive_taxonomy_reference_blocks_plan(self) -> None:
        inventory = self._inventory()
        inventory["taxonomyLists"][0]["nodes"][1]["usages"][0]["classes"] = [
            f"{self.namespace}NewsItem"
        ]

        plan = build_migration_plan(
            inventory=inventory,
            mapping=self.mapping,
            decisions=self._decisions(),
        )

        self.assertFalse(plan["readyToApply"])
        self.assertEqual(1, plan["summary"]["outOfScopeReferenceCount"])
        self.assertEqual(f"{self.namespace}NewsItem", plan["outOfScope"][0]["resourceClasses"][0])

    def test_data_update_replaces_only_materialized_reference(self) -> None:
        plan = build_migration_plan(
            inventory=self._inventory(),
            mapping=self.mapping,
            decisions=self._decisions(),
        )
        update = build_data_reference_update(plan)

        self.assertIn("DELETE DATA", update)
        self.assertIn("ObjectTaxonomy#Undetermined", update)
        self.assertIn("ObjectTaxonomy#Plakette", update)
        self.assertNotIn("ObjectTaxonomy#Laterne", update)

    def test_flat_list_replacement_has_ordered_root_indices(self) -> None:
        update = build_flat_list_replacement_update(
            namespace=self.namespace,
            taxonomy_path=Path(__file__).parents[1] / "fasnacht" / "CarnivalPracticeTaxonomy.yaml",
            contributor_iri="https://orcid.org/0000-0000-0000-0000",
        )

        self.assertIn("CarnivalPracticeTaxonomy#CraftAndArt", update)
        self.assertIn("oldap:leftIndex 1", update)
        self.assertIn("oldap:rightIndex 8", update)
        self.assertNotIn("skos:broader", update)

    def test_practice_model_cutover_is_narrowly_scoped(self) -> None:
        update = build_practice_model_cutover_update(self.namespace)

        self.assertIn("CarnivalThingShape", update)
        self.assertIn("ArchiveMediaObjectShape", update)
        self.assertIn("CarnivalPracticeTaxonomyNode", update)
        self.assertIn("dcterms:subject", update)
        self.assertNotIn("CLEAR GRAPH", update)


if __name__ == "__main__":
    unittest.main()
