import logging
from pathlib import Path

import typer
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.oldaplist_helpers import load_list_from_yaml
from oldaplib.src.project import Project

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
        connection = Connection(server=graphdb_base,
                                repo=repo,
                                dbuser=graphdb_user,
                                dbpassword=graphdb_password,
                                userId=user,
                                credentials=password,
                                context_name="DEFAULT")
        project = Project.read(connection, project_id)
        listnodes = load_list_from_yaml(con=connection,
                                        project=project_id,
                                        filepath=filepath)
    except OldapError as error:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {error}")
        raise typer.Exit(code=1)
    except FileNotFoundError as error:
        log.error(f"ERROR: File {filepath} not found': {error}")
        raise typer.Exit(code=1)

