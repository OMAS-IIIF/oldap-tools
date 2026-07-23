"""Tests for the shared direct-connection boundary."""

import unittest
from unittest.mock import patch

from oldap_tools.connection import create_connection


class TestCreateConnection(unittest.TestCase):
    """Verify secure and complete forwarding to `oldaplib.Connection`."""

    @patch("oldap_tools.connection.Connection")
    def test_disables_access_token_issuance(self, connection_mock) -> None:
        expected_connection = connection_mock.return_value

        result = create_connection(
            graphdb_base="https://graphdb.example",
            repo="oldap",
            user="admin",
            password="secret",
            graphdb_user="graphdb-user",
            graphdb_password="graphdb-secret",
            context_name="DEFAULT",
        )

        self.assertIs(result, expected_connection)
        connection_mock.assert_called_once_with(
            server="https://graphdb.example",
            repo="oldap",
            dbuser="graphdb-user",
            dbpassword="graphdb-secret",
            userId="admin",
            credentials="secret",
            issue_access_token=False,
            context_name="DEFAULT",
        )

    @patch("oldap_tools.connection.Connection")
    def test_preserves_oldaplib_default_context(self, connection_mock) -> None:
        create_connection(
            graphdb_base="http://localhost:7200",
            repo="oldap",
            user="admin",
            password="secret",
        )

        self.assertNotIn("context_name", connection_mock.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
