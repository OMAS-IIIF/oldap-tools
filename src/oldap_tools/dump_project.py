import gzip
import json
from datetime import datetime
from pathlib import Path

import requests
import typer
import logging

from oldaplib.src.connection import Connection
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.project import Project
from oldaplib.src.user import User
from oldaplib.src.xsd.xsd_qname import Xsd_QName
from rdflib import Dataset

log = logging.getLogger(__name__)

def export_graphs_as_trig(
    graphdb_base: str,      # e.g. "http://localhost:7200"
    repo: str,              # e.g. "oldap"
    graph_iris: list[str],  # the 4 graphs you want
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
) -> str:
    ds = Dataset()

    for g in graph_iris:
        # RDF4J "statements" endpoint; context must be given as <IRI>
        url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
        params = {"context": f"<{g}>"}
        r = requests.get(
            url,
            params=params,
            headers={"Accept": "application/n-quads"},
            auth=auth,
            timeout=timeout,
        )
        if r.status_code != 200:
            log.error(f"ERROR: Request to '{url}' failed with status code {r.status_code}")
            raise typer.Exit(code=1)

        # N-Quads keeps the graph/context in each statement -> perfect for Dataset
        ds.parse(data=r.text, format="nquads")

    trig = ds.serialize(format="trig")
    return trig.decode("utf-8") if isinstance(trig, bytes) else trig


def dump_project(project_id: str,
                 graphdb_base: str,
                 repo: str,
                 out: Path,
                 include_data: bool,
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
    trig += "\n#\n# User info\n#\n"
    userIris = User.search(con=con, inProject=project.projectIri)
    for userIri in userIris:
        user = User.read(con=con, userId=str(userIri))
        user_json = json.dumps(user, default=serializer.encoder_default)
        trig += "#>> " + user_json + "\n"
    trig += "#<<\n\n"

    context = Context(name=con.context_name)
    trig += context.turtle_context
    trig += "#\n# Load the oldap:admin part\n#\n"
    trig += "oldap:admin {"

    trig += "\n#\n# Project info\n#\n"
    trig += project.trig_to_str(created=project.created, modified=project.modified, indent=1)
    trig += " .\n\n"

    trig += "\n#\n# PermissionSet info\n#\n"
    permsetQNames = PermissionSet.search(con=con, definedByProject=project.projectIri)
    for permsetQName in permsetQNames:
        permset = PermissionSet.read(con=con, qname=permsetQName)
        trig += permset.trig_to_str(created=permset.created, modified=permset.modified, indent=1)
        trig += " .\n\n"

    trig += "\n}\n\n"

    project_graphs = [
        str(context.qname2iri(Xsd_QName(project.projectShortName, "shacl"))),
        str(context.qname2iri(Xsd_QName(project.projectShortName, "onto"))),
        str(context.qname2iri(Xsd_QName(project.projectShortName, "lists"))),
    ]
    if include_data:
        project_graphs.append(str(context.qname2iri(Xsd_QName(project.projectShortName, "data"))))

    trig += export_graphs_as_trig(
        graphdb_base="http://localhost:7200",
        repo="oldap",
        graph_iris=project_graphs,
        auth=None,  # or None
    )

    with gzip.open(out, "wt", encoding="utf-8", newline="") as f:
        f.write(trig)


