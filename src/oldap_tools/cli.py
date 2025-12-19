from pathlib import Path

import typer
from importlib.metadata import version

from oldap_tools.config import AppConfig
from oldap_tools.dump_oldap import dump_oldap
from oldap_tools.load_oldap import load_oldap

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
                 user: str = typer.Option(None, "--user", "-u", help="GraphDB user"),
                 password: str = typer.Option(None, "--password", "-p", help="GraphDB password", hide_input=True)):
    setup_logging(verbose)
    ctx.obj = AppConfig(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
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
        out: Path = typer.Option(Path("dump.trig"), "--out", "-o", help="Output dump file"),
        include_data: bool = typer.Option(True, "--data/--no-data", help="Include project:data graph"),
):
    """Export project data."""
    typer.echo(f"Exporting '{project_id}' data to {out}")
    cfg = ctx.obj
    dump_oldap(project_id=project_id,
               graphdb_base=cfg.graphdb_base,
               repo=cfg.repo,
               out=out,
               include_data=include_data,
               user=cfg.user,
               password=cfg.password)

@project.command("load")
def project_load(ctx: typer.Context,
                 inf: Path = typer.Option(Path("dump.trig.gz"), "--inf", "-i", help="Input file for load")):
    cfg = ctx.obj
    load_oldap(graphdb_base=cfg.graphdb_base,
               repo=cfg.repo,
               inf=inf,
               user=cfg.user,
               password=cfg.password)

lists = typer.Typer(help="List-related commands")
app.add_typer(project, name="lists")

@lists.command("dump", help="Dump all project data to a JSON file.")
def list_dump(ctx: typer.Context,
              project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
              out: Path = typer.Option(Path("dump.trig"), "--out", "-o", help="Output dump file")):
    pass

@lists.command("load", help="Load project data from a JSON/YAML file.")
def list_load(ctx: typer.Context,
              project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
              inf: Path = typer.Option(Path("dump.trig.gz"), "--inf", "-i", help="Input file for load")):
    pass

def main():
    app()
