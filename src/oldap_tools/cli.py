import enum
from pathlib import Path

import typer
from importlib.metadata import version

from dump_list import dump_list
from oldap_tools.config import AppConfig
from oldap_tools.dump_project import dump_project
from oldap_tools.load_list import load_list
from oldap_tools.load_project import load_project

from oldap_tools.logging import setup_logging

app = typer.Typer(
    no_args_is_help=True,
    help="OLDAP command line tools"
)

@app.callback()
def app_callback(ctx: typer.Context,
                 verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose (debug) logging"),
                 graphdb_base: str = typer.Option("http://localhost:7200", "--graphdb", "-g", help="GraphDB base URL"),
                 repo: str = typer.Option("oldap", "--repo", "-r", help="GraphDB repository"),
                 user: str = typer.Option(..., "--user", "-u", help="OLDAP user"),
                 password: str = typer.Option(..., "--password", "-p", help="OLDAP password", hide_input=True),
                 graphdb_user: str = typer.Option(None, "--graphdb_user", envvar="GRAPHDB_USER", help="GraphDB user"),
                 graphdb_password: str = typer.Option(None, "--graphdb_password", envvar="GRAPHDB_PASSWORD", help="GraphDB password", hide_input=True)
                 ):
    setup_logging(verbose)
    ctx.obj = AppConfig(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password
    )

@app.command()
def show_version():
    """Show version information."""
    typer.echo(version("oldap-tools"))

project = typer.Typer(help="Project-related commands")
app.add_typer(project, name="project")

@project.command("dump")
def project_dump(
        ctx: typer.Context,
        project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
        out: Path = typer.Option(Path("<project>.trig.gz"), "--out", "-o", help="Output dump file"),
        include_data: bool = typer.Option(True, "--data/--no-data", help="Include '<project>:data' graph"),
):
    """Export project data."""
    if out == Path("<project>.trig.gz"):
        out = Path(project_id).with_suffix(".trig.gz")
    typer.echo(f"Exporting '{project_id}' data to {out}")
    cfg = ctx.obj
    dump_project(project_id=project_id,
                 graphdb_base=cfg.graphdb_base,
                 repo=cfg.repo,
                 out=out,
                 include_data=include_data,
                 user=cfg.user,
                 password=cfg.password,
                 graphdb_user=cfg.graphdb_user,
                 graphdb_password=cfg.graphdb_password)

@project.command("load")
def project_load(ctx: typer.Context,
                 inf: Path = typer.Option(Path("dump.trig.gz"), "--inf", "-i", help="Input file for load")):
    cfg = ctx.obj
    load_project(graphdb_base=cfg.graphdb_base,
                 repo=cfg.repo,
                 inf=inf,
                 user=cfg.user,
                 password=cfg.password,
                 graphdb_user=cfg.graphdb_user,
                 graphdb_password=cfg.graphdb_password)

lists = typer.Typer(help="List-related commands")
app.add_typer(lists, name="lists")

@lists.command("dump", help="Dump all list data to a YAML file.")
def list_dump(ctx: typer.Context,
              project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
              list_id: str = typer.Argument(..., help="List ID (e.g. 'CreativeCommons', 'BuildingCategories', ...)"),
              out: Path = typer.Option(Path("dump.trig"), "--out", "-o", help="Output dump file")):
    cfg = ctx.obj
    dump_list(project_id=project_id,
              list_id=list_id,
              graphdb_base=cfg.graphdb_base,
              repo=cfg.repo,
              filepath=out,
              user=cfg.user,
              password=cfg.password,
              graphdb_user = cfg.graphdb_user,
              graphdb_password = cfg.graphdb_password
    )

@lists.command("load", help="Load project data from a JSON/YAML file.")
def list_load(ctx: typer.Context,
              project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
              inf: Path = typer.Option(Path("dump.trig.gz"), "--inf", "-i", help="Input file for load")):
    cfg = ctx.obj
    load_list(project_id=project_id,
              graphdb_base=cfg.graphdb_base,
              repo=cfg.repo,
              filepath=inf,
              user=cfg.user,
              password=cfg.password)

def main():
    app()
