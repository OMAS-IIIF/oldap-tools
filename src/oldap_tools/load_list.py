import logging
from pathlib import Path

import typer
from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldap_tools.connection import create_connection
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.project import Project

from oldap_tools.list_merge import load_or_merge_lists_from_yaml

log = logging.getLogger(__name__)

def load_list(project_id: str,
              graphdb_base: str,
              repo: str,
              filepath: Path,
              user: str,
              password: str,
              graphdb_user: str | None = None,
              graphdb_password: str | None = None):

    try:
        connection = create_connection(
            graphdb_base=graphdb_base,
            repo=repo,
            graphdb_user=graphdb_user,
            graphdb_password=graphdb_password,
            user=user,
            password=password,
            context_name="DEFAULT",
        )
        project = Project.read(connection, project_id)
        CacheSingletonRedis().clear()
        load_or_merge_lists_from_yaml(con=connection, project=project, filepath=filepath)
    except OldapError as error:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {error}")
        raise typer.Exit(code=1)
    except ValueError as error:
        log.error(f"ERROR: Failed to load list YAML '{filepath}': {error}")
        raise typer.Exit(code=1)
    except FileNotFoundError as error:
        log.error(f"ERROR: File {filepath} not found': {error}")
        raise typer.Exit(code=1)
