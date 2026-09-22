"""Contract and failure tests for ontology imports over existing HTTP routes."""

import copy
import gzip
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch
from zipfile import ZipFile

import requests
import yaml
from typer.testing import CliRunner

from oldap_tools.api_client import ApiError, ApiOperation, OldapApiClient, api_path
from oldap_tools.cli import app
from oldap_tools.list_api import plan_list
from oldap_tools.ontology_api import (
    OntologyApiPlan, _changes, _property_payload, apply_ontology_plan,
    load_ontology_api, plan_ontology_api, prepare_api_ontology, write_api_backup,
)
from oldap_tools.ontology_api_dump import api_model_to_yaml, dump_ontology_api, _publish_dump


PROJECT = {"projectShortName": "demo", "projectIri": "https://example.org/demo",
           "namespaceIri": "https://example.org/demo/"}
MODEL = {"project": "demo", "externalOntologies": [], "annotationProperties": [], "resources": [
    {"iri": "demo:Book", "superclass": ["oldap:Thing"], "label": ["Book@en"], "properties": [
        {"iri": "demo:title", "projectid": "demo", "datatype": "xsd:string", "maxCount": 1},
        {"iri": "demo:unused", "projectid": "demo", "datatype": "xsd:string"},
    ]}
]}


class ReadClient:
    """Read-only API fixture matching the observed project/model/list contracts."""

    def __init__(self, model=None, project=PROJECT, lists=None):
        self.model = copy.deepcopy(MODEL if model is None else model)
        self.project = copy.deepcopy(project)
        self.lists = lists or {}
        self.apply = Mock()

    def get_json(self, path, **kwargs):
        if path == "/admin/lucene/demo":
            return {"name": "demo", "configuration": None, "revision": None}
        if path == "/admin/project/demo":
            return self.project
        if path == "/admin/datamodel/demo":
            return self.model
        if path == "/admin/hlist/search":
            return [f"demo:{key}" for key in self.lists]
        raise AssertionError(f"Unexpected API read {path}")

    def get_bytes(self, path):
        for key, raw in self.lists.items():
            if path == f"/admin/hlist/demo/{key}/download":
                return raw
        if path == "/admin/datamodel/demo/download":
            return b'@prefix demo: <https://example.org/demo/> . demo:onto { demo:Book a <http://www.w3.org/2002/07/owl#Class> . }'
        raise AssertionError(f"Unexpected API download {path}")


def document(properties=None):
    return {"project": {"shortname": "demo"}, "classes": {"demo:Book": {
        "label": {"en": "Book"}, "properties": properties if properties is not None else [
            {"iri": "demo:title", "datatype": "xsd:string", "max_count": 1}
        ]}}}


