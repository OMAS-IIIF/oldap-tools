import gzip
import json
from datetime import datetime
from pathlib import Path

import typer
import logging

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.role import Role
from oldaplib.src.project import Project
from oldaplib.src.user import User
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.graph_helpers import export_graphs_as_trig

log = logging.getLogger(__name__)


def dump_project(project_id: str,
                 graphdb_base: str,
                 repo: str,
                 out: Path,
                 include_data: bool,
                 include_model: bool,
                 include_admin: bool,
                 user: str,
                 password: str,
                 graphdb_user: str | None = None,
                 graphdb_password: str | None = None):
    try:
        con = Connection(server=graphdb_base,
                         repo = repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)

    try:
        project = Project.read(con=con, projectIri_SName=project_id)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to read project '{project_id}': {e}")
        raise typer.Exit(code=1)

    trig = "################################################################################\n"
    trig += f"# Project: {project.projectShortName}\n"
    trig += f"# Date: {datetime.now().isoformat()}\n"
    trig += "################################################################################\n"

    context = Context(name=con.context_name)
    if include_admin:
        trig += "\n#\n# User info\n#\n"
        userIris = User.search(con=con, inProject=project.projectIri)
        for userIri in userIris:
            user = User.read(con=con, userId=str(userIri))
            user_json = json.dumps(user, default=serializer.encoder_default)
            trig += "#>> " + user_json + "\n"
        trig += "#<<\n\n"

        trig += context.turtle_context
        trig += "#\n# Load the oldap:admin part\n#\n"
        trig += "oldap:admin {"

        trig += "\n#\n# Project info\n#\n"
        trig += project.trig_to_str(created=project.created, modified=project.modified, indent=1)
        trig += " .\n\n"

        trig += "\n#\n# Roles info\n#\n"
        roleQNames = Role.search(con=con, definedByProject=project.projectIri)
        for roleQName in roleQNames:
            role = Role.read(con=con, qname=roleQName)
            trig += role.trig_to_str(created=role.created, modified=role.modified, indent=1)
            trig += " .\n\n"

        trig += "\n}\n\n"

    project_graphs = []
    if include_model:
        project_graphs.append(str(context.qname2iri(Xsd_QName(project.projectShortName, "shacl")))),
        project_graphs.append(str(context.qname2iri(Xsd_QName(project.projectShortName, "onto")))),
        project_graphs.append(str(context.qname2iri(Xsd_QName(project.projectShortName, "lists")))),

    if include_data:
        project_graphs.append(str(context.qname2iri(Xsd_QName(project.projectShortName, "data"))))

    trig += export_graphs_as_trig(
        graphdb_base=graphdb_base,
        repo=repo,
        graph_iris=project_graphs,
        auth=None,  # or None
    )

    with gzip.open(out, "wt", encoding="utf-8", newline="") as f:
        f.write(trig)


