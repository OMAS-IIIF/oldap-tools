"""Managed fulltext preflight, final activation, backup and YAML round trip."""
import copy
import json
from uuid import uuid4
from unittest.mock import patch
from zipfile import ZipFile

import pytest
import yaml
from oldap_tools.api_client import ApiError
from oldap_tools.ontology_api import plan_ontology_api, write_api_backup, apply_ontology_plan
from oldap_tools.ontology_api_dump import dump_ontology_api
from oldap_tools.fulltext import plan_fulltext
from test_ontology_api import ReadClient, document


class Client(ReadClient):
    def __init__(self, state=None, **kwargs):
        super().__init__(**kwargs)
        self.state = state or {'project': 'demo', 'configuration': None, 'revision': None, 'status': 'absent'}
        self.failure = None

    def get_json(self, path, **kwargs):
        if path == '/admin/fulltext/demo':
            if self.failure:
                raise self.failure
            return copy.deepcopy(self.state)
        if path == '/admin/lucene/demo':
            raise AssertionError('Jena workflow must not query GraphDB connectors')
        return super().get_json(path, **kwargs)


def ontology():
    result = document()
    result['project']['namespace'] = 'https://example.org/demo/'
    result['fulltext'] = {'fields': {'title': ['schema:name'], 'related': ['demo:link', 'schema:name']}}
    return result


def test_activation_last_and_backup_contains_fulltext(tmp_path):
    client = Client()
    source = ontology()
    source['classes']['demo:Book']['label'] = {'en': 'Changed'}
    plan = plan_ontology_api(client, source, {}, fulltext_mode='apply')
    assert len(plan.operations) == 2
    assert plan.operations[-1].path == '/admin/fulltext/demo'
    assert plan.operations[-1].payload['expectedRevision'] is None
    target = tmp_path / 'backup.zip'
    write_api_backup(client, plan, target)
    with ZipFile(target) as archive:
        assert json.loads(archive.read('fulltext.json')) == client.state
    assert apply_ontology_plan(client, plan, lambda _: None) == (2, 0)


@pytest.mark.parametrize('status', [403, 404, 503])
def test_backend_or_permission_failure_prevents_any_mutation(status):
    client = Client()
    client.failure = ApiError('unavailable', status=status)
    with pytest.raises(ApiError):
        plan_ontology_api(client, ontology(), {}, fulltext_mode='apply')
    client.apply.assert_not_called()


def test_new_project_requires_provisioning_before_import():
    client = Client(project=None)
    with pytest.raises(ValueError, match='Create the project'):
        plan_ontology_api(client, ontology(), {}, fulltext_mode='apply')
    client.apply.assert_not_called()


def test_unchanged_index_is_noop_and_failure_never_retried():
    client = Client()
    plan = plan_ontology_api(client, ontology(), {}, fulltext_mode='apply')
    config = plan.operations[-1].payload['configuration']
    client.state = {'project': 'demo', 'configuration': config, 'revision': str(uuid4()), 'status': 'active'}
    assert plan_ontology_api(client, ontology(), {}, fulltext_mode='apply').operations == []
    client.apply.side_effect = ApiError('uncertain', status=503)
    with pytest.raises(ApiError, match='Earlier successful operations remain committed'):
        apply_ontology_plan(client, plan, lambda _: None)
    assert client.apply.call_count == 1


def test_dump_reloads_same_fields_without_native_connector_calls(tmp_path):
    client = Client()
    normalized = plan_fulltext(ontology())
    client.state = {'project': 'demo', 'configuration': {'graph': normalized['graph'], 'fields': normalized['fields']},
                    'revision': str(uuid4()), 'status': 'active'}
    with patch('oldap_tools.ontology_api_dump.OldapApiClient') as factory:
        remote = factory.return_value.__enter__.return_value
        remote.get_json.side_effect = client.get_json
        output = dump_ontology_api(api_base='http://unused', user='u', password='p', project_id='demo',
                                   out=tmp_path / 'ontology.yaml', emit=lambda _: None)
    dumped = yaml.safe_load(output.read_text())['ontology']
    assert 'lucene_connectors' not in dumped
    assert plan_fulltext(dumped) == normalized
    assert plan_ontology_api(client, dumped, {}, fulltext_mode='apply').operations == []


def test_mismatched_backend_graph_fails_before_apply():
    client = Client({'project': 'demo', 'configuration': {'graph': 'https://wrong/data', 'fields': {'title': ['https://schema.org/name']}},
                     'revision': str(uuid4()), 'status': 'active'})
    with pytest.raises(ValueError, match='graph differs'):
        plan_ontology_api(client, ontology(), {}, fulltext_mode='apply')
    client.apply.assert_not_called()


def test_default_dump_failure_does_not_publish_incomplete_yaml(tmp_path):
    """An unavailable Jena configuration must not silently lose search fields."""
    client = Client()
    client.failure = ApiError('unavailable', status=503)
    output = tmp_path / 'ontology.yaml'
    with patch('oldap_tools.ontology_api_dump.OldapApiClient') as factory:
        factory.return_value.__enter__.return_value.get_json.side_effect = client.get_json
        with pytest.raises(ApiError):
            dump_ontology_api(api_base='http://unused', user='u', password='p',
                              project_id='demo', out=output, emit=lambda _: None)
    assert not output.exists()
