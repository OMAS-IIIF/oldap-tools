from pathlib import Path

import typer

from oldap_tools.archive import load_archive, read_archive_yaml
from oldap_tools.dump_list import dump_list
from oldap_tools.config import AppConfig
from oldap_tools.data_batch import run_batch_import, write_batch_report
from oldap_tools.data_import import run_data_import
from oldap_tools.data_prepare import prepare_data_file
from oldap_tools.data_yaml import DataValidationError, load_data_document
from oldap_tools.media_ingest import MediaIngestError, run_media_attach
from oldap_tools.fasnacht_taxonomy_inventory import (
    run_fasnacht_taxonomy_inventory,
    write_inventory_report,
)
from oldap_tools.fasnacht_taxonomy_migration import (
    apply_fasnacht_taxonomy_migration,
    run_fasnacht_taxonomy_migration_plan,
    write_migration_plan,
)
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
                 api_base: str = typer.Option("http://localhost:8000", "--api", help="OLDAP API base URL"),
                 media_base: str = typer.Option("http://localhost:8088", "--media", help="OLDAP media-server base URL"),
                 user: str | None = typer.Option(None, "--user", "-u", help="OLDAP user (required for connected commands)"),
                 password: str | None = typer.Option(None, "--password", "-p", help="OLDAP password (required for connected commands)", hide_input=True),
                 graphdb_user: str = typer.Option(None, "--graphdb_user", envvar="GRAPHDB_USER", help="GraphDB user"),
                 graphdb_password: str = typer.Option(None, "--graphdb_password", envvar="GRAPHDB_PASSWORD", help="GraphDB password", hide_input=True)
                 ):
    setup_logging(verbose)
    ctx.obj = AppConfig(
        graphdb_base=graphdb_base,
        repo=repo,
        api_base=api_base,
        media_base=media_base,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password
    )


def connection_config(ctx: typer.Context) -> AppConfig:
    """Return CLI configuration after enforcing connected-command credentials."""
    cfg = ctx.obj
    if not isinstance(cfg, AppConfig):
        raise typer.BadParameter("OLDAP command configuration is unavailable.")
    missing = []
    if not cfg.user:
        missing.append("--user")
    if not cfg.password:
        missing.append("--password")
    if missing:
        raise typer.BadParameter(
            f"Connected commands require {' and '.join(missing)}. "
            "Offline validate commands do not require credentials."
        )
    return cfg

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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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
    cfg = connection_config(ctx)
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


data = typer.Typer(help="Versioned OLDAP instance-data commands")
app.add_typer(data, name="data")


@data.command("validate", help="Validate an OLDAP instance-data YAML or JSON file.")
def data_validate(
        inf: Path = typer.Option(..., "--inf", "-i", help="Input data YAML or JSON file")):
    """Validate format version 1 locally without connecting to OLDAP."""

    try:
        document = load_data_document(inf)
    except DataValidationError as error:
        typer.echo(f"Data validation failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"{inf} is valid OLDAP data version {document.version} "
        f"({len(document.resources)} resource(s), project {document.project})"
    )
    if document.auto_iri_count:
        typer.echo(
            f"Contains {document.auto_iri_count} unresolved iri: auto placeholder(s); "
            "run data prepare before live import."
        )


@data.command("prepare", help="Mint stable IRIs for resource-level iri: auto placeholders.")
def data_prepare_command(
        inf: Path = typer.Option(..., "--inf", "-i", help="Input data YAML or JSON file"),
        out: Path = typer.Option(..., "--out", "-o", help="Prepared output in the same directory"),
        force: bool = typer.Option(False, "--force", help="Replace an existing output file")):
    """Prepare stable resource identities offline without contacting OLDAP."""

    try:
        count = prepare_data_file(inf, out, force=force)
    except DataValidationError as error:
        typer.echo(f"Data preparation failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Prepared {count} resource IRI(s) in {out}. "
        "Use this output for dry-run, apply, and resume."
    )


