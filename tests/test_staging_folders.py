"""Unit tests for idempotent StagingArea Mobile-folder planning."""

import unittest

from oldap_tools.staging_folders import (
    MobileFolderPlan,
    StagingAreaRecord,
    StagingFolderRecord,
    plan_mobile_folder,
)


class MobileFolderPlanTest(unittest.TestCase):
    """Verify hierarchy validation without requiring a GraphDB instance."""

    area = StagingAreaRecord("fasnacht:area", "fasnacht:Depositor")
    top = StagingFolderRecord("fasnacht:top", "fasnacht:area", "top", "")

    def test_missing_mobile_folder_requires_creation(self) -> None:
        plan = plan_mobile_folder(self.area, [self.top])

        self.assertIsInstance(plan, MobileFolderPlan)
        self.assertTrue(plan.needs_creation)
        self.assertEqual(plan.top_folder_iri, "fasnacht:top")

    def test_existing_mobile_folder_is_a_no_op(self) -> None:
        mobile = StagingFolderRecord(
            "fasnacht:mobile",
            "fasnacht:area",
            "Mobile",
            "fasnacht:top",
        )

        plan = plan_mobile_folder(self.area, [self.top, mobile])

        self.assertFalse(plan.needs_creation)
        self.assertEqual(plan.existing_mobile_folder_iri, "fasnacht:mobile")

    def test_rejects_mobile_folder_outside_top(self) -> None:
        misplaced = StagingFolderRecord(
            "fasnacht:mobile",
            "fasnacht:area",
            "Mobile",
            "fasnacht:user-folder",
        )

        with self.assertRaisesRegex(ValueError, "noncanonical Mobile"):
            plan_mobile_folder(self.area, [self.top, misplaced])

    def test_rejects_noncanonical_mobile_name(self) -> None:
        misplaced = StagingFolderRecord(
            "fasnacht:mobile",
            "fasnacht:area",
            "mobile",
            "fasnacht:top",
        )

        with self.assertRaisesRegex(ValueError, "noncanonical Mobile"):
            plan_mobile_folder(self.area, [self.top, misplaced])

    def test_rejects_ambiguous_top_folder(self) -> None:
        duplicate_top = StagingFolderRecord("fasnacht:top-2", "fasnacht:area", "top", "")

        with self.assertRaisesRegex(ValueError, "exactly one root folder"):
            plan_mobile_folder(self.area, [self.top, duplicate_top])


if __name__ == "__main__":
    unittest.main()