class OntologyApiPlanningTests(unittest.TestCase):
    """Verify incremental semantics against actual API field/route shapes."""

    def test_default_preserves_omitted_properties_and_is_noop(self):
        client = ReadClient()
        plan = plan_ontology_api(client, document(), {})
        self.assertEqual(plan.operations, [])
        client.apply.assert_not_called()

    def test_remove_unused_is_opt_in_and_runs_last(self):
        source = document([{"iri": "demo:title", "max_count": None}])
        plan = plan_ontology_api(ReadClient(), source, {}, remove_unused=True)
        self.assertEqual([(op.method, op.payload) for op in plan.operations], [("POST", {"maxCount": None}), ("DELETE", None)])
        self.assertTrue(plan.operations[-1].remove_unused)
        self.assertEqual(plan.operations[-1].path, "/admin/datamodel/demo/demo%3ABook/demo%3Aunused")

    def test_omitted_property_set_never_requests_removal(self):
        source = document()
        del source["classes"]["demo:Book"]["properties"]
        self.assertEqual(plan_ontology_api(ReadClient(), source, {}, remove_unused=True).operations, [])

    def test_foreign_and_standalone_definitions_are_not_garbage_collected(self):
        model = copy.deepcopy(MODEL)
        model["resources"][0]["properties"][1]["projectid"] = "shared"
        model["annotationProperties"] = [{"iri": "demo:title"}]
        self.assertEqual(plan_ontology_api(ReadClient(model), document([]), {}, remove_unused=True).operations, [])

    def test_empty_property_set_removes_only_with_option(self):
        plan = plan_ontology_api(ReadClient(), document([]), {}, remove_unused=True)
        self.assertEqual(len(plan.operations), 2)
        self.assertTrue(all(op.method == "DELETE" for op in plan.operations))

    def test_property_translation_preserves_null_and_resolves_list_class(self):
        payload = _property_payload({"iri": "demo:topic", "to_class": "list:Topics", "max_count": None,
                                     "name": {"de": "Thema"}, "in": ["L-Topics:A"]}, "demo", {"Topics"})
        self.assertEqual(payload, {"class": "demo:TopicsNode", "maxCount": None,
                                   "name": ["Thema@de"], "inSet": ["L-Topics:A"]})
        self.assertEqual(_changes({"class": "demo:Person"}, {"toClass": "demo:Agent"}), {"class": "demo:Person"})

    def test_implicit_thing_base_does_not_cause_repeated_updates(self):
        self.assertEqual(_changes({"superclass": ["demo:Base"]}, {"superclass": ["oldap:Thing", "demo:Base"]}), {})
        self.assertEqual(_changes({"superclass": []}, {"superclass": ["oldap:Thing", "demo:Base"]}),
                         {"superclass": ["oldap:Thing"]})

    def test_language_and_numeric_sets_ignore_order(self):
        self.assertEqual(_changes({"name": ["B@en", "A@de"], "inSet": [2, 1]},
                                  {"name": ["A@de", "B@en"], "inSet": ["1", "2"]}), {})

    def test_equivalent_editor_aliases_do_not_plan_writes(self):
        model = copy.deepcopy(MODEL)
        model["resources"][0]["properties"][0]["editor"] = "dash:TextFieldEditor"
        for alias in ("TEXT_FIELD", "TextFieldEditor", "dash:TextFieldEditor"):
            with self.subTest(alias=alias):
                source = document([{"iri": "demo:title", "editor": alias}])
                self.assertEqual(plan_ontology_api(ReadClient(model), source, {}).operations, [])
        self.assertEqual(_changes({"editor": "dash:TextFieldEditor"}, {"editor": "TEXT_FIELD"}), {})

    def test_changed_editor_uses_canonical_dash_identifier(self):
        model = copy.deepcopy(MODEL)
        model["resources"][0]["properties"][0]["editor"] = "dash:TextFieldEditor"
        source = document([{"iri": "demo:title", "editor": "TEXT_AREA_WITH_LANG"}])
        operations = plan_ontology_api(ReadClient(model), source, {}).operations
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0].payload, {"editor": "dash:TextAreaWithLangEditor"})

    def test_editor_removal_and_invalid_alias_remain_explicit(self):
        self.assertEqual(_changes({"editor": None}, {"editor": "dash:TextFieldEditor"}), {"editor": None})
        self.assertEqual(_changes({"editor": None}, {}), {})
        with self.assertRaises(ValueError):
            _property_payload({"editor": "UNKNOWN_EDITOR"}, "demo", set())

    def test_yaml_date_constraints_are_json_lexical_values(self):
        self.assertEqual(_property_payload({"datatype": "xsd:date", "in": [date(2026, 9, 22)]}, "demo", set()),
                         {"datatype": "xsd:date", "inSet": ["2026-09-22"]})

    def test_nonfinite_payload_fails_during_planning(self):
        with self.assertRaisesRegex(ValueError, "cannot be represented as JSON"):
            plan_ontology_api(ReadClient(), document([{"iri": "demo:title", "order": float("nan")}]), {})

    def test_parent_classes_precede_children_and_all_classes_precede_properties(self):
        source = {"project": {"shortname": "demo"}, "classes": {
            "demo:Child": {"superclass": ["demo:Parent"], "properties": [{"iri": "demo:link", "to_class": "demo:Parent"}]},
            "demo:Parent": {"properties": [{"iri": "demo:back", "to_class": "demo:Child"}]},
        }}
        operations = plan_ontology_api(ReadClient(), source, {}).operations
        self.assertEqual([op.path for op in operations[:2]], ["/admin/datamodel/demo/demo%3AParent", "/admin/datamodel/demo/demo%3AChild"])
        self.assertEqual(operations[1].payload, {"superclass": ["demo:Parent"]})
        self.assertEqual(len(operations), 4)

    def test_cycle_and_missing_new_property_type_fail_before_writes(self):
        source = {"project": {"shortname": "demo"}, "classes": {"demo:A": {"superclass": ["demo:B"]}, "demo:B": {"superclass": ["demo:A"]}}}
        with self.assertRaisesRegex(ValueError, "cycle"):
            plan_ontology_api(ReadClient(), source, {})
        with self.assertRaisesRegex(ValueError, "requires exactly one"):
            plan_ontology_api(ReadClient(), document([{"iri": "demo:new", "max_count": 1}]), {})

    def test_project_identity_mismatch_and_malformed_model_fail_closed(self):
        source = document()
        source["project"]["namespace"] = "https://wrong.example/"
        with self.assertRaisesRegex(ValueError, "different project"):
            plan_ontology_api(ReadClient(), source, {})
        with self.assertRaisesRegex(ValueError, "datamodel response"):
            plan_ontology_api(ReadClient(model={"message": "not a datamodel"}), document(), {})

    def test_external_metadata_uses_existing_api_endpoints(self):
        source = document()
        source["external_ontologies"] = {"schema": {"namespace": "https://schema.org/", "label": {"en": "Schema"}, "resource_classes": ["Person"]}}
        ops = plan_ontology_api(ReadClient(), source, {}).operations
        self.assertEqual(ops, [ApiOperation("PUT", "/admin/datamodel/demo/extonto/schema", {
            "namespaceIri": "https://schema.org/", "label": ["Schema@en"], "proposedResourceClass": ["Person"]})])

    def test_new_project_uses_existing_create_and_date_update_routes(self):
        source = {"project": {"shortname": "demo", "iri": PROJECT["projectIri"], "namespace": PROJECT["namespaceIri"], "start": "2026-01-01"}}
        ops = plan_ontology_api(ReadClient(project=None), source, {}).operations
        self.assertEqual([(op.method, op.path) for op in ops], [("PUT", "/admin/project/demo"), ("POST", "/admin/project/demo"), ("PUT", "/admin/datamodel/demo")])
        self.assertEqual(ops[1].payload, {"projectStart": "2026-01-01"})

    def test_real_fasnacht_document_validates_without_network(self):
        source = Path(__file__).resolve().parents[1] / "fasnacht/fasnacht-onto.yaml"
        with patch("requests.Session.request", side_effect=AssertionError("Unexpected network")):
            ontology, lists = prepare_api_ontology(source)
        self.assertEqual(ontology["project"]["shortname"], "fasnacht")
        self.assertIn("CreativeCommons", lists)

    def test_unsupported_node_kind_fails_before_authentication(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "onto.yaml"
            path.write_text("ontology:\n  project: {shortname: demo}\n  standalone_properties:\n    demo:p: {datatype: 'xsd:string', node_kind: 'sh:Literal'}\n")
            with patch("oldap_tools.ontology_api.OldapApiClient") as client:
                with self.assertRaisesRegex(ValueError, "node_kind"):
                    load_ontology_api(api_base="http://example.test", user="admin", password="secret", inf=path)
                client.assert_not_called()


class ListApiPlanningTests(unittest.TestCase):
    """Exercise hierarchy preservation, insertion anchors and full preflight."""

    def test_adds_nodes_before_between_after_and_below_existing_nodes(self):
        old = {"label": ["Topics@en"], "nodes": {"B": {"label": ["B@en"]}, "D": {"label": ["D@en"]}}}
        desired = {"label": ["Ignored new label@en"], "nodes": {key: {"label": [f"{key}@en"]} for key in "ABCDE"}}
        desired["nodes"]["C"]["nodes"] = {"Child": {"label": ["Child@en"]}}
        ops = plan_list("demo", "Topics", desired, old)
        self.assertEqual([(op.payload["position"], op.payload.get("refnode")) for op in ops],
                         [("leftOf", "B"), ("rightOf", "B"), ("belowOf", "C"), ("rightOf", "D")])

    def test_new_list_root_and_multiple_siblings(self):
        desired = {"label": ["Topics@en"], "nodes": {"A": {"label": ["A@en"]}, "B": {"label": ["B@en"]}}}
        ops = plan_list("demo", "Topics", desired, None)
        self.assertEqual([op.payload for op in ops], [{"prefLabel": ["Topics@en"]},
                         {"prefLabel": ["A@en"], "position": "root"},
                         {"prefLabel": ["B@en"], "position": "rightOf", "refnode": "A"}])

    def test_parent_conflict_and_duplicate_nodes_rejected(self):
        old = {"nodes": {"A": {"nodes": {"B": {}}}}}
        with self.assertRaisesRegex(ValueError, "cannot be moved"):
            plan_list("demo", "Topics", {"nodes": {"B": {}}}, old)
        with self.assertRaisesRegex(ValueError, "more than once"):
            plan_list("demo", "Topics", {"nodes": {"B": {}, "A": {"nodes": {"B": {}}}}}, old)


class ApiApplyAndBackupTests(unittest.TestCase):
    """Do not hide partial writes, rejected deletion or incomplete backups."""

    def test_invalid_server_trig_aborts_before_backup_or_mutations(self):
        client = Mock()
        client.get_bytes.return_value = b'@prefix demo: <https://example.org/> .\ndemo:shacl { INSERT DATA { GRAPH demo:shacl { demo:a demo:b demo:c . } } }'
        plan = OntologyApiPlan("demo", [ApiOperation("PUT", "/never")], PROJECT, MODEL)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "backup.zip"
            with self.assertRaisesRegex(ValueError, "invalid TriG at line 2.*no import operations"):
                write_api_backup(client, plan, path)
            self.assertFalse(path.exists())
        client.apply.assert_not_called()

    def test_exact_in_use_refusal_keeps_property_and_continues(self):
        ops = [ApiOperation("DELETE", "/first", remove_unused=True), ApiOperation("DELETE", "/second", remove_unused=True)]
        client = Mock()
        client.apply.side_effect = [ApiError("refused", status=500, detail='Cannot update: resource "demo:Book" is in use'), None]
        emit = Mock()
        self.assertEqual(apply_ontology_plan(client, OntologyApiPlan("demo", ops, PROJECT, MODEL), emit), (1, 1))
        self.assertIn("KEEP", emit.call_args_list[0].args[0])

    def test_unknown_server_error_stops_after_recorded_partial_progress(self):
        ops = [ApiOperation("PUT", "/first"), ApiOperation("DELETE", "/second", remove_unused=True), ApiOperation("PUT", "/third")]
        client = Mock()
        client.apply.side_effect = [None, ApiError("database unavailable", status=500)]
        with self.assertRaisesRegex(ApiError, "after 1 successful.*Earlier successful operations remain committed"):
            apply_ontology_plan(client, OntologyApiPlan("demo", ops, PROJECT, MODEL), Mock())
        self.assertEqual(client.apply.call_count, 2)

    def test_backup_contains_all_lists_and_never_overwrites(self):
        raw = b"Unmentioned:\n  label: [Other@en]\n"
        client = ReadClient(lists={"Unmentioned": raw})
        plan = plan_ontology_api(client, document(), {})
        with TemporaryDirectory() as folder:
            out = Path(folder) / "backup.zip"
            write_api_backup(client, plan, out)
            original = out.read_bytes()
            with ZipFile(out) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(archive.read("lists/Unmentioned.yaml"), raw)
                self.assertIn("model.trig", archive.namelist())
                self.assertFalse(json.loads(archive.read("manifest.json"))["rawGraphBackup"])
            with self.assertRaises(FileExistsError):
                write_api_backup(client, plan, out)
            self.assertEqual(out.read_bytes(), original)

    def test_backup_failure_prevents_all_mutations(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "onto.yaml"
            path.write_text("ontology:\n  project: {shortname: demo}\n  classes:\n    demo:New: {label: New}\n")
            client = ReadClient()
            client.login = Mock()
            with patch("oldap_tools.ontology_api.OldapApiClient") as factory, patch("oldap_tools.ontology_api.write_api_backup", side_effect=OSError("disk full")):
                factory.return_value.__enter__.return_value = client
                with self.assertRaisesRegex(OSError, "disk full"):
                    load_ontology_api(api_base="http://example.test", user="admin", password="secret", inf=path, emit=Mock())
            client.apply.assert_not_called()

    def test_dry_run_makes_no_model_writes_or_backup(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "onto.yaml"
            path.write_text("ontology:\n  project: {shortname: demo}\n  classes:\n    demo:New: {label: New}\n")
            client = ReadClient()
            client.login = Mock()
            with patch("oldap_tools.ontology_api.OldapApiClient") as factory, patch("oldap_tools.ontology_api.write_api_backup") as backup:
                factory.return_value.__enter__.return_value = client
                plan = load_ontology_api(api_base="http://example.test", user="admin", password="secret", inf=path, dry_run=True, emit=Mock())
            self.assertTrue(plan.operations)
            client.apply.assert_not_called()
            backup.assert_not_called()


def response(status=200, payload=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(payload if payload is not None else {}).encode()
    return result


class ApiTransportTests(unittest.TestCase):
    """Exercise bearer/session lifecycle and never replay ambiguous writes."""

    @patch("oldap_tools.api_client.requests.Session")
    def test_login_encoding_bearer_and_proactive_refresh(self, factory):
        session = factory.return_value
        session.request.side_effect = [response(payload={"accessToken": "old", "expiresIn": 0}),
                                       response(payload={"accessToken": "fresh", "expiresIn": 900}),
                                       response(payload=MODEL)]
        with OldapApiClient("https://api.example/root/") as client:
            client.login("user/name", "secret")
            self.assertEqual(client.get_json("/admin/datamodel/demo"), MODEL)
        calls = session.request.call_args_list
        self.assertEqual(calls[0].args[1], "https://api.example/root/admin/auth/user%2Fname")
        self.assertNotIn("Authorization", calls[0].kwargs["headers"])
        self.assertEqual(calls[1].args[1], "https://api.example/root/admin/auth/refresh")
        self.assertEqual(calls[2].kwargs["headers"]["Authorization"], "Bearer fresh")
        self.assertTrue(all(call.kwargs["allow_redirects"] is False for call in calls))
        session.close.assert_called_once()

    @patch("oldap_tools.api_client.requests.Session")
    def test_mutation_timeout_is_not_retried(self, factory):
        factory.return_value.request.side_effect = [response(payload={"token": "token"}), requests.Timeout("secret")]
        with OldapApiClient("http://api.example") as client:
            client.login("user", "password")
            with self.assertRaisesRegex(ApiError, "no retry") as error:
                client.apply(ApiOperation("PUT", "/admin/datamodel/demo"))
            self.assertNotIn("secret", str(error.exception))
        self.assertEqual(factory.return_value.request.call_count, 2)

    @patch("oldap_tools.api_client.requests.Session")
    def test_only_404_is_missing_and_redirect_is_rejected(self, factory):
        factory.return_value.request.side_effect = [response(payload={"token": "token"}), response(404), response(403), response(302)]
        with OldapApiClient("http://api.example") as client:
            client.login("user", "password")
            self.assertIsNone(client.get_json("/missing", missing_ok=True))
            for status in (403, 302):
                with self.assertRaises(ApiError) as error:
                    client.get_json("/denied", missing_ok=True)
                self.assertEqual(error.exception.status, status)

    @patch("oldap_tools.api_client.requests.Session")
    def test_login_error_does_not_echo_server_secrets(self, factory):
        factory.return_value.request.return_value = response(401, {"message": "secret password"})
        with OldapApiClient("http://api.example") as client:
            with self.assertRaises(ApiError) as error:
                client.login("user", "secret password")
            self.assertNotIn("secret password", str(error.exception))


class OntologyCliTests(unittest.TestCase):
    """Ensure API mode never falls back to direct connections."""

    @patch("oldap_tools.cli.dump_ontology")
    @patch("oldap_tools.cli.dump_ontology_api")
    def test_dump_uses_api_and_directory_with_hidden_password(self, api, direct):
        result = CliRunner().invoke(app, ["--user", "u", "ontology", "dump", "demo", "--out-dir", "export/demo",
                                          "--include-taxonomies"], input="hidden-password\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertNotIn("hidden-password", result.output)
        self.assertEqual(api.call_args.kwargs["out_dir"], Path("export/demo"))
        self.assertTrue(api.call_args.kwargs["include_taxonomies"])
        direct.assert_not_called()

    @patch("oldap_tools.cli.typer.prompt")
    def test_dump_rejects_ambiguous_paths_before_password_prompt(self, prompt):
        for options in (["--include-taxonomies"], ["--out", "x.yaml", "--out-dir", "folder"], ["--format", "trig"]):
            result = CliRunner().invoke(app, ["--user", "u", "ontology", "dump", "demo", *options])
            self.assertNotEqual(result.exit_code, 0)
        prompt.assert_not_called()

    @patch("oldap_tools.cli.load_ontology_api")
    def test_missing_password_is_prompted_without_echo(self, api):
        result = CliRunner().invoke(app, ["--user", "u", "ontology", "load", "--inf", "model.yaml", "--dry-run"],
                                    input="hidden-test-password\n")
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("OLDAP password", result.output)
        self.assertNotIn("hidden-test-password", result.output)
        self.assertEqual(api.call_args.kwargs["password"], "hidden-test-password")

    @patch("oldap_tools.cli.load_ontology_api")
    def test_password_prompt_eof_aborts_before_connection(self, api):
        result = CliRunner().invoke(app, ["--user", "u", "ontology", "load", "--inf", "model.yaml"], input="")
        self.assertNotEqual(result.exit_code, 0)
        api.assert_not_called()

    @patch("oldap_tools.cli.typer.prompt")
    @patch("oldap_tools.cli.validate_ontology_yaml")
    def test_offline_validation_and_help_never_prompt(self, validate, prompt):
        runner = CliRunner()
        for args in (["ontology", "validate", "--inf", "model.yaml"], ["ontology", "load", "--help"]):
            result = runner.invoke(app, args)
            self.assertEqual(result.exit_code, 0, result.output)
        prompt.assert_not_called()

    @patch("oldap_tools.cli.load_ontology")
    @patch("oldap_tools.cli.load_ontology_api")
    def test_api_is_default_and_options_are_forwarded(self, api, direct):
        result = CliRunner().invoke(app, ["--api", "https://api.example", "--user", "u", "--password", "p",
                                           "ontology", "load", "--inf", "model.yaml", "--remove-unused", "--dry-run"])
        self.assertEqual(result.exit_code, 0, result.output)
        direct.assert_not_called()
        self.assertNotIn("OLDAP password:", result.output)
        self.assertEqual(api.call_args.kwargs["api_base"], "https://api.example")
        self.assertTrue(api.call_args.kwargs["remove_unused"])
        self.assertTrue(api.call_args.kwargs["dry_run"])

    @patch("oldap_tools.cli.load_ontology_api")
    def test_unsupported_modes_rejected_before_connection(self, api):
        for options in (["--mode", "replace"], ["--connectors", "create"], ["--transport", "invalid"]):
            result = CliRunner().invoke(app, ["ontology", "load", "--inf", "model.yaml", *options])
            self.assertNotEqual(result.exit_code, 0)
        api.assert_not_called()

    @patch("oldap_tools.cli.load_ontology")
    def test_direct_transport_remains_explicit(self, direct):
        result = CliRunner().invoke(app, ["--user", "u", "--password", "p", "ontology", "load", "--inf", "model.yaml", "--transport", "direct"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertFalse(direct.call_args.kwargs["remove_unused"])


class ApiDumpTests(unittest.TestCase):
    """Verify portable, non-destructive YAML exports and their import roundtrip."""

    def test_single_gzip_export_does_not_download_taxonomies(self):
        client = ReadClient()
        client.login = Mock()
        original = client.get_json
        client.get_json = Mock(side_effect=original)
        with TemporaryDirectory() as folder, patch("oldap_tools.ontology_api_dump.OldapApiClient") as factory:
            factory.return_value.__enter__.return_value = client
            out = Path(folder) / "single.yaml.gz"
            dump_ontology_api(api_base="https://api.example", user="u", password="secret", project_id="demo", out=out, emit=Mock())
            exported = yaml.safe_load(gzip.decompress(out.read_bytes()))
            self.assertNotIn("lists", exported["ontology"])
            self.assertEqual(client.get_json.call_count, 3)

    def test_complete_export_roundtrip_has_no_planned_changes(self):
        model = copy.deepcopy(MODEL)
        model["resources"][0]["properties"].append({"iri": "demo:topic", "projectid": "demo", "toClass": "demo:TopicsNode",
                                                 "name": ["Topic@en"], "minCount": 0, "order": 0})
        model["annotationProperties"] = [{"iri": "demo:note", "datatype": "rdf:langString", "uniqueLang": False,
                                          "name": ["Note@en"], "languageIn": ["en", "de"], "editor": "dash:TextFieldWithLangEditor"}]
        model["externalOntologies"] = [{"prefix": "schema", "namespaceIri": "https://schema.org/", "label": ["Schema@en"],
                                        "proposedResourceClass": ["Book"]}]
        project = dict(PROJECT, projectStart="2026-01-01", label=["Demo@en"])
        raw = b"Topics:\n  label: [Topics@en]\n  nodes:\n    A:\n      label: [First@en]\n"
        client = ReadClient(model, project, {"Topics": raw})
        client.login = Mock()
        with TemporaryDirectory() as folder, patch("oldap_tools.ontology_api_dump.OldapApiClient") as factory:
            factory.return_value.__enter__.return_value = client
            out_dir = Path(folder) / "new" / "package"
            out = dump_ontology_api(api_base="https://api.example", user="u", password="secret", project_id="demo",
                                    out_dir=out_dir, include_taxonomies=True, emit=Mock())
            source, lists = prepare_api_ontology(out)
            self.assertEqual(source["project"]["start"], "2026-01-01")
            self.assertEqual(source["lists"], {"Topics": "taxonomies/Topics.yaml"})
            self.assertEqual((out_dir / "taxonomies/Topics.yaml").read_bytes(), raw)
            self.assertEqual(source["classes"]["demo:Book"]["properties"][1]["to_class"], "list:Topics")
            self.assertFalse(source["standalone_properties"]["demo:note"]["unique_lang"])
            self.assertEqual(plan_ontology_api(client, source, lists).operations, [])
        client.apply.assert_not_called()

    def test_conflict_does_not_write_any_file(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "ontology.yaml").write_text("original")
            with self.assertRaisesRegex(ValueError, "--overwrite"):
                _publish_dump(path, {"taxonomies/A.yaml": b"new", "ontology.yaml": b"changed"}, overwrite=False)
            self.assertEqual((path / "ontology.yaml").read_text(), "original")
            self.assertFalse((path / "taxonomies").exists())

    def test_overwrite_preserves_unrelated_files(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "ontology.yaml").write_text("old")
            (path / "notes.txt").write_text("keep")
            _publish_dump(path, {"ontology.yaml": b"new"}, overwrite=True)
            self.assertEqual((path / "ontology.yaml").read_text(), "new")
            self.assertEqual((path / "notes.txt").read_text(), "keep")

    def test_taxonomy_symlink_is_rejected_even_with_overwrite(self):
        with TemporaryDirectory() as folder:
            path = Path(folder)
            outside = path / "outside"
            outside.mkdir()
            output = path / "dump"
            output.mkdir()
            (output / "taxonomies").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                _publish_dump(output, {"taxonomies/A.yaml": b"bad"}, overwrite=True)
            self.assertEqual(list(outside.iterdir()), [])

    def test_failed_download_does_not_create_target(self):
        client = ReadClient(lists={"Topics": b"Topics: invalid"})
        client.login = Mock()
        with TemporaryDirectory() as folder, patch("oldap_tools.ontology_api_dump.OldapApiClient") as factory:
            factory.return_value.__enter__.return_value = client
            output = Path(folder) / "dump"
            with self.assertRaises(ValueError):
                dump_ontology_api(api_base="https://api.example", user="u", password="secret", project_id="demo",
                                   out_dir=output, include_taxonomies=True, emit=Mock())
            self.assertFalse(output.exists())

    def test_unrepresentable_properties_are_not_silently_dropped(self):
        model = copy.deepcopy(MODEL)
        model["resources"][0]["properties"][0]["type"] = ["SymmetricProperty"]
        with self.assertRaisesRegex(ValueError, "not supported"):
            api_model_to_yaml(PROJECT, model, {})


if __name__ == "__main__":
    unittest.main()


class LuceneApiTests(unittest.TestCase):
    """Roundtrip, compatibility and preflight checks for connector instructions."""

    configuration = {"types": ["https://example.org/demo/Book"], "fields": [
        {"fieldName": "title", "propertyChain": ["https://example.org/demo/title"],
         "valueFilter": '?value != "ignored"', "analyzer": "custom"}],
        "languages": ["de"], "customOption": {"enabled": True}}

    def client_with_connector(self):
        import hashlib
        client = ReadClient()
        raw = json.dumps(self.configuration, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        state = {"name": "demo", "configuration": copy.deepcopy(self.configuration),
                 "revision": hashlib.sha256(raw.encode()).hexdigest()}
        original = client.get_json
        client.get_json = Mock(side_effect=lambda path, **kw: state if path == "/admin/lucene/demo" else original(path, **kw))
        client.login = Mock()
        return client, state

    def test_lossless_dump_load_roundtrip_and_skip(self):
        client, state = self.client_with_connector()
        with TemporaryDirectory() as folder, patch("oldap_tools.ontology_api_dump.OldapApiClient") as factory:
            factory.return_value.__enter__.return_value = client
            path = dump_ontology_api(api_base="https://api.example", user="u", password="secret",
                                     project_id="demo", out_dir=Path(folder), emit=Mock())
            ontology, lists = prepare_api_ontology(path)
            self.assertEqual(ontology["lucene_connectors"]["demo"]["configuration"], self.configuration)
            plan = plan_ontology_api(client, ontology, lists, connector_mode="replace")
            self.assertEqual(plan.operations, [])
            self.assertEqual(plan.connector_before, state)
            client.get_json.reset_mock()
            plan_ontology_api(client, ontology, lists)
            self.assertNotIn("/admin/lucene/demo", [call.args[0] for call in client.get_json.call_args_list])
        client.apply.assert_not_called()

    def test_create_conflict_is_preflight_and_replace_is_last_and_backed_up(self):
        client, state = self.client_with_connector()
        ontology = {"project": {"shortname": "demo"}, "classes": {"demo:Book": {"label": "Changed@en"}},
                    "lucene_connectors": {"demo": {"configuration": dict(self.configuration, languages=["fr"])}}}
        with self.assertRaisesRegex(ValueError, "already exists"):
            plan_ontology_api(client, ontology, {}, connector_mode="create")
        client.apply.assert_not_called()
        plan = plan_ontology_api(client, ontology, {}, connector_mode="replace")
        self.assertEqual(plan.operations[-1].path, "/admin/lucene/demo")
        self.assertEqual(plan.operations[-1].payload["expectedRevision"], state["revision"])
        with TemporaryDirectory() as folder:
            out = Path(folder) / "backup.zip"
            write_api_backup(client, plan, out)
            with ZipFile(out) as archive:
                self.assertEqual(json.loads(archive.read("lucene.json")), state)

    def test_older_api_explicit_opt_out(self):
        client = ReadClient()
        client.login = Mock()
        original = client.get_json
        client.get_json = Mock(side_effect=lambda path, **kw: (_ for _ in ()).throw(ApiError("Not found", status=404)) if path == "/admin/lucene/demo" else original(path, **kw))
        with TemporaryDirectory() as folder, patch("oldap_tools.ontology_api_dump.OldapApiClient") as factory:
            factory.return_value.__enter__.return_value = client
            target = Path(folder) / "package"
            with self.assertRaises(ApiError):
                dump_ontology_api(api_base="https://api.example", user="u", password="secret", project_id="demo", out_dir=target, emit=Mock())
            self.assertFalse(target.exists())
            dump_ontology_api(api_base="https://api.example", user="u", password="secret", project_id="demo", out_dir=target, include_connectors=False, emit=Mock())
            self.assertTrue((target / "ontology.yaml").exists())

    def test_shorthand_still_expands_qnames_and_native_mixing_fails(self):
        from oldap_tools.lucene_api import plan_connector
        client = ReadClient()
        ontology = {"project": {"shortname": "demo"}, "lucene_connectors": {"group": {
            "types": ["demo:Book"], "fields": {"title": "demo:title"}}}}
        operation, _ = plan_connector(client, ontology, PROJECT, "create")
        self.assertEqual(operation.payload["configuration"]["types"], ["https://example.org/demo/Book"])
        ontology["lucene_connectors"]["native"] = {"configuration": self.configuration}
        with self.assertRaisesRegex(ValueError, "only connector"):
            plan_connector(client, ontology, PROJECT, "replace")

    def test_invalid_native_fields_fail_during_planning(self):
        from oldap_tools.lucene_api import plan_connector
        client = ReadClient()
        ontology = {"project": {"shortname": "demo"}, "lucene_connectors": {"demo": {
            "configuration": {"types": ["https://example.org/Book"], "fields": [{"fieldName": "title"}]}}}}
        with self.assertRaisesRegex(ValueError, "propertyChain"):
            plan_connector(client, ontology, PROJECT, "replace")
        client.apply.assert_not_called()

    def test_direct_dump_also_preserves_native_options(self):
        from types import SimpleNamespace
        from oldap_tools.ontology import _dump_lucene_connector
        con = Mock()
        con.query.side_effect = [{"boolean": True}, {"results": {"bindings": [
            {"options": {"value": json.dumps(self.configuration)}}]}}]
        result = _dump_lucene_connector(con, SimpleNamespace(projectShortName="demo"))
        self.assertEqual(result, {"demo": {"configuration": self.configuration}})
        self.assertIn("instance#demo>", con.query.call_args_list[0].args[0])

    @patch("oldap_tools.cli.load_ontology_api")
    def test_cli_accepts_api_connector_mode(self, loader):
        result = CliRunner().invoke(app, ["--user", "u", "--password", "secret", "ontology", "load",
                                         "--inf", "ontology.yaml", "--connectors", "replace", "--dry-run"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(loader.call_args.kwargs["connector_mode"], "replace")
