"""Tests for external ontology YAML import/export behavior."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import yaml
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.enums.externalontologyattr import ExternalOntologyAttr

from oldap_tools.ontology import (
    _build_external_ontology,
    _dump_external_ontology,
    dump_ontology,
    validate_ontology_yaml,
)


class TestExternalOntologyYaml(unittest.TestCase):
    """Verify that external ontology metadata survives a YAML roundtrip."""

    def test_dump_emits_all_supported_external_ontology_fields(self) -> None:
        values = {
            ExternalOntologyAttr.NAMESPACE_IRI: NamespaceIRI("http://xmlns.com/foaf/0.1/"),
            ExternalOntologyAttr.LABEL: {"en": "Friend of a Friend"},
            ExternalOntologyAttr.COMMENT: {"en": "FOAF vocabulary"},
            ExternalOntologyAttr.PROPOSED_RESOURCE_CLASS: {"Agent", "Person"},
            ExternalOntologyAttr.PROPOSED_DATATYPE_PROPERTY_CLASS: {"givenName", "familyName"},
            ExternalOntologyAttr.PROPOSED_OBJECT_PROPERTY_CLASS: {"knows"},
        }
        ontology = Mock()
        ontology.get.side_effect = values.get

        result = _dump_external_ontology(ontology)

        self.assertEqual(
            result,
            {
                "namespace": "http://xmlns.com/foaf/0.1/",
                "label": {"en": "Friend of a Friend"},
                "comment": {"en": "FOAF vocabulary"},
                "proposedResourceClass": ["Agent", "Person"],
                "proposedDatatypePropertyClass": ["familyName", "givenName"],
                "proposedObjectPropertyClass": ["knows"],
            },
        )

    @patch("oldap_tools.ontology.ExternalOntology")
    def test_import_accepts_canonical_export_fields(self, external_ontology_mock) -> None:
        connection = Mock()
        project = SimpleNamespace(projectShortName="fasnacht")
        spec = {
            "namespace": "http://xmlns.com/foaf/0.1/",
            "label": {"en": "Friend of a Friend"},
            "comment": {"en": "FOAF vocabulary"},
            "proposedResourceClass": ["Agent", "Person"],
            "proposedDatatypePropertyClass": ["familyName", "givenName"],
            "proposedObjectPropertyClass": ["knows"],
        }

        _build_external_ontology(connection, project, "foaf", spec)

        kwargs = external_ontology_mock.call_args.kwargs
        self.assertEqual(str(kwargs["prefix"]), "foaf")
        self.assertEqual(str(kwargs["namespaceIri"]), spec["namespace"])
        self.assertEqual(kwargs["proposedResourceClass"], {"Agent", "Person"})
        self.assertEqual(kwargs["proposedDatatypePropertyClass"], {"familyName", "givenName"})
        self.assertEqual(kwargs["proposedObjectPropertyClass"], {"knows"})

    @patch("oldap_tools.ontology._dump_lucene_connector", return_value=None)
    @patch("oldap_tools.ontology.DataModel.read")
    @patch("oldap_tools.ontology.Project.read")
    @patch("oldap_tools.ontology._connect")
    def test_yaml_dump_includes_external_ontologies(
        self,
        connect_mock,
        project_read_mock,
        datamodel_read_mock,
        _connector_mock,
    ) -> None:
        project = SimpleNamespace(
            projectShortName="fasnacht",
            projectIri="https://fasnacht.digital",
            namespaceIri="http://fasnacht.digital/ns/",
        )
        project_read_mock.return_value = project
        external = Mock()
        values = {
            ExternalOntologyAttr.PREFIX: "foaf",
            ExternalOntologyAttr.NAMESPACE_IRI: "http://xmlns.com/foaf/0.1/",
            ExternalOntologyAttr.LABEL: {"en": "Friend of a Friend"},
            ExternalOntologyAttr.COMMENT: None,
            ExternalOntologyAttr.PROPOSED_RESOURCE_CLASS: set(),
            ExternalOntologyAttr.PROPOSED_DATATYPE_PROPERTY_CLASS: {"familyName", "givenName"},
            ExternalOntologyAttr.PROPOSED_OBJECT_PROPERTY_CLASS: set(),
        }
        external.get.side_effect = values.get
        model = Mock()
        model.get_extontos.return_value = ["fasnacht:foaf"]
        model.get_resclasses.return_value = []
        model.__getitem__ = Mock(return_value=external)
        datamodel_read_mock.return_value = model

        with TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "ontology.yaml"
            dump_ontology(
                graphdb_base="http://localhost:7200",
                repo="oldap",
                project_id="fasnacht",
                out=out,
                fmt="yaml",
                user="admin",
                password="secret",
            )
            validate_ontology_yaml(out)
            exported = yaml.safe_load(out.read_text(encoding="utf-8"))

        self.assertEqual(
            exported["ontology"]["external_ontologies"]["foaf"],
            {
                "namespace": "http://xmlns.com/foaf/0.1/",
                "label": {"en": "Friend of a Friend"},
                "proposedDatatypePropertyClass": ["familyName", "givenName"],
            },
        )
        connect_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
