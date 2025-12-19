import argparse
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path
from pprint import pprint
import logging
import requests
from rdflib import Dataset

from oldaplib.src.cachesingleton import CacheSingletonRedis
from oldaplib.src.connection import Connection
from oldaplib.src.datamodel import DataModel
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.oldaperror import OldapError, OldapErrorAlreadyExists
from oldaplib.src.helpers.serializer import serializer
from oldaplib.src.iconnection import IConnection
from oldaplib.src.oldaplist import OldapList
from oldaplib.src.permissionset import PermissionSet
from oldaplib.src.project import Project
from oldaplib.src.user import User
from oldaplib.src.xsd.xsd_qname import Xsd_QName

logger = logging.getLogger(__name__)


def _make_parser() -> argparse.ArgumentParser:
    """
    Create and configure an ArgumentParser for the OLDAP Tools command-line utility.

    This function sets up an ArgumentParser that includes various arguments and
    subcommands for the OLDAP Tools command-line utility. It returns the configured
    ArgumentParser instance, which can parse user-provided command-line arguments.
    The parser supports operations such as dumping and loading project data in JSON
    format.

    :returns: A configured ArgumentParser instance for parsing command-line arguments.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description=f"OLDAP TOOLS (Version 0.0.1), ©2025 by lukas.rosenthaler@pm.me)"
    )
    parser.add_argument("-u", "--user", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-s", "--server", default="http://localhost:7200")
    parser.add_argument("-r", "--repo", default="oldap")
    parser.add_argument("--loglevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    subparsers = parser.add_subparsers(
        title="Subcommands", description="Valid subcommands are", help="sub-command help"
    )
    parser_dump = subparsers.add_parser(
        name="dump",
        help="Dump all project data to a JSON file. This includes, project info, users, datamodel and data"
    )
    parser_dump.set_defaults(action="dump")
    parser_dump.add_argument("outfile", help="Name of output file")
    parser_dump.add_argument("--project", required=True, help="Project IRI or short name")

    parser_load = subparsers.add_parser(
        name="load",
        help="Load project data from a JSON file. This includes, project info, users, datamodel and data"
    )
    parser_load.set_defaults(action="load")
    parser_load.add_argument("infile", help="Name of input file")

    return parser

def _parse_arguments(
    user_args: list[str],
    parser: argparse.ArgumentParser,
) -> argparse.Namespace:
    """
    Parses command-line arguments provided by the user and ensures
    that a valid "action" attribute is present. If the "action"
    attribute is missing, displays help information and exits the
    program.

    :param user_args: A list of string arguments provided by the user for parsing.
    :param parser: The ArgumentParser instance used to parse the provided arguments.
    :return: The parsed arguments as a Namespace object.
    :rtype: argparse.Namespace
    """
    args = parser.parse_args(user_args)
    if not hasattr(args, "action"):
        parser.print_help(sys.stderr)
        sys.exit(1)
    return args

def _call_requested_action(con: IConnection, args: argparse.Namespace) -> bool:
    """
    Executes the requested action based on the supplied arguments and connection.

    This function performs actions such as "dump" or "load" depending on the
    value of ``args.action``. For the "dump" action, it exports the
    specified project to an output file using the provided connection. For the
    "load" action, it currently sets the operation as successful. If an invalid
    action is given, it logs an error message and sets the operation as
    unsuccessful.

    :param con: Connection object used to interact with the relevant system.
        Should conform to the IConnection interface.
    :param args: Parsed arguments namespace containing the action to execute
        and its associated parameters.
    :return: A boolean indicating whether the requested action executed
        successfully.
    """
    if args.action == "dump":
        success = dump_project(con=con, projectId=args.project, outfile=args.outfile)
    elif args.action == "load":
        success = load_project(args=args, infile=args.infile)
    else:
        success = False
        print(f"ERROR: Unknown action '{args.action}'")
    return success

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
        r.raise_for_status()

        # N-Quads keeps the graph/context in each statement -> perfect for Dataset
        ds.parse(data=r.text, format="nquads")

    trig = ds.serialize(format="trig")
    return trig.decode("utf-8") if isinstance(trig, bytes) else trig


# Example:

def dump_project(con: IConnection, projectId: str, outfile: str) -> bool:
    try:
        project = Project.read(con=con, projectIri_SName=projectId)
    except OldapError as e:
        print(f"ERROR: Failed to read project '{project}': {e}")
        return False

    trig = f"# Project: {project.projectShortName}\n"
    trig += f"# Date: {datetime.now().isoformat()}\n"
    trig += "################################################################################\n"
    trig += "\n#\n# User info\n#\n"
    userIris = User.search(con=con, inProject=project.projectIri)
    for userIri in userIris:
        user = User.read(con=con, userId=str(userIri))
        user_json = json.dumps(user, default=serializer.encoder_default)
        trig += "#>> " + user_json + "\n"
        #userx = json.loads(user_json, object_hook=serializer.make_decoder_hook(connection=con))
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
    logger.error(f"Found {len(permsetQNames)} permission sets")
    for permsetQName in permsetQNames:
        permset = PermissionSet.read(con=con, qname=permsetQName)
        trig += permset.trig_to_str(created=permset.created, modified=permset.modified, indent=1)
        trig += " .\n\n"

    # trig += "\n#\n# User info\n#\n"
    # userIris = User.search(con=con, inProject=project.projectIri)
    # for userIri in userIris:
    #     user = User.read(con=con, userId=str(userIri))
    #     trig += user.trig_to_str(created=user.created, modified=user.modified, indent=1)
    #     trig += " .\n\n"
    trig += "\n}\n\n"

    project_graphs = [
        str(context.qname2iri(Xsd_QName(project.projectShortName, "shacl"))),
        str(context.qname2iri(Xsd_QName(project.projectShortName, "onto"))),
        str(context.qname2iri(Xsd_QName(project.projectShortName, "lists"))),
        str(context.qname2iri(Xsd_QName(project.projectShortName, "data"))),
    ]

    trig += export_graphs_as_trig(
        graphdb_base="http://localhost:7200",
        repo="oldap",
        graph_iris=project_graphs,
        auth=None,  # or None
    )

    path = Path(outfile)
    path = path.with_suffix(".trig.gz")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        f.write(trig)


    return True

def import_trig(
    graphdb_base: str,
    repo: str,
    trig_str: str,
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
):
    url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
    r = requests.post(
        url,
        data=trig_str.encode("utf-8"),
        headers={"Content-Type": "application/trig"},
        auth=auth,
        timeout=timeout,
    )
    r.raise_for_status()

def import_trig_gz(
    graphdb_base: str,
    repo: str,
    trig_gz: bytes,
    auth: tuple[str, str] | None = None,
    timeout: int = 120,
):
    url = f"{graphdb_base.rstrip('/')}/repositories/{repo}/statements"
    r = requests.post(
        url,
        data=trig_gz,
        headers={
            "Content-Type": "application/trig",
            "Content-Encoding": "gzip",
        },
        auth=auth,
        timeout=timeout,
    )
    r.raise_for_status()

def load_project(args: argparse.Namespace, infile: str) -> bool:
    cache = CacheSingletonRedis()
    cache.clear()

    path = Path(infile)
    path = path.with_suffix(".trig.gz")
    with open(path, "rb") as f:
        import_trig_gz(graphdb_base="http://localhost:7200",
                       repo="oldap",
                       trig_gz=f.read())

    con = Connection(server=args.server, userId=args.user, credentials=args.password, repo=args.repo)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.startswith('#>>'):
                user_json = line[3:].strip()
                user = json.loads(user_json, object_hook=serializer.make_decoder_hook(connection=con))
                try:
                    existing_user = User.read(con=con, userId=user.userId)
                except OldapErrorAlreadyExists:
                    # user does not exist -> create it
                    user.create(keep_dates=True)
                    logger.info(f"Created user {user.userId}")
                else:
                    # user exists -> update it
                    if user.hasPermissions != existing_user.hasPermissions or user.inProject != existing_user.inProject:
                        existing_user.delete()
                        user.create(keep_dates=True)
                        logger.info(f"Updated (replaced) user {user.userId}")
                    pass
            if line.startswith('#<<'):
                break

    return True

def main():
    parser = _make_parser()
    args = parser.parse_args()
    if not hasattr(args, "action"):
        parser.print_help(sys.stderr)
        sys.exit(1)
    match args.loglevel:
        case "DEBUG":
            logger.setLevel(logging.DEBUG)
        case "INFO":
            logger.setLevel(logging.INFO)
        case "WARNING":
            logger.setLevel(logging.WARNING)
        case "ERROR":
            logger.setLevel(logging.ERROR)
        case "CRITICAL":
            logger.setLevel(logging.CRITICAL)
        case _:
            raise ValueError(f"Invalid log level: {args.loglevel}")

    try:
        con = Connection(server=args.server, userId=args.user, credentials=args.password, repo=args.repo)
    except OldapError as e:
        print(f"ERROR: Failed to connect to OLDAP server: {e}")
        sys.exit(1)
    success = _call_requested_action(con, args)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
