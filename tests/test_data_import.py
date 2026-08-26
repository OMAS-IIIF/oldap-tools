"""Tests for the read-only, ontology-aware instance-data preflight."""

from dataclasses import dataclass
import unittest

from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.data_import import (
    DataImportPreflightError,
    apply_data_import,
    prepare_data_import,
)
from oldap_tools.data_yaml import DataValidationError, loads_data_document


@dataclass
class FakeProperty:
    """Minimal property interface consumed by the preflight."""

    datatype: XsdDatatypes | None = None
    toClass: Xsd_QName | None = None
    inSet: set[Iri] | None = None


class FakeConnection:
    """Connection-shaped object exposing an isolated OLDAP context."""

    context_name = "DATA_IMPORT_TEST"


class FakeCataloguedPhotograph:
    """Dynamic-class substitute that records in-memory construction values."""

    name = Xsd_QName("chama:CataloguedPhotograph", validate=False)
    superclass = {Xsd_QName("oldap:Thing", validate=False): None}
    last_kwargs = None
    created_iris = []
    properties = {
        Xsd_QName("schema:name", validate=False): FakeProperty(
            datatype=XsdDatatypes.langString
        ),
        Xsd_QName("dcterms:creator", validate=False): FakeProperty(
            toClass=Xsd_QName("chama:Agent", validate=False)
        ),
        Xsd_QName("chama:capturePlace", validate=False): FakeProperty(
            toClass=Xsd_QName("chama:Place", validate=False)
        ),
        Xsd_QName("chama:creationDating", validate=False): FakeProperty(
            toClass=Xsd_QName("oldap:Dating", validate=False)
        ),
        Xsd_QName("chama:publicDisplayPermission", validate=False): FakeProperty(
            datatype=XsdDatatypes.boolean
        ),
        Xsd_QName("shared:archiveLevel", validate=False): FakeProperty(
            toClass=Xsd_QName("shared:ArchiveLevel", validate=False),
            inSet={Iri("shared:ArchiveGroup", validate=False)},
        ),
    }

    @classmethod
    def resolved_properties(cls):
        return cls.properties

    def __init__(self, *, iri, **kwargs):
        if "schema:name" not in kwargs:
            raise ValueError("schema:name with MIN_COUNT=1 is missing")
        self.iri = iri
        self.values = kwargs
        type(self).last_kwargs = kwargs

    def get(self, key):
        """Return constructor values through the ResourceInstance read interface."""

        if str(key) == "oldap:attachedToRole":
            return self.values.get("attachedToRole")
        return self.values.get(str(key))

    def check_for_permissions(self, _permission):
        return True, "OK"

    def create(self):
        type(self).created_iris.append(str(self.iri))


class FakeAgent:
    name = Xsd_QName("chama:Person", validate=False)
    superclass = {Xsd_QName("chama:Agent", validate=False): None}


class FakePlace:
    name = Xsd_QName("chama:Place", validate=False)
    superclass = {Xsd_QName("oldap:Thing", validate=False): None}


class FakeFactory:
    """Read-only factory with configurable visible resources."""

    def __init__(self, visible=None):
        self.visible = visible or {
            "chama:LukasRosenthaler": FakeAgent(),
            "chama:ChamaStation": FakePlace(),
        }

    def createObjectInstance(self, class_iri):
        if str(class_iri) != "chama:CataloguedPhotograph":
            raise OldapErrorNotFound(f"Unknown class {class_iri}")
        return FakeCataloguedPhotograph

    def read(self, iri):
        value = self.visible.get(str(iri))
        if value is None:
            raise OldapErrorNotFound(str(iri))
        return value


VALID_DATA = """\
data:
  version: 1
  project: chama
  resources:
    - iri: IMG_1520
      class: chama:CataloguedPhotograph
      properties:
        schema:name:
          - value: Stationsgebäude in Chama
            language: de
        dcterms:creator:
          - iri: chama:LukasRosenthaler
        chama:capturePlace:
          - iri: chama:ChamaStation
        chama:creationDating:
          - value: "2018-07-08"
        chama:publicDisplayPermission:
          - value: true
      permissions:
        oldap:Unknown: DATA_VIEW
"""


