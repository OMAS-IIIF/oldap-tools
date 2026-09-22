"""Regression tests for incremental ontology property synchronization."""

import unittest
from types import SimpleNamespace

from oldaplib.src.enums.propertyclassattr import PropClassAttr
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.ontology import _dump_property, _sync_property, _sync_resource


class _PropertyStub:
    """Minimal mutable PropertyClass interface used by the synchronizer."""

    def __init__(self) -> None:
        self.values = {
            PropClassAttr.CLASS: Xsd_QName("chama:Agent", validate=False),
        }

    def get(self, attr: PropClassAttr):
        """Return the current value for one OLDAP property attribute."""
        return self.values.get(attr)

    def __setitem__(self, attr: PropClassAttr, value) -> None:
        """Record a synchronized attribute value."""
        self.values[attr] = value


class TestOntologyPropertySync(unittest.TestCase):
    """Verify YAML aliases update the corresponding OLDAP attributes."""

    def test_to_class_replaces_existing_shacl_class(self) -> None:
        existing = _PropertyStub()

        _sync_property(
            existing,
            {"iri": "schema:author", "to_class": "chama:Person"},
            {},
        )

        self.assertEqual(str(existing.values[PropClassAttr.CLASS]), "chama:Person")

    def test_dump_uses_canonical_to_class_key(self) -> None:
        prop = SimpleNamespace(
            property_class_iri=Xsd_QName("schema:author", validate=False),
            _attributes={PropClassAttr.CLASS: Xsd_QName("chama:Person", validate=False)},
        )

        self.assertEqual(
            _dump_property(prop),
            {"iri": "schema:author", "to_class": "chama:Person"},
        )

    def test_direct_sync_preserves_omitted_properties_by_default(self) -> None:
        iri = Xsd_QName("chama:legacy", validate=False)
        class ResourceStub(dict):
            def properties_items(self):
                return self.items()
        existing = ResourceStub({iri: object()})
        _sync_resource(existing, {"properties": []}, None, {})
        self.assertIn(iri, existing)
        _sync_resource(existing, {"properties": []}, None, {}, remove_unused=True)
        self.assertNotIn(iri, existing)


if __name__ == "__main__":
    unittest.main()
