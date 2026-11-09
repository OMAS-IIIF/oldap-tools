"""Scoped native RDF 1.2 project dumps for explicitly configured Jena hosts.

This administrative transport deliberately excludes users/roles and requires an
already provisioned project. It preserves existing project dump/load signatures;
backend selection is explicit through OLDAP_BACKEND, never inferred from a URL.
"""
import gzip
import json
import os
from pathlib import Path
import tempfile

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.helpers.oldaperror import OldapErrorConfiguration, OldapErrorValue

MARKER = '# OLDAP-JENA-PROJECT '
MAX_REQUEST = 262144  # Existing migration service request limit, including JSON.


def enabled() -> bool:
    """Refuse misspelled backend settings instead of selecting the wrong store."""
    backend = os.getenv('OLDAP_BACKEND', 'graphdb')
    if backend not in {'graphdb', 'jena'}:
        raise OldapErrorConfiguration('OLDAP_BACKEND must be graphdb or jena.')
    return backend == 'jena'


def dump(project: str, out: Path, parts: list[str], *, user: str, password: str, include_admin: bool):
    """Write one gzip TriG snapshot atomically; leave an existing file on failure.

    Args:
        project: Existing project short name.
        out: Destination file; replaced only after complete serialization.
        parts: Selected data, shacl, onto and/or lists graph suffixes.
        user: OLDAP root administrator's login.
        password: OLDAP password; never included in output.
        include_admin: Must be false until administrative identity migration is supported.
    """
    if include_admin:
        raise OldapErrorConfiguration('Jena project dump currently requires --no-admin; provision target project, roles and users separately.')
    # Legacy GraphDB installations may not contain the Jena transport module.
    from oldaplib.src.jena_connection import JenaConnection
    con = JenaConnection(userId=user, credentials=password)
    trig = con._project_graph_export(project, parts)
    metadata = {'version': 1, 'project': project, 'parts': parts}
    # Ensure our own bounded migration dump can be loaded by the same protocol.
    payload = {'project': project, 'parts': parts, 'trig': trig}
    content = MARKER + json.dumps(metadata) + '\n' + trig
    # The loader bounds the native file too; its header is not the HTTP envelope.
    if max(len(content.encode('utf-8')), len(json.dumps(payload).encode('utf-8'))) > MAX_REQUEST:
        raise OldapErrorValue('Project exceeds the migration transfer request limit; streaming transfer is not yet supported.')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=out.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with gzip.open(temporary, 'wt', encoding='utf-8') as handle:
            handle.write(content)
        temporary.replace(out)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load(inf: Path, *, user: str, password: str):
    """Validate a native dump then atomically append it to its existing project.

    Administrative GraphDB dumps are explicitly refused. No graph replacement,
    user deletion, namespace remapping or automatic RDF-star conversion occurs.
    Reimporting blank nodes creates new nodes, matching additive RDF import.
    """
    with gzip.open(inf, 'rt', encoding='utf-8') as handle:
        content = handle.read(MAX_REQUEST + 1)
    if len(content) > MAX_REQUEST:
        raise OldapErrorValue('Dump exceeds the bounded migration transfer limit.')
    header, separator, trig = content.partition('\n')
    if not separator or not header.startswith(MARKER):
        raise OldapErrorValue('Expected a native Jena project dump; legacy GraphDB/admin dumps require a separate migration.')
    try:
        metadata = json.loads(header[len(MARKER):])
    except json.JSONDecodeError as error:
        raise OldapErrorValue('Invalid Jena project dump metadata.') from error
    if (not isinstance(metadata, dict) or set(metadata) != {'version', 'project', 'parts'}
            or type(metadata['version']) is not int or metadata['version'] != 1 or not isinstance(metadata['project'], str)
            or not isinstance(metadata['parts'], list)
            or any(part not in ('data', 'shacl', 'onto', 'lists') for part in metadata['parts'])):
        raise OldapErrorValue('Invalid Jena project dump metadata.')
    payload = {'project': metadata['project'], 'parts': metadata['parts'], 'trig': trig}
    if len(json.dumps(payload).encode('utf-8')) > MAX_REQUEST:
        raise OldapErrorValue('Dump exceeds the migration transfer request limit.')
    # Legacy GraphDB installations may not contain the Jena transport module.
    from oldaplib.src.jena_connection import JenaConnection
    con = JenaConnection(userId=user, credentials=password)
    cache = CacheSingletonRedis()
    cache.clear()  # Detect unavailable/misconfigured cache before changing RDF.
    con._project_graph_import(metadata['project'], metadata['parts'], trig)
    try:
        cache.clear()
    except Exception as error:
        raise OldapErrorConfiguration(
            'Import committed, but cache invalidation failed; repair the cache and do not reimport.'
        ) from error