class DataImportPreflightTest(unittest.TestCase):
    """Exercise preflight behavior without GraphDB or write methods."""

    @classmethod
    def setUpClass(cls):
        context = Context(name=FakeConnection.context_name)
        context["chama"] = "https://chama.salsah.org/ns/"

    def prepare(self, source=VALID_DATA, factory=None, role_reader=None):
        return prepare_data_import(
            FakeConnection(),
            factory or FakeFactory(),
            loads_data_document(source),
            role_reader=role_reader or (lambda _role: object()),
        )

    def setUp(self):
        FakeCataloguedPhotograph.created_iris = []

    def test_prepares_typed_values_links_roles_and_create_candidate(self):
        plan = self.prepare()

        self.assertEqual(plan.project, "chama")
        self.assertEqual(plan.resources[0].iri, "chama:IMG_1520")
        self.assertEqual(plan.resources[0].reference_count, 2)
        values = FakeCataloguedPhotograph.last_kwargs
        self.assertEqual(values["schema:name"]["de"], "Stationsgebäude in Chama")
        self.assertEqual(str(values["dcterms:creator"]), "chama:LukasRosenthaler")
        self.assertEqual(values["chama:creationDating"], "2018-07-08")
        self.assertEqual(values["attachedToRole"], {"oldap:Unknown": "DATA_VIEW"})

    def test_controlled_object_property_value_needs_no_project_resource_read(self):
        source = VALID_DATA.replace(
            "        chama:publicDisplayPermission:\n",
            "        shared:archiveLevel:\n"
            "          - iri: shared:ArchiveGroup\n"
            "        chama:publicDisplayPermission:\n",
        )

        plan = self.prepare(source)

        self.assertEqual(plan.resources[0].reference_count, 2)
        self.assertEqual(
            str(FakeCataloguedPhotograph.last_kwargs["shared:archiveLevel"]),
            "shared:ArchiveGroup",
        )

    def test_rejects_unknown_properties_and_literal_link_values(self):
        with self.assertRaisesRegex(DataImportPreflightError, "not defined"):
            self.prepare(VALID_DATA.replace("schema:name:", "schema:headline:"))
        with self.assertRaisesRegex(DataImportPreflightError, "must be an IRI reference"):
            self.prepare(
                VALID_DATA.replace(
                    "- iri: chama:LukasRosenthaler",
                    "- value: Lukas Rosenthaler",
                )
            )

    def test_rejects_missing_or_wrongly_typed_link_targets(self):
        missing = FakeFactory(visible={"chama:ChamaStation": FakePlace()})
        with self.assertRaisesRegex(DataImportPreflightError, "does not exist or is not visible"):
            self.prepare(factory=missing)

        wrong_type = FakeFactory(
            visible={
                "chama:LukasRosenthaler": FakePlace(),
                "chama:ChamaStation": FakePlace(),
            }
        )
        with self.assertRaisesRegex(DataImportPreflightError, "requires an instance"):
            self.prepare(factory=wrong_type)

    def test_rejects_existing_target_and_unknown_role(self):
        existing = FakeFactory()
        existing.visible["chama:IMG_1520"] = FakeCataloguedPhotograph(
            iri=Iri("chama:IMG_1520"),
            **{"schema:name": {"de": "Existing"}},
        )
        with self.assertRaisesRegex(DataImportPreflightError, "already exists"):
            self.prepare(factory=existing)

        def missing_role(_role):
            raise OldapErrorNotFound("missing role")

        with self.assertRaisesRegex(DataImportPreflightError, "unknown role"):
            self.prepare(role_reader=missing_role)

    def test_batch_preflight_accepts_only_matching_existing_resources(self):
        existing = FakeCataloguedPhotograph(
            iri=Iri("chama:IMG_1520"),
            **{
                "schema:name": LangString({"de": "Stationsgebäude in Chama"}),
                "dcterms:creator": Iri("chama:LukasRosenthaler"),
                "chama:capturePlace": Iri("chama:ChamaStation"),
                "chama:creationDating": "2018-07-08",
                "chama:publicDisplayPermission": True,
                "attachedToRole": {"oldap:Unknown": "DATA_VIEW"},
            },
        )
        factory = FakeFactory()
        factory.visible["chama:IMG_1520"] = existing

        plan = prepare_data_import(
            FakeConnection(),
            factory,
            loads_data_document(VALID_DATA),
            role_reader=lambda _role: object(),
            allow_existing=True,
        )
        self.assertEqual(plan.resources[0].disposition, "existing_verified")

        existing.values["chama:publicDisplayPermission"] = False
        with self.assertRaisesRegex(DataImportPreflightError, "does not match the YAML"):
            prepare_data_import(
                FakeConnection(),
                factory,
                loads_data_document(VALID_DATA),
                role_reader=lambda _role: object(),
                allow_existing=True,
            )

    def test_wraps_dynamic_ontology_constraint_failures(self):
        without_title = VALID_DATA.replace(
            "        schema:name:\n"
            "          - value: Stationsgebäude in Chama\n"
            "            language: de\n",
            "",
        )

        with self.assertRaisesRegex(DataImportPreflightError, "MIN_COUNT=1"):
            self.prepare(without_title)

    def test_apply_creates_exactly_one_resource_after_rechecking(self):
        result = apply_data_import(
            FakeConnection(),
            FakeFactory(),
            loads_data_document(VALID_DATA),
            role_reader=lambda _role: object(),
        )

        self.assertEqual(result.created_iris, ("chama:IMG_1520",))
        self.assertEqual(FakeCataloguedPhotograph.created_iris, ["chama:IMG_1520"])

    def test_apply_refuses_multi_resource_documents_before_writing(self):
        resource_block = VALID_DATA.split("    - iri: IMG_1520", maxsplit=1)[1]
        multi_resource = VALID_DATA + "    - iri: IMG_1521" + resource_block

        with self.assertRaisesRegex(DataImportPreflightError, "exactly one resource"):
            apply_data_import(
                FakeConnection(),
                FakeFactory(),
                loads_data_document(multi_resource),
                role_reader=lambda _role: object(),
            )

        self.assertEqual(FakeCataloguedPhotograph.created_iris, [])

    def test_live_preflight_refuses_unprepared_auto_identity(self):
        source = VALID_DATA.replace("iri: IMG_1520", "iri: auto")

        with self.assertRaisesRegex(DataValidationError, "data prepare"):
            prepare_data_import(
                FakeConnection(),
                FakeFactory(),
                loads_data_document(source),
                role_reader=lambda _role: object(),
            )


if __name__ == "__main__":
    unittest.main()
