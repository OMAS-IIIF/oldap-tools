"""Bounded native dumps, atomic file replacement and explicit backend routing."""
import gzip
import json
from unittest.mock import Mock

import pytest
from oldap_tools import jena_project_transfer as transfer
from oldaplib.src import jena_connection
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration, OldapErrorValue


@pytest.mark.parametrize('backend,expected', [('jena', True), ('graphdb', False)])
def test_backend_is_explicit(monkeypatch, backend, expected):
    monkeypatch.setenv('OLDAP_BACKEND', backend)
    assert transfer.enabled() is expected


def test_unknown_backend_never_falls_back_to_graphdb(monkeypatch):
    monkeypatch.setenv('OLDAP_BACKEND', 'jenna')
    with pytest.raises(OldapErrorConfiguration):
        transfer.enabled()


def test_admin_dump_refused_before_connecting(monkeypatch, tmp_path):
    connection = Mock()
    monkeypatch.setattr(jena_connection, 'JenaConnection', connection)
    with pytest.raises(OldapErrorConfiguration, match='no-admin'):
        transfer.dump('demo', tmp_path / 'dump.gz', ['data'], user='root', password='secret', include_admin=True)
    connection.assert_not_called()


def test_roundtrip_keeps_native_trig_and_graph_scope(monkeypatch, tmp_path):
    trig = '<urn:demo:data> { _:g <urn:reifies> <<( <urn:s> <urn:p> "v" )>> . }'
    con = Mock()
    con._project_graph_export.return_value = trig
    monkeypatch.setattr(jena_connection, 'JenaConnection', Mock(return_value=con))
    cache = Mock()
    monkeypatch.setattr(transfer, 'CacheSingletonRedis', Mock(return_value=cache))
    path = tmp_path / 'dump.gz'
    transfer.dump('demo', path, ['data'], user='root', password='secret', include_admin=False)
    transfer.load(path, user='root', password='secret')
    con._project_graph_import.assert_called_once_with('demo', ['data'], trig)
    assert cache.clear.call_count == 2
    assert 'secret' not in gzip.decompress(path.read_bytes()).decode()


@pytest.mark.parametrize('failure', ['remote', 'size'])
def test_failed_dump_preserves_existing_destination(monkeypatch, tmp_path, failure):
    path = tmp_path / 'dump.gz'
    path.write_bytes(b'existing')
    con = Mock()
    if failure == 'remote':
        con._project_graph_export.side_effect = OldapErrorValue('refused')
    else:
        con._project_graph_export.return_value = 'x' * transfer.MAX_REQUEST
    monkeypatch.setattr(jena_connection, 'JenaConnection', Mock(return_value=con))
    with pytest.raises(OldapErrorValue):
        transfer.dump('demo', path, ['data'], user='root', password='secret', include_admin=False)
    assert path.read_bytes() == b'existing'


@pytest.mark.parametrize('content', ['# GraphDB old dump\n', transfer.MARKER + '{bad\n',
    transfer.MARKER + json.dumps({'version': 1, 'project': 'demo', 'parts': ['admin']}) + '\n',
    'x' * (transfer.MAX_REQUEST + 1)])
def test_invalid_dump_never_connects(monkeypatch, tmp_path, content):
    path = tmp_path / 'dump.gz'
    path.write_bytes(gzip.compress(content.encode()))
    connection = Mock()
    monkeypatch.setattr(jena_connection, 'JenaConnection', connection)
    with pytest.raises(OldapErrorValue):
        transfer.load(path, user='root', password='secret')
    connection.assert_not_called()


def test_post_commit_cache_failure_does_not_look_like_a_failed_import(monkeypatch, tmp_path):
    path = tmp_path / 'dump.gz'
    path.write_bytes(gzip.compress((transfer.MARKER + json.dumps(
        {'version': 1, 'project': 'demo', 'parts': ['data']}) + '\n').encode()))
    con = Mock()
    monkeypatch.setattr(jena_connection, 'JenaConnection', Mock(return_value=con))
    cache = Mock()
    cache.clear.side_effect = [None, RuntimeError('offline')]
    monkeypatch.setattr(transfer, 'CacheSingletonRedis', Mock(return_value=cache))
    with pytest.raises(OldapErrorConfiguration, match='Import committed'):
        transfer.load(path, user='root', password='secret')
    con._project_graph_import.assert_called_once()


def test_cache_failure_before_import_never_changes_rdf(monkeypatch, tmp_path):
    path = tmp_path / 'dump.gz'
    path.write_bytes(gzip.compress((transfer.MARKER + json.dumps(
        {'version': 1, 'project': 'demo', 'parts': ['data']}) + '\n').encode()))
    con = Mock()
    monkeypatch.setattr(jena_connection, 'JenaConnection', Mock(return_value=con))
    cache = Mock()
    cache.clear.side_effect = RuntimeError('offline')
    monkeypatch.setattr(transfer, 'CacheSingletonRedis', Mock(return_value=cache))
    with pytest.raises(RuntimeError, match='offline'):
        transfer.load(path, user='root', password='secret')
    con._project_graph_import.assert_not_called()


def test_existing_public_project_functions_route_to_jena_without_graphdb(monkeypatch, tmp_path):
    from oldap_tools.dump_project import dump_project
    from oldap_tools.load_project import load_project
    monkeypatch.setenv('OLDAP_BACKEND', 'jena')
    export, restore = Mock(), Mock()
    monkeypatch.setattr(transfer, 'dump', export)
    monkeypatch.setattr(transfer, 'load', restore)
    path = tmp_path / 'dump.gz'
    dump_project('demo', 'unused', 'unused', path, True, True, False, False, 'root', 'secret')
    export.assert_called_once_with('demo', path, ['shacl', 'onto', 'data'], user='root', password='secret', include_admin=False)
    load_project('unused', 'unused', path, 'root', 'secret')
    restore.assert_called_once_with(path, user='root', password='secret')


def test_graphdb_backend_selection_does_not_require_jena_library(monkeypatch):
    """Released GraphDB libraries need not contain the new Jena module."""
    import runpy
    import sys
    monkeypatch.setenv('OLDAP_BACKEND', 'graphdb')
    monkeypatch.setitem(sys.modules, 'oldaplib.src.jena_connection', None)
    namespace = runpy.run_path(transfer.__file__)
    assert namespace['enabled']() is False


def test_dump_accounts_for_native_header_at_transfer_limit(monkeypatch, tmp_path):
    """Do not replace a backup with a dump that the bounded loader rejects."""
    payload = {'project': 'demo', 'parts': ['data'], 'trig': ''}
    trig = 'x' * (transfer.MAX_REQUEST - len(json.dumps(payload).encode()))
    assert len(json.dumps({**payload, 'trig': trig}).encode()) == transfer.MAX_REQUEST
    con = Mock()
    con._project_graph_export.return_value = trig
    monkeypatch.setattr(jena_connection, 'JenaConnection', Mock(return_value=con))
    path = tmp_path / 'dump.gz'
    path.write_bytes(b'previous backup')
    with pytest.raises(OldapErrorValue, match='limit'):
        transfer.dump('demo', path, ['data'], user='root', password='secret', include_admin=False)
    assert path.read_bytes() == b'previous backup'
