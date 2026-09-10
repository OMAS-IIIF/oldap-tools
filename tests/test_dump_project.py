import unittest

from oldap_tools.dump_project import graphdb_http_auth


class GraphDbHttpAuthTests(unittest.TestCase):
    def test_returns_basic_auth_pair_for_protected_export(self) -> None:
        self.assertEqual(
            ("graph-user", "graph-password"),
            graphdb_http_auth("graph-user", "graph-password"),
        )

    def test_returns_none_for_unprotected_export(self) -> None:
        self.assertIsNone(graphdb_http_auth(None, None))

    def test_rejects_partial_credentials(self) -> None:
        with self.assertRaisesRegex(ValueError, "both username and password"):
            graphdb_http_auth("graph-user", None)


if __name__ == "__main__":
    unittest.main()
