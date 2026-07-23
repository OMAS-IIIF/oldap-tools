import logging
from pathlib import Path

import typer
from oldap_tools.connection import create_connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.project import Project
from oldaplib.src.xsd.xsd_qname import Xsd_QName

log = logging.getLogger(__name__)


def delete_projectdata(project_id: str,
                       graphdb_base: str,
                       repo: str,
                       out: Path,
                       user: str,
                       password: str,
                       graphdb_user: str | None = None,
                       graphdb_password: str | None = None) -> None:
    try:
        con = create_connection(
            graphdb_base=graphdb_base,
            repo=repo,
            graphdb_user=graphdb_user,
            graphdb_password=graphdb_password,
            user=user,
            password=password,
        )
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)
    context = Context(name=con.context_name)

    try:
        project = Project.read(con=con, projectIri_SName=project_id)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to read project '{project_id}': {e}")
        raise typer.Exit(code=1)

    con.clear_graph(Xsd_QName(project.projectShortName, "data"))

