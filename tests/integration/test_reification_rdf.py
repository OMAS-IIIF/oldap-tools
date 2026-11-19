"""Local sibling-source acceptance: tools -> library/Flask -> RDF -> YAML.

Run with oldaplib, oldap-api and oldap-tools/src on PYTHONPATH. No services,
network sockets or persistent Redis stores are used.
"""
from contextlib import ExitStack
from pathlib import Path
import hashlib
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import yaml
import json
from zipfile import ZipFile
import typer

pytest.importorskip('oldap_api')
pytest.importorskip('oldaplib.test.test_reifier_shape')
from flask import Flask
from oldaplib.test.test_reifier_shape import DatasetConnection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.dtypes.namespaceiri import NamespaceIRI
from oldaplib.src.project import Project
from oldaplib.src.resourceclass import ResourceClass
from oldaplib.src.xsd.xsd_date import Xsd_date
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldap_api.views.datamodelling_views import datamodel_bp
from oldap_tools.ontology import _build_datamodel, _apply_update, _model_reification_yaml, _read_yaml, _preflight_direct_ontology
from oldap_tools.ontology_api import plan_ontology_api, apply_ontology_plan, write_api_backup
from oldap_tools.ontology_api_dump import api_model_to_yaml
from oldap_tools.api_client import ApiError


