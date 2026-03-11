import logging
from enum import Enum
from pathlib import Path
from typing import Literal

import typer
from oldaplib.src.connection import Connection
from oldaplib.src.helpers.oldaperror import OldapError
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.load_project import import_trig, import_trig_gz

class SystemGraphs(str, Enum):
    oldap = "oldap"
    shared = "shared"
    admin = "admin"


log = logging.getLogger(__name__)

def load_sysgraph(
        graph: SystemGraphs,
        inf: Path,
        graphdb_base: str,
        repo: str,
        user: str,
        password: str,
        graphdb_user: str | None = None,
        graphdb_password: str | None = None) -> None:

    try:
        con = Connection(server=graphdb_base,
                         repo=repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)

    try:
        if graph == 'oldap':
            if con.graph_exists(Xsd_QName('oldap:shacl')):
                con.move_graph(Xsd_QName('oldap:shacl'), Xsd_QName('oldap:shacl_bak'))
            if con.graph_exists(Xsd_QName('oldap:onto')):
                con.move_graph(Xsd_QName('oldap:onto'), Xsd_QName('oldap:onto_bak'))
        if graph == 'shared':
            if con.graph_exists(Xsd_QName('shared:shacl')):
                con.move_graph(Xsd_QName('shared:shacl'), Xsd_QName('shared:shacl_bak'))
            if con.graph_exists(Xsd_QName('shared:onto')):
                con.move_graph(Xsd_QName('shared:onto'), Xsd_QName('shared:onto_bak'))
        if graph == 'admin':
            if con.graph_exists(Xsd_QName('oldap:admin')):
                con.move_graph(Xsd_QName('oldap:admin'), Xsd_QName('oldap:admin_bak'))
    except OldapError as e:
        log.error(f"Failed to move graphs '{graph}': {e}")
        raise typer.Exit(code=1)

    if graph == 'oldap':
        inf = inf / 'oldap.trig'
    elif graph == 'shared':
        inf = inf / 'shared.trig'
    elif graph == 'admin':
        inf = inf / 'admin.trig'
    else:
        log.error(f"Invalid graph '{graph}' specified")
        raise typer.Exit(code=1)
    if not inf.exists():
        log.error(f"File '{inf}' does not exist to load graph '{graph}'")
        raise typer.Exit(code=1)

    try:
        with open(inf, "rb") as f:
            import_trig(graphdb_base=graphdb_base,
                        repo=repo,
                        auth=(graphdb_user, graphdb_password) if graphdb_user and graphdb_password else None,
                        trig_str=f.read().decode("utf-8"))
    except FileNotFoundError as e:
        log.error(f"File '{inf}' not found to load graph '{graph}': {e}")
        raise typer.Exit(code=1)
    except PermissionError as e:
        log.error(f"No permission to read file '{inf}': {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        log.error(f"Could not load graph '{graph}' from '{inf}': {e}")
        raise typer.Exit(code=1)
    log.info(f"Loaded graph '{graph}' from '{inf}' successfully")

def restore_sysgraph(
        graph: SystemGraphs,
        graphdb_base: str,
        repo: str,
        user: str,
        password: str,
        graphdb_user: str | None = None,
        graphdb_password: str | None = None) -> None:

    try:
        con = Connection(server=graphdb_base,
                         repo=repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password)
    except OldapError as e:
        log.error(f"ERROR: Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)

    try:
        if graph == 'oldap':
            con.move_graph(Xsd_QName('oldap:shacl_bak'), Xsd_QName('oldap:shacl'))
            con.move_graph(Xsd_QName('oldap:onto_bak'), Xsd_QName('oldap:onto'))
        if graph == 'shared':
            con.move_graph(Xsd_QName('shared:shacl_bak'), Xsd_QName('shared:shacl'))
            con.move_graph(Xsd_QName('shared:onto_bak'), Xsd_QName('shared:onto'))
        if graph == 'admin':
            con.move_graph(Xsd_QName('oldap:admin_bak'), Xsd_QName('oldap:admin'))
    except OldapError as e:
        log.error(f"ERROR: Failed to restore graphs '{graph}': {e}")
        raise typer.Exit(code=1)


def purge_sysgraph(graph: SystemGraphs,
                   graphdb_base: str,
                   repo: str,
                   user: str,
                   password: str,
                   graphdb_user: str | None = None,
                   graphdb_password: str | None = None) -> None:
    try:
        con = Connection(server=graphdb_base,
                         repo=repo,
                         dbuser=graphdb_user,
                         dbpassword=graphdb_password,
                         userId=user,
                         credentials=password)
    except OldapError as e:
        log.error(f"Failed to connect to GraphDB database at '{graphdb_base}': {e}")
        raise typer.Exit(code=1)

    try:
        if graph == 'oldap':
            con.clear_graph(Xsd_QName('oldap:shacl_bak'))
            con.clear_graph(Xsd_QName('oldap:onto_bak'))
        if graph == 'shared':
            con.clear_graph(Xsd_QName('shared:shacl_bak'))
            con.clear_graph(Xsd_QName('shared:onto_bak'))
        if graph == 'admin':
            con.clear_graph(Xsd_QName('oldap:admin_bak'))
    except OldapError as e:
        log.error(f"ERROR: Failed to clear backup graph '{graph}_bak': {e}")
        raise typer.Exit(code=1)
    log.info(f"Cleared backup graph '{graph}_bak' successfully")
