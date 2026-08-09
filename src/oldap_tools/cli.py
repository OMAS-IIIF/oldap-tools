from pathlib import Path

import typer

from oldap_tools.archive import load_archive, read_archive_yaml
from oldap_tools.dump_list import dump_list
from oldap_tools.config import AppConfig
from oldap_tools.dump_project import dump_project
from oldap_tools.load_list import load_list
from oldap_tools.load_project import load_project
from oldap_tools.load_sysgraph import load_sysgraph, restore_sysgraph, purge_sysgraph, SystemGraphs
from oldap_tools.ontology import dump_ontology, load_ontology, validate_ontology_yaml
from oldap_tools.staging_folders import ensure_mobile_folders
from oldap_tools import __version__

from oldap_tools.logging import setup_logging


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


app = typer.Typer(
    no_args_is_help=True,
    help="OLDAP command line tools"
)

@app.callback()
def app_callback(ctx: typer.Context,
                 verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose (debug) logging"),
                 version: bool = typer.Option(
                     False,
                     "--version",
                     "--show-version",
                     help="Show version information and exit",
                     callback=version_callback,
                     is_eager=True,
                 ),
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

project = typer.Typer(help="Project-related commands")
app.add_typer(project, name="project")

@project.command("dump")
def project_dump(
        ctx: typer.Context,
        project_id: str = typer.Argument(..., help="Project ID (e.g. swissbritnet, hyha, ...)"),
        out: Path = typer.Option(Path("<project>.trig.gz"), "--out", "-o", help="Output dump file"),
        include_data: bool = typer.Option(True, "--data/--no-data", help="Include '<project>:data' graph"),
        include_model: bool = typer.Option(True, "--model/--no-model", help="Include '<project>:model' graph"),
        include_admin: bool = typer.Option(True, "--admin/--no-admin", help="Include '<project>:admin' graph"),
        include_lists: bool = typer.Option(True, "--lists/--no-lists", help="Include '<project>:lists' graph")
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
                 include_model=include_model,
                 include_admin=include_admin,
                 include_lists=include_lists,
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

sys = typer.Typer(help="System graphs commands")
app.add_typer(sys, name="system")

@sys.command("load", help="Load system graph from trig")
def sys_load(ctx: typer.Context,
             graph: SystemGraphs = typer.Argument(..., help="System graph to load. Allowed are 'oldap', 'shared', 'admin'."),
             inf: Path = typer.Option(Path("oldap.trig"),"--inf", "-i", help="Input file for load")):
    cfg = ctx.obj
    load_sysgraph(graphdb_base=cfg.graphdb_base,
                  repo=cfg.repo,
                  inf=inf,
                  graph=graph,
                  user=cfg.user,
                  password=cfg.password,
                  graphdb_user=cfg.graphdb_user,
                  graphdb_password=cfg.graphdb_password)


@sys.command("restore", help="Restore system graph from last backup")
def sys_restore(ctx: typer.Context,
                graph: SystemGraphs = typer.Argument(..., help="System graph to restore. Allowed are 'oldap', 'shared', 'admin'.")):
    cfg = ctx.obj
    restore_sysgraph(graphdb_base=cfg.graphdb_base,
                     repo=cfg.repo,
                     graph=graph,
                     user=cfg.user,
                     password=cfg.password,
                     graphdb_user=cfg.graphdb_user,
                     graphdb_password=cfg.graphdb_password)

@sys.command("purge", help="Purge system graph from last backup")
def sys_purge(ctx: typer.Context,
                graph: SystemGraphs = typer.Argument(..., help="System graph to purge backup. Allowed are 'oldap', 'shared', 'admin'.")):
    cfg = ctx.obj
    purge_sysgraph(graphdb_base=cfg.graphdb_base,
                   repo=cfg.repo,
                   graph=graph,
                   user=cfg.user,
                   password=cfg.password,
                   graphdb_user=cfg.graphdb_user,
                   graphdb_password=cfg.graphdb_password)

ontology = typer.Typer(help="Ontology datamodel commands")
app.add_typer(ontology, name="ontology")


@ontology.command("validate", help="Validate an ontology YAML file.")
def ontology_validate(
        inf: Path = typer.Option(..., "--inf", "-i", help="Input ontology YAML file"),
        schema: Path | None = typer.Option(None, "--schema", "-s", help="Alternative Yamale schema file")):
    validate_ontology_yaml(inf=inf, schema=schema)
    typer.echo(f"{inf} is valid")


@ontology.command("load", help="Load or update an ontology datamodel from YAML.")
def ontology_load(
        ctx: typer.Context,
        inf: Path = typer.Option(..., "--inf", "-i", help="Input ontology YAML file"),
        mode: str = typer.Option("update", "--mode", "-m", help="Load mode: 'update' or 'replace'"),
        connectors: str = typer.Option("skip", "--connectors", help="Lucene connector mode: 'skip', 'create', or 'replace'"),
        backup: bool = typer.Option(True, "--backup/--no-backup", help="Dump model and lists before loading"),
        backup_out: Path | None = typer.Option(None, "--backup-out", help="Backup TriG gzip output file")):
    cfg = ctx.obj
    load_ontology(graphdb_base=cfg.graphdb_base,
                  repo=cfg.repo,
                  inf=inf,
                  user=cfg.user,
                  password=cfg.password,
                  mode=mode,
                  connector_mode=connectors,
                  backup=backup,
                  backup_out=backup_out,
                  graphdb_user=cfg.graphdb_user,
                  graphdb_password=cfg.graphdb_password)


@ontology.command("dump", help="Dump an ontology datamodel to YAML or TriG.")
def ontology_dump(
        ctx: typer.Context,
        project_id: str = typer.Argument(..., help="Project ID (e.g. fasnacht, hyha, ...)"),
        out: Path = typer.Option(Path("ontology.yaml"), "--out", "-o", help="Output file"),
        fmt: str = typer.Option("yaml", "--format", "-f", help="Output format: 'yaml' or 'trig'"),
        include_taxonomies: bool = typer.Option(
            False,
            "--include-taxonomies",
            help="When dumping YAML, also write all project taxonomies as <ListId>.yaml and reference them from ontology.lists.",
        )):
    cfg = ctx.obj
    dump_ontology(graphdb_base=cfg.graphdb_base,
                  repo=cfg.repo,
                  project_id=project_id,
                  out=out,
                  fmt=fmt,
                  user=cfg.user,
                  password=cfg.password,
                  include_taxonomies=include_taxonomies,
                  graphdb_user=cfg.graphdb_user,
                  graphdb_password=cfg.graphdb_password)


archive = typer.Typer(help="Archive structure commands")
app.add_typer(archive, name="archive")


@archive.command("validate", help="Validate an archive structure YAML file.")
def archive_validate(
        inf: Path = typer.Option(..., "--inf", "-i", help="Input archive YAML file"),
        schema: Path | None = typer.Option(None, "--schema", "-s", help="Alternative Yamale schema file")):
    """Validate archive YAML without connecting to OLDAP."""

    try:
        read_archive_yaml(inf=inf, project_shortname="archive", schema=schema)
    except ValueError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"{inf} is valid")


@archive.command("load", help="Add a YAML-defined archive structure to an existing project.")
def archive_load(
        ctx: typer.Context,
        project_id: str = typer.Argument(..., help="Existing target project shortname or IRI"),
        inf: Path = typer.Option(..., "--inf", "-i", help="Input archive YAML file"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--apply",
            help="Preflight only, or create the archive units",
        )):
    """Preflight and optionally add archive units without changing existing data."""

    cfg = ctx.obj
    try:
        plan = load_archive(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            project_id=project_id,
            inf=inf,
            dry_run=dry_run,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
    except Exception as error:
        typer.echo(f"Archive load failed: {error}", err=True)
        raise typer.Exit(code=1) from error

    action = "Would create" if dry_run else "Created"
    typer.echo(f"{action} {len(plan.units)} archive unit(s) in project {project_id}.")
    for unit in plan.units:
        parent = f" below {unit.parent_iri}" if unit.parent_iri is not None else " as a root"
        typer.echo(f"- {unit.iri} [{unit.level}]{parent}")


staging = typer.Typer(help="StagingArea maintenance commands")
app.add_typer(staging, name="staging")


@staging.command("ensure-mobile-folder")
def staging_ensure_mobile_folder(
        ctx: typer.Context,
        project_id: str = typer.Option("fasnacht", "--project", help="Project containing the StagingAreas"),
        staging_area: list[str] | None = typer.Option(
            None,
            "--staging-area",
            help="StagingArea IRI to process; may be supplied more than once",
        ),
        all_areas: bool = typer.Option(False, "--all", help="Process every StagingArea in the project"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--apply",
            help="Validate and report only, or create missing Mobile folders",
        )):
    """Ensure the protected Mobile system folder below each selected top folder."""

    cfg = ctx.obj
    try:
        plans = ensure_mobile_folders(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            project_id=project_id,
            staging_area_iris=staging_area,
            all_areas=all_areas,
            dry_run=dry_run,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error

    for plan in plans:
        if plan.needs_creation:
            action = "would create" if dry_run else "created"
            typer.echo(f"{plan.area.iri}: {action} Mobile below {plan.top_folder_iri}")
        else:
            typer.echo(f"{plan.area.iri}: Mobile already exists ({plan.existing_mobile_folder_iri})")

def main():
    app()