@pytest.fixture(params=['rdflib', 'jena'])
def store(request, tmp_path):
    process = None
    if request.param == 'jena':
        jar = os.environ.get('OLDAP_TEST_FUSEKI_JAR')
        if not jar:
            pytest.skip('Set OLDAP_TEST_FUSEKI_JAR for isolated native acceptance.')
        from tools.reification.probe_model import NativeConnection, ROOT
        assert hashlib.sha256(Path(jar).read_bytes()).hexdigest() == '2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee'
        java = Path(os.environ.get('OLDAP_TEST_JAVA_HOME', '/opt/homebrew/opt/openjdk@25')) / 'bin'
        subprocess.run([str(java / 'javac'), '-cp', jar, '-d', str(tmp_path),
                        str(ROOT / 'tools/reification/JenaModelProbe.java')], check=True)
        process = subprocess.Popen([str(java / 'java'), '-cp', str(tmp_path) + ':' + jar,
                                    'JenaModelProbe', str(tmp_path / 'tdb')],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        con = NativeConnection(process)
        def close_process():
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        request.addfinalizer(close_process)
    else:
        con = DatasetConnection()
    projects = {name: Project(con=con, projectIri=f'https://example.org/projects/{name}',
                projectShortName=name, namespaceIri=NamespaceIRI(namespace), projectStart=Xsd_date('2026-01-01'))
                for name, namespace in [('travel', 'https://example.org/travel/'),
                                        ('oldap', 'http://oldap.org/base#'), ('shared', 'http://oldap.org/shared#')]}
    def project_read(connection, name, **kwargs):
        return name if isinstance(name, Project) else projects[str(name)]
    cache = MagicMock()
    cache.get.return_value = None
    with ExitStack() as stack:
        stack.enter_context(patch('rdflib.plugins.sparql.SPARQL_LOAD_GRAPHS', False))
        stack.enter_context(patch.object(Project, 'read', side_effect=project_read))
        stack.enter_context(patch.object(ResourceClass, '_sysproject', projects['oldap']))
        stack.enter_context(patch.object(ResourceClass, '_sharedproject', projects['shared']))
        for module in ['datamodel', 'resourceclass', 'propertyclass']:
            stack.enter_context(patch(f'oldaplib.src.{module}.CacheSingletonRedis', return_value=cache))
        stack.enter_context(patch('oldaplib.src.cachesingleton.CacheSingletonRedis', return_value=cache))
        stack.enter_context(patch('oldaplib.src.datamodel.OldapList.ensure_list_node_context'))
        stack.enter_context(patch('oldaplib.src.datamodel.ExternalOntology.search', return_value=[]))
        stack.enter_context(patch('oldaplib.src.resource_transaction.archive_coordination_enabled', return_value=False))
        stack.enter_context(patch('oldap_api.authentication.Connection', return_value=con))
        ResourceClass(con=con, project=projects['oldap'], owlclass_iri='oldap:Thing').create()
        # Real system ontology defines Thing as the root, without a self-parent.
        con.transaction_start()
        con.transaction_update('PREFIX oldap: <http://oldap.org/base#> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> DELETE DATA { GRAPH oldap:onto { oldap:Thing rdfs:subClassOf oldap:Thing } }')
        con.transaction_commit()
        app = Flask(__name__)
        app.register_blueprint(datamodel_bp)
        yield con, projects['travel'], app.test_client()


def document():
    return _read_yaml(Path(__file__).parents[2] / 'examples/ontology/travel-reification.yaml')


def test_direct_rdf_roundtrip_update_and_replay(store, tmp_path):
    con, project, _ = store
    doc = document()
    model = _build_datamodel(con, project, doc, {})
    model.create()
    loaded = DataModel.read(con, project, ignore_cache=True)
    from oldap_tools.ontology import dump_ontology
    out = tmp_path / 'export.yaml'
    with patch('oldap_tools.ontology._connect', return_value=con):
        dump_ontology(graphdb_base='http://unused.invalid', repo='unused', project_id='travel',
                      out=out, fmt='yaml', user='test', password='test', include_connectors=False)
    exported = _read_yaml(out)
    assert exported['reifier_shapes'] == doc['reifier_shapes']
    actual = exported['classes']['travel:Travel']['properties'][0]
    assert actual['reifier_shapes'] == ['travel:VisitAnnotationShape']
    def tokens():
        model = DataModel.read(con, project, ignore_cache=True)
        return {str(iri): str(model[iri].modified) for iri in model.get_reifier_shapes() + model.get_resclasses()}
    before = tokens()
    _apply_update(con, project, exported, {})
    assert tokens() == before
    patch_doc = {'project': doc['project'], 'reifier_shapes': {'travel:VisitAnnotationShape': {
        'properties': [{'iri': 'travel:dateTime', 'max_count': 2, 'min_count': 0}]}},
        'classes': {'travel:Travel': {'properties': [{'iri': 'travel:isAt', 'reification_required': False}]}}}
    _apply_update(con, project, patch_doc, {})
    updated = _model_reification_yaml(DataModel.read(con, project, ignore_cache=True))
    assert updated['reifier_shapes']['travel:VisitAnnotationShape']['properties'][0]['max_count'] == 2
    assert updated['reifier_shapes']['travel:VisitAnnotationShape']['properties'][0]['min_count'] == 0
    assert updated['classes']['travel:Travel']['properties'][0]['reification_required'] is False
    clear = {'project': doc['project'], 'reifier_shapes': {'travel:VisitAnnotationShape': None},
        'classes': {'travel:Travel': {'properties': [{'iri': 'travel:isAt', 'reifier_shapes': [], 'reification_required': None}]}}}
    _apply_update(con, project, clear, {}, remove_unused=True)
    assert not DataModel.read(con, project, ignore_cache=True).reifier_shapes


class FlaskTransport:
    """Route actual tool operations through authenticated Flask view functions."""
    def __init__(self, http):
        self.http = http
        self.operations = []
    def get_json(self, path, **kwargs):
        if path == '/admin/project/travel':
            return {'projectShortName': 'travel', 'projectIri': 'https://example.org/projects/travel',
                    'namespaceIri': 'https://example.org/travel/', 'projectStart': '2026-01-01'}
        if path == '/admin/hlist/search':
            return []
        response = self.http.get(path, headers={'Authorization': 'Bearer local'})
        if response.status_code == 404 and kwargs.get('missing_ok'):
            return None
        assert response.status_code == 200, response.json
        return response.json
    def get_bytes(self, path):
        response = self.http.get(path, headers={'Authorization': 'Bearer local'})
        assert response.status_code == 200, response.data
        return response.data
    def apply(self, operation):
        response = self.http.open(operation.path, method=operation.method, json=operation.payload,
                                  headers={'Authorization': 'Bearer local'})
        if response.status_code >= 400:
            raise ApiError(str(response.json), status=response.status_code)
        self.operations.append(operation)


def test_api_rdf_roundtrip_and_noop_reimport(store, tmp_path):
    con, project, http = store
    DataModel(con=con, project=project).create()
    client = FlaskTransport(http)
    doc = document()
    plan = plan_ontology_api(client, doc, {})
    apply_ontology_plan(client, plan, lambda message: None)
    snapshot = client.get_json('/admin/datamodel/travel')
    exported = api_model_to_yaml(client.get_json('/admin/project/travel'), snapshot, {})['ontology']
    assert exported['reifier_shapes'] == doc['reifier_shapes']
    replay = plan_ontology_api(client, exported, {})
    assert replay.operations == []
    backup = tmp_path / 'before.zip'
    write_api_backup(client, replay, backup)
    with ZipFile(backup) as archive:
        assert json.loads(archive.read('datamodel.json'))['reifierShapes']
        assert b'VisitAnnotationShape' in archive.read('model.trig')
    # Mutation and deletion exercise existing property endpoints, not only the
    # dedicated shape route. No stateful fake API substitutes for persistence.
    patch_doc = {'project': doc['project'], 'classes': {'travel:Travel': {'properties': [
        {'iri': 'travel:isAt', 'reification_required': False}]}},
        'reifier_shapes': {'travel:VisitAnnotationShape': {'properties': [{'iri': 'travel:dateTime', 'max_count': 2, 'min_count': 0}]}}}
    apply_ontology_plan(client, plan_ontology_api(client, patch_doc, {}), lambda message: None)
    assert not bool(DataModel.read(con, project, ignore_cache=True)[Xsd_QName('travel:Travel')][Xsd_QName('travel:isAt')].reificationRequired)
    clear = {'project': doc['project'], 'classes': {'travel:Travel': {'properties': [
        {'iri': 'travel:isAt', 'reifier_shapes': [], 'reification_required': None}]}},
        'reifier_shapes': {'travel:VisitAnnotationShape': None}}
    apply_ontology_plan(client, plan_ontology_api(client, clear, {}, remove_unused=True), lambda message: None)
    assert not DataModel.read(con, project, ignore_cache=True).reifier_shapes


def test_direct_invalid_reference_precedes_project_or_list_writes(store, tmp_path):
    from oldap_tools.ontology import load_ontology
    con, _, _ = store
    doc = document()
    doc['classes']['travel:Travel']['properties'][0]['reifier_shapes'] = ['travel:Missing']
    path = tmp_path / 'invalid.yaml'
    path.write_text(yaml.safe_dump({'ontology': doc}))
    with patch('oldap_tools.ontology._connect', return_value=con), patch(
        'oldap_tools.ontology._read_or_create_project') as project_writer, patch(
        'oldap_tools.ontology._load_lists') as list_writer:
        with pytest.raises(typer.Exit):
            load_ontology(graphdb_base='http://unused.invalid', repo='unused', inf=path,
                          user='test', password='test', mode='update', connector_mode='skip',
                          backup=False, backup_out=None)
        project_writer.assert_not_called()
        list_writer.assert_not_called()


@pytest.mark.parametrize('parents', ['dcterms:coverage', ['dcterms:coverage', 'dc:coverage']])
def test_superproperty_direct_yaml_rdf_roundtrip_and_replay(store, tmp_path, parents):
    from oldap_tools.ontology import _build_property, _dump_property, _sync_property
    from oldaplib.src.reifier_shape import ReifierShape

    con, project, _ = store
    spec = {'iri': 'travel:temporal', 'datatype': 'xsd:string', 'subproperty_of': parents}
    prop = _build_property(con, project, spec, {})
    shape = ReifierShape(con=con, project=project, shape_iri='travel:TemporalShape', properties=[prop])
    shape.create()
    shape = ReifierShape.read(con, project, 'travel:TemporalShape')
    loaded = shape['travel:temporal']
    expected = sorted([parents] if isinstance(parents, str) else parents)
    assert sorted(str(parent) for parent in loaded.subPropertyOf) == expected
    _sync_property(loaded, spec, {})
    assert not loaded.changeset
    exported = _dump_property(loaded)
    path = tmp_path / 'exported-parents.yaml'
    path.write_text(yaml.safe_dump({'ontology': {'project': {'shortname': 'travel'},
        'standalone_properties': {'travel:temporal': exported}}}), encoding='utf-8')
    imported = _read_yaml(path)['standalone_properties']['travel:temporal']
    assert imported['subproperty_of'] == expected
    _sync_property(loaded, imported, {})
    assert not loaded.changeset
    imported['max_count'] = 2
    _sync_property(loaded, imported, {})
    shape.update()
    reloaded = ReifierShape.read(con, project, 'travel:TemporalShape')['travel:temporal']
    assert sorted(str(parent) for parent in reloaded.subPropertyOf) == expected