@data.command("import", help="Preflight or create resources in a live OLDAP project.")
def data_import_command(
        ctx: typer.Context,
        inf: Path = typer.Option(..., "--inf", "-i", help="Input data YAML or JSON file"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--apply",
            help="Read-only preflight, or create one resource unless --batch is set",
        ),
        batch: bool = typer.Option(
            False,
            "--batch",
            help="Allow resumable sequential processing of multiple resources",
        ),
        report: Path | None = typer.Option(
            None,
            "--report",
            help="Batch audit report (.json, .yaml, or .yml)",
        )):
    """Preflight instance data or create resources without overwriting."""

    operation = "Data preflight" if dry_run else "Data import"
    try:
        document = load_data_document(inf)
    except DataValidationError as error:
        typer.echo(f"{operation} failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    cfg = connection_config(ctx)
    if report is not None and not batch:
        typer.echo("Data import failed: --report requires --batch.", err=True)
        raise typer.Exit(code=1)

    if batch:
        try:
            plan, batch_execution = run_batch_import(
                graphdb_base=cfg.graphdb_base,
                repo=cfg.repo,
                user=cfg.user,
                password=cfg.password,
                document=document,
                apply=not dry_run,
                api_base=cfg.api_base,
                media_base=cfg.media_base,
                graphdb_user=cfg.graphdb_user,
                graphdb_password=cfg.graphdb_password,
            )
        except Exception as error:
            typer.echo(f"Batch {operation.lower()} failed before processing: {error}", err=True)
            raise typer.Exit(code=1) from error

        report_error: Exception | None = None
        if report is not None:
            try:
                write_batch_report(report, batch_execution)
            except Exception as error:
                report_error = error

        typer.echo(
            f"Batch {'dry-run' if dry_run else 'apply'} completed for "
            f"{len(plan.resources)} resource(s) in project {plan.project}."
        )
        for result in batch_execution.resources:
            line = (
                f"- {result.iri}: metadata={result.metadata_status}, "
                f"media={result.media_status}"
            )
            if result.error:
                line += f"; error={result.error}"
            typer.echo(line)
        if report is not None and report_error is None:
            typer.echo(f"Report written to {report}.")
        if report_error is not None:
            typer.echo(
                f"Batch processing completed, but report writing failed: {report_error}",
                err=True,
            )
        if not batch_execution.succeeded or report_error is not None:
            raise typer.Exit(code=1)
        return

    try:
        execution = run_data_import(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            document=document,
            apply=not dry_run,
            api_base=cfg.api_base,
            media_base=cfg.media_base,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
    except Exception as error:
        typer.echo(f"{operation} failed: {error}", err=True)
        raise typer.Exit(code=1) from error

    plan = execution.plan
    if dry_run:
        typer.echo(
            f"Dry-run passed for {len(plan.resources)} resource(s) in project "
            f"{plan.project}; no data was written."
        )
    else:
        typer.echo(
            f"Created {len(execution.created_iris)} resource(s) in project {plan.project}."
        )
    for resource in plan.resources:
        action = "would create" if dry_run else "created"
        typer.echo(
            f"- {action} {resource.iri} [{resource.resource_class}] "
            f"with {resource.property_count} properties and "
            f"{resource.reference_count} typed reference(s)"
        )
        if resource.media_action:
            typer.echo(f"  media: {resource.media_action}")
    for media_result in execution.media_results:
        typer.echo(
            f"- attached media {media_result.asset_id} to {media_result.resource_iri}; "
            f"IIIF {media_result.width or '?'}x{media_result.height or '?'}"
        )


@data.command("media-attach", help="Preflight or attach media to one existing resource.")
def data_media_attach_command(
        ctx: typer.Context,
        inf: Path = typer.Option(..., "--inf", "-i", help="Input data YAML or JSON file"),
        dry_run: bool = typer.Option(
            True,
            "--dry-run/--apply",
            help="Verify source and target, or attach and verify the media",
        )):
    """Finish or idempotently verify a document-declared media attachment."""

    operation = "Media preflight" if dry_run else "Media attachment"
    try:
        document = load_data_document(inf)
    except DataValidationError as error:
        typer.echo(f"{operation} failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    cfg = connection_config(ctx)
    try:
        plan, results = run_media_attach(
            document,
            api_base=cfg.api_base,
            media_base=cfg.media_base,
            user=cfg.user,
            password=cfg.password,
            apply=not dry_run,
        )
    except MediaIngestError as error:
        typer.echo(f"{operation} failed: {error}", err=True)
        raise typer.Exit(code=1) from error

    if dry_run:
        typer.echo(
            f"Media dry-run passed for {plan.resource_iri}: would copy "
            f"{plan.original_name} as {plan.ingest_profile}; no data was written."
        )
        return
    result = results[0]
    action = "imported and attached" if result.imported_now else "already attached and verified"
    typer.echo(
        f"Media {action}: {result.asset_id} -> {result.resource_iri} "
        f"({result.protocol}, {result.width or '?'}x{result.height or '?'})."
    )


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

    cfg = connection_config(ctx)
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

    cfg = connection_config(ctx)
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


fasnacht = typer.Typer(help="Fasnacht project migration and audit commands")
app.add_typer(fasnacht, name="fasnacht")


@fasnacht.command("taxonomy-inventory")
def fasnacht_taxonomy_inventory(
        ctx: typer.Context,
        mapping: Path = typer.Option(
            Path("fasnacht/TaxonomyPhase1Mapping.yaml"),
            "--mapping",
            help="Version-1 Phase-1 mapping YAML",
        ),
        out: Path = typer.Option(..., "--out", "-o", help="Read-only report (.json, .yaml, or .yml)"),
        project_id: str = typer.Option("fasnacht", "--project", help="Project to inspect")):
    """Inventory taxonomy references and strict empty-year event candidates."""

    cfg = connection_config(ctx)
    try:
        report = run_fasnacht_taxonomy_inventory(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            mapping_path=mapping,
            project_id=project_id,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
        write_inventory_report(out, report)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    event_report = report["events"]
    typer.echo(
        f"Read-only taxonomy inventory written to {out}: "
        f"{event_report['eventCount']} event(s), "
        f"{event_report['reviewCandidateCount']} empty-year review candidate(s), "
        f"{event_report['deletionCandidateCount']} strict empty-year candidate(s)."
    )


@fasnacht.command("taxonomy-migration-plan")
def fasnacht_taxonomy_migration_plan(
        ctx: typer.Context,
        mapping: Path = typer.Option(
            Path("fasnacht/TaxonomyPhase1Mapping.yaml"),
            "--mapping",
            help="Version-1 Phase-1 mapping YAML",
        ),
        decisions: Path = typer.Option(
            Path("fasnacht/TaxonomyPhase2LocalDecisions.yaml"),
            "--decisions",
            help="Version-1 reviewed Phase-2 decisions YAML",
        ),
        out: Path = typer.Option(..., "--out", "-o", help="Dry-run manifest (.json, .yaml, or .yml)"),
        project_id: str = typer.Option("fasnacht", "--project", help="Project to inspect")):
    """Materialize the current Phase-2 data migration as a read-only manifest."""

    cfg = connection_config(ctx)
    try:
        plan = run_fasnacht_taxonomy_migration_plan(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            mapping_path=mapping,
            decisions_path=decisions,
            project_id=project_id,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
        write_migration_plan(out, plan)
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    summary = plan["summary"]
    typer.echo(
        f"Read-only migration plan written to {out}; digest {plan['digest']}: "
        f"{summary['actionableReferenceCount']} change(s), "
        f"{summary['unchangedReferenceCount']} unchanged, "
        f"{summary['unresolvedReferenceCount']} unresolved, "
        f"{summary['outOfScopeReferenceCount']} out of scope, "
        f"{summary['ruleCountErrorCount']} rule-count error(s)."
    )


@fasnacht.command("taxonomy-migration-apply")
def fasnacht_taxonomy_migration_apply(
        ctx: typer.Context,
        expected_digest: str = typer.Option(..., "--expected-digest", help="Digest from the immediately preceding dry-run"),
        backup_out: Path = typer.Option(..., "--backup-out", help="New full project backup (.trig.gz)"),
        mapping: Path = typer.Option(Path("fasnacht/TaxonomyPhase1Mapping.yaml"), "--mapping"),
        decisions: Path = typer.Option(Path("fasnacht/TaxonomyPhase2LocalDecisions.yaml"), "--decisions"),
        ontology_path: Path = typer.Option(Path("fasnacht/fasnacht-onto.yaml"), "--ontology"),
        object_taxonomy: Path = typer.Option(Path("fasnacht/ObjectTaxonomy.yaml"), "--object-taxonomy"),
        event_taxonomy: Path = typer.Option(Path("fasnacht/CarnivalEventTaxonomy.yaml"), "--event-taxonomy"),
        practice_taxonomy: Path = typer.Option(Path("fasnacht/CarnivalPracticeTaxonomy.yaml"), "--practice-taxonomy"),
        project_id: str = typer.Option("fasnacht", "--project"),
        allow_local_rehearsal: bool = typer.Option(
            False,
            "--allow-local-rehearsal",
            help="Explicitly permit a decisions file whose status is local-rehearsal",
        )):
    """Apply the reviewed local cutover; never migrates organisations or deletes events."""

    cfg = connection_config(ctx)
    try:
        result = apply_fasnacht_taxonomy_migration(
            graphdb_base=cfg.graphdb_base,
            repo=cfg.repo,
            user=cfg.user,
            password=cfg.password,
            mapping_path=mapping,
            decisions_path=decisions,
            ontology_path=ontology_path,
            object_taxonomy_path=object_taxonomy,
            event_taxonomy_path=event_taxonomy,
            practice_taxonomy_path=practice_taxonomy,
            backup_path=backup_out,
            expected_digest=expected_digest,
            project_id=project_id,
            allow_local_rehearsal=allow_local_rehearsal,
            graphdb_user=cfg.graphdb_user,
            graphdb_password=cfg.graphdb_password,
        )
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error

    typer.echo(
        f"Taxonomy migration {result['digest']} applied: "
        f"{result['changedReferenceCount']} reference change(s), "
        f"backup {result['backup']} (sha256 {result['backupSha256']})."
    )

def main():
    app()
