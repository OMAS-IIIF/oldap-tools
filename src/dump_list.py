import logging
from pathlib import Path

import typer
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.oldaplist_helpers import ListFormat, dump_list_to
from oldaplib.src.project import Project

log = logging.getLogger(__name__)

def dump_list(project_id: str,
              list_id: str,
              graphdb_base: str,
              repo: str,
              filepath: Path,
              user: str,
              password: str,
              graphdb_user: str | None = None,
              graphdb_password: str | None = None
              ):
    try:
        con = Connection(server=graphdb_base,
                         repo=repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password,
                         context_name="DEFAULT")
        yamlfile = dump_list_to(con=con,
                                project=project_id,
                                oldapListId=list_id,
                                listformat=ListFormat.YAML,
                                ignore_cache=False)
    except OldapError as error:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {error}")
        raise typer.Exit(code=1)
    except FileNotFoundError as error:
        log.error(f"ERROR: File {filepath} not found': {error}")
        raise typer.Exit(code=1)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(yamlfile)
