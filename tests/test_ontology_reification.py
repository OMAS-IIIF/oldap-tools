"""Reification YAML preflight, ordering, replay, and persistence regressions."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from oldap_tools.ontology import _read_yaml, _property_kwargs, _sync_property, _dump_property
from oldap_tools.ontology_api import plan_ontology_api, prepare_api_ontology, apply_ontology_plan, _changes
from oldap_tools.ontology_api_dump import api_model_to_yaml
from oldap_tools.ontology_reification import prepare_reification
from oldap_tools.api_client import ApiError
from test_ontology_api import ReadClient, PROJECT, MODEL


def source():
    return {'project': {'shortname': 'demo'}, 'reifier_shapes': {
        'demo:VisitShape': {'properties': [{'iri': 'demo:time', 'datatype': 'xsd:dateTime', 'min_count': 1}]}},
        'classes': {'demo:Book': {'properties': [{'iri': 'demo:title',
            'reifier_shapes': ['demo:VisitShape'], 'reification_required': False}]}}}


def model():
    result = deepcopy(MODEL)
    result['reifierShapes'] = [{'iri': 'demo:VisitShape', 'properties': [
        {'iri': 'demo:time', 'datatype': 'xsd:dateTime', 'minCount': 1}]}]
    result['resources'][0]['properties'][0].update(reifierShapes=['demo:VisitShape'], reificationRequired=False)
    return result


def test_example_and_new_project_plan():
    path = Path(__file__).parents[1] / 'examples/ontology/travel-reification.yaml'
    doc, lists = prepare_api_ontology(path)
    class NewClient(ReadClient):
        def get_json(self, path, **kwargs):
            if path == '/admin/project/travel':
                return None
            raise AssertionError(path)
    operations = plan_ontology_api(NewClient(), doc, lists).operations
    shape = next(i for i, op in enumerate(operations) if '/reifier-shape/' in op.path)
    attach = next(i for i, op in enumerate(operations) if (op.payload or {}).get('reifierShapes'))
    assert shape < attach


def test_new_shape_precedes_context_owned_attachment_and_false_survives():
    client = ReadClient()
    ops = plan_ontology_api(client, source(), {}).operations
    assert len(ops) == 2
    assert '/reifier-shape/' in ops[0].path
    assert ops[1].payload == {'reifierShapes': ['demo:VisitShape'], 'reificationRequired': False}
    client.apply.assert_not_called()


def test_export_and_reimport_are_noop():
    snapshot = model()
    doc = api_model_to_yaml(PROJECT, snapshot, {})['ontology']
    assert doc['classes']['demo:Book']['properties'][0]['reification_required'] is False
    assert plan_ontology_api(ReadClient(snapshot), doc, {}).operations == []
    assert _changes({'reifierShapes': []}, {'reifierShapes': ['demo:VisitShape']}) == {'reifierShapes': []}


def test_partial_shape_fields_preserve_omission_and_remove_explicit_null():
    snapshot = model()
    snapshot['reifierShapes'][0]['properties'][0]['maxCount'] = 2
    doc = {'project': {'shortname': 'demo'}, 'reifier_shapes': {'demo:VisitShape': {
        'properties': [{'iri': 'demo:time', 'max_count': None}]}}}
    ops = plan_ontology_api(ReadClient(snapshot), doc, {}).operations
    assert ops[0].payload == {'properties': [{'iri': 'demo:time', 'datatype': 'xsd:dateTime', 'minCount': 1}]}
    doc['reifier_shapes']['demo:VisitShape'] = {}
    assert not plan_ontology_api(ReadClient(snapshot), doc, {}).operations


def test_shape_field_removal_requires_remove_unused():
    doc = {'project': {'shortname': 'demo'}, 'reifier_shapes': {'demo:VisitShape': {'properties': []}}}
    assert not plan_ontology_api(ReadClient(model()), doc, {}).operations
    ops = plan_ontology_api(ReadClient(model()), doc, {}, remove_unused=True).operations
    assert ops[0].payload == {'properties': []}


def test_delete_requires_flag_and_removing_references_first():
    doc = {'project': {'shortname': 'demo'}, 'reifier_shapes': {'demo:VisitShape': None}}
    with pytest.raises(ValueError, match='remove-unused'):
        plan_ontology_api(ReadClient(model()), doc, {})
    with pytest.raises(ValueError, match='Unknown or deleted'):
        plan_ontology_api(ReadClient(model()), doc, {}, remove_unused=True)
    doc['classes'] = {'demo:Book': {'properties': [{'iri': 'demo:title', 'reifier_shapes': [],
                                                  'reification_required': None}]}}
    ops = plan_ontology_api(ReadClient(model()), doc, {}, remove_unused=True).operations
    assert ops[0].payload == {'reifierShapes': [], 'reificationRequired': None}
    assert ops[-1].method == 'DELETE' and '/reifier-shape/' in ops[-1].path


@pytest.mark.parametrize('mutate,match', [
    (lambda doc: doc['reifier_shapes']['demo:VisitShape']['properties'][0].update(inverse_path='demo:x'), 'Unsupported'),
    (lambda doc: doc['reifier_shapes']['demo:VisitShape']['properties'][0].update(min_count=3, max_count=1), 'cardinality'),
    (lambda doc: doc['classes']['demo:Book']['properties'][0].update(reifier_shapes=['demo:Missing']), 'Unknown'),
    (lambda doc: doc['reifier_shapes']['demo:VisitShape']['properties'][0].pop('datatype'), 'exactly one'),
])
def test_invalid_input_fails_before_apply(mutate, match):
    doc = source()
    mutate(doc)
    client = ReadClient()
    with pytest.raises(ValueError, match=match):
        plan_ontology_api(client, doc, {})
    client.apply.assert_not_called()


def test_shared_reference_is_resolved_without_copying_shape():
    doc = source()
    doc.pop('reifier_shapes')
    doc['classes']['demo:Book']['properties'][0]['reifier_shapes'] = ['shared:VisitShape']
    class SharedClient(ReadClient):
        def get_json(self, path, **kwargs):
            if path == '/admin/project/shared':
                return dict(PROJECT, projectShortName='shared')
            if path == '/admin/datamodel/shared':
                return {'project': 'shared', 'externalOntologies': [], 'annotationProperties': [], 'resources': [],
                        'reifierShapes': [{'iri': 'shared:VisitShape', 'properties': []}]}
            return super().get_json(path, **kwargs)
    ops = plan_ontology_api(SharedClient(), doc, {}).operations
    assert len(ops) == 1 and '/reifier-shape/' not in ops[0].path


def test_inherited_reference_satisfies_child_flag():
    doc = source()
    doc['classes']['demo:Child'] = {'superclass': ['demo:Book'], 'properties': [
        {'iri': 'demo:title', 'datatype': 'xsd:string', 'reification_required': True}]}
    prepare_reification(doc, {})


def test_partial_apply_is_reported_and_fresh_plan_resumes_without_duplicate_shape():
    plan = plan_ontology_api(ReadClient(), source(), {})
    client = ReadClient()
    client.apply.side_effect = [None, ApiError('injected failure', status=503)]
    with pytest.raises(ApiError, match='1 successful operation'):
        apply_ontology_plan(client, plan, lambda message: None)
    snapshot = deepcopy(MODEL)
    snapshot['reifierShapes'] = model()['reifierShapes']
    remaining = plan_ontology_api(ReadClient(snapshot), source(), {}).operations
    assert len(remaining) == 1 and '/reifier-shape/' not in remaining[0].path


def test_legacy_annotation_metadata_does_not_block_unrelated_import():
    snapshot = deepcopy(MODEL)
    snapshot['annotationProperties'] = [{'iri': 'demo:legacy', 'datatype': 'xsd:string',
                                        'appliesToProperty': 'demo:other', 'type': ['StatementProperty']}]
    assert len(plan_ontology_api(ReadClient(snapshot), source(), {}).operations) == 2


def test_invalid_literal_constraint_on_object_field_fails_in_preflight():
    doc = source()
    field = doc['reifier_shapes']['demo:VisitShape']['properties'][0]
    field.pop('datatype')
    field.update(to_class='schema:Person', pattern='.*')
    with pytest.raises(ValueError, match='literal restrictions'):
        plan_ontology_api(ReadClient(), doc, {})


def test_protected_omitted_property_still_prevents_shape_deletion():
    snapshot = model()
    snapshot['resources'][0]['properties'][0]['projectid'] = 'shared'
    doc = {'project': {'shortname': 'demo'}, 'classes': {'demo:Book': {'properties': []}},
           'reifier_shapes': {'demo:VisitShape': None}}
    with pytest.raises(ValueError, match='Unknown or deleted'):
        plan_ontology_api(ReadClient(snapshot), doc, {}, remove_unused=True)


@pytest.mark.parametrize('parents', ['dcterms:coverage', ['dcterms:coverage'],
                                    ['dcterms:coverage', 'dc:coverage']])
def test_superproperty_yaml_export_import_roundtrip(tmp_path, parents):
    import yaml
    from oldaplib.src.helpers.observable_set import ObservableSet
    from oldaplib.src.enums.propertyclassattr import PropClassAttr
    from oldaplib.src.xsd.iri import Iri
    from types import SimpleNamespace

    # Real exports serialize the library's set-valued attribute, even for one parent.
    expected = sorted([parents] if isinstance(parents, str) else parents)
    prop = SimpleNamespace(property_class_iri='demo:temporal', _attributes={
        PropClassAttr.SUBPROPERTY_OF: ObservableSet({Iri(parent) for parent in expected})})
    exported = _dump_property(prop)
    assert exported['subproperty_of'] == expected
    doc = {'ontology': {'project': {'shortname': 'demo'}, 'standalone_properties': {
        'demo:temporal': {'datatype': 'xsd:string', 'subproperty_of': parents}}}}
    path = tmp_path / 'parents.yaml'
    path.write_text(yaml.safe_dump(doc), encoding='utf-8')
    imported = _read_yaml(path)
    kwargs = _property_kwargs(imported['standalone_properties']['demo:temporal'], {})
    # Both input forms normalize to the complete set expected by direct updates.
    assert sorted(str(value) for value in kwargs['subPropertyOf']) == expected
    doc['ontology']['standalone_properties']['demo:temporal'].update(exported)
    path.write_text(yaml.safe_dump(doc), encoding='utf-8')
    assert _read_yaml(path)['standalone_properties']['demo:temporal']['subproperty_of'] == expected


@pytest.mark.parametrize('parents', ['dcterms:coverage', ['dcterms:coverage', 'dc:coverage']])
def test_api_superproperty_export_reimport_is_noop(tmp_path, parents):
    import yaml

    snapshot = deepcopy(MODEL)
    snapshot['resources'][0]['properties'][0]['subPropertyOf'] = parents
    doc = api_model_to_yaml(PROJECT, snapshot, {})
    path = tmp_path / 'api-parents.yaml'
    path.write_text(yaml.safe_dump(doc), encoding='utf-8')
    parsed = _read_yaml(path)
    field = parsed['classes']['demo:Book']['properties'][0]
    # Direct exports normalize singletons to lists; order is never semantic.
    field['subproperty_of'] = [parents] if isinstance(parents, str) else list(reversed(parents))
    assert plan_ontology_api(ReadClient(snapshot), parsed, {}).operations == []
    assert _changes({'subPropertyOf': []}, {'subPropertyOf': parents}) == {'subPropertyOf': []}
