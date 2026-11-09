"""Offline fulltext configuration and import safety contracts."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from typer.testing import CliRunner

from oldap_tools.cli import app
from oldap_tools.fulltext import plan_fulltext
from oldap_tools.ontology import load_ontology
from oldap_tools.ontology_api import load_ontology_api, plan_ontology_api


@pytest.fixture
def ontology():
    return {'project': {'shortname': 'demo', 'namespace': 'https://example.org/demo/'},
            'external_ontologies': {'custom': {'namespace': 'https://example.org/custom#'}},
            'fulltext': {'fields': {'title': ['schema:name'], 'alias': ['schema:name'],
                                   'linked': ['demo:link', 'custom:text']}}}


def write_yaml(tmp_path, ontology):
    path = tmp_path / 'ontology.yaml'
    path.write_text(yaml.safe_dump({'ontology': ontology}))
    return path


def test_plan_resolves_paths_and_deduplicates_terminal_predicates(ontology):
    before = deepcopy(ontology)
    plan = plan_fulltext(ontology)
    assert plan['graph'] == 'https://example.org/demo/data'
    assert plan['fields']['linked'] == ['https://example.org/demo/link', 'https://example.org/custom#text']
    assert plan['indexed_predicates'] == ['https://example.org/custom#text', 'https://schema.org/name']
    assert ontology == before


def test_namespace_does_not_leak_between_documents(ontology):
    plan_fulltext(ontology)
    del ontology['external_ontologies']
    with pytest.raises(Exception, match='prefix'):
        plan_fulltext(ontology)


@pytest.mark.parametrize('configuration', [
    {'fields': {}}, {'fields': {'title': []}}, {'fields': {'title': 'schema:name'}},
    {'fields': {'title': ['unknown:name']}}, {'fields': {'title': ['schema:name']}, 'languages': ['en']},
    {'fields': {'invalid field': ['schema:name']}}, None,
])
def test_cli_validation_rejects_invalid_fulltext(tmp_path, ontology, configuration):
    ontology['fulltext'] = configuration
    result = CliRunner().invoke(app, ['ontology', 'validate', '-i', str(write_yaml(tmp_path, ontology))])
    assert result.exit_code == 1


def test_offline_cli_requires_no_credentials(tmp_path, ontology):
    path = write_yaml(tmp_path, ontology)
    with patch('requests.sessions.Session.request', side_effect=AssertionError('Network forbidden')):
        result = CliRunner().invoke(app, ['ontology', 'fulltext-plan', '-i', str(path)])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout) == plan_fulltext(ontology)
        assert CliRunner().invoke(app, ['ontology', 'validate', '-i', str(path)]).exit_code == 0


def test_mixed_formats_and_namespace_conflicts_rejected(ontology):
    ontology['lucene_connectors'] = {}
    with pytest.raises(ValueError, match='either'):
        plan_fulltext(ontology)
    del ontology['lucene_connectors']
    ontology['external_ontologies']['demo'] = {'namespace': 'https://wrong.example/'}
    with pytest.raises(ValueError, match='Conflicting'):
        plan_fulltext(ontology)


def test_imports_fail_before_authentication_or_writes(tmp_path, ontology):
    path = write_yaml(tmp_path, ontology)
    with patch('oldap_tools.ontology_api.OldapApiClient') as client:
        with pytest.raises(ValueError, match='not yet supported'):
            load_ontology_api(api_base='http://unused', user='x', password='x', inf=path)
        client.assert_not_called()
    with patch('oldap_tools.ontology._connect') as connect:
        with pytest.raises(ValueError, match='not yet supported'):
            load_ontology(graphdb_base='http://unused', repo='x', inf=path, user='x', password='x',
                          mode='update', connector_mode='skip', backup=False, backup_out=None)
        connect.assert_not_called()
    client = Mock()
    with pytest.raises(ValueError, match='not yet supported'):
        plan_ontology_api(client, ontology, {})
    assert not client.mock_calls


def test_fasnacht_example_includes_current_document_text_and_paths():
    path = Path(__file__).resolve().parents[1] / 'examples/ontology/fasnacht-jena.yaml'
    result = CliRunner().invoke(app, ['ontology', 'fulltext-plan', '-i', str(path)])
    assert result.exit_code == 0, result.output
    plan = json.loads(result.stdout)
    assert len(plan['fields']) == 9
    assert len(plan['indexed_predicates']) == 5
    assert plan['fields']['archiveMediaObjectText'] == ['http://fasnacht.digital/ns/searchableText']
    assert plan['fields']['representedArchiveObjectTitle'] == [
        'http://fasnacht.digital/ns/archiveMediaObjectOf', 'https://schema.org/name']
