"""Managed fulltext API state validation and import planning, without retries."""
from uuid import UUID

from oldap_tools.api_client import ApiOperation, api_path
from oldap_tools.fulltext import plan_fulltext


def read_fulltext(client, project: str, namespace: str) -> dict:
    """Read explicit backend state; never treat a missing route as absence."""
    state = client.get_json(api_path('admin', 'fulltext', project))
    if not isinstance(state, dict) or set(state) != {'project', 'configuration', 'revision', 'status'} or state['project'] != project:
        raise ValueError('Invalid fulltext API state.')
    config, revision = state['configuration'], state['revision']
    if config is None:
        if revision is not None or state['status'] != 'absent':
            raise ValueError('Inconsistent absent fulltext state.')
    else:
        if not isinstance(revision, str) or str(UUID(revision)) != revision or state['status'] != 'active':
            raise ValueError('Invalid active fulltext revision/status.')
        if not isinstance(config, dict) or set(config) != {'graph', 'fields'} or config['graph'] != namespace + 'data':
            raise ValueError('Fulltext data graph differs from the API project namespace.')
        normalized = plan_fulltext({'project': {'shortname': project, 'namespace': namespace},
                                    'fulltext': {'fields': config['fields']}})
        if normalized['fields'] != config['fields']:
            raise ValueError('API fulltext fields must use full IRIs.')
    return state


def plan_fulltext_api(client, ontology: dict, project_before: dict | None):
    """Preflight an existing project's backend, permissions and current revision.

    Return a final activation operation and backup state. New projects must be
    provisioned first: absence cannot demonstrate that their API connection has
    the required backend capability and project authorization.
    """
    if 'fulltext' not in ontology:
        return None, None
    if project_before is None:
        raise ValueError('Create the project before importing an ontology with managed fulltext.')
    desired = plan_fulltext(ontology)
    namespace = project_before['namespaceIri']
    if desired['graph'] != namespace + 'data':
        raise ValueError('Fulltext YAML namespace differs from the API project.')
    state = read_fulltext(client, desired['project'], namespace)
    configuration = {'graph': desired['graph'], 'fields': desired['fields']}
    if configuration == state['configuration']:
        return None, state
    return ApiOperation('PUT', api_path('admin', 'fulltext', desired['project']),
                        {'configuration': configuration, 'expectedRevision': state['revision']}), state
