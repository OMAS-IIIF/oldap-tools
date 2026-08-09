"""Validate and add YAML-defined archive trees to an OLDAP project.

The module deliberately implements create-only semantics. YAML identifiers map
to stable project IRIs, existing resources are never updated, moved, or deleted,
and an optional external parent may only be used on a top-level YAML unit.
"""

from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yamale
import yaml
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.project import Project
from oldaplib.src.xsd.dating import Dating
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.connection import create_connection


ARCHIVE_LEVELS = frozenset(
    {"ArchiveGroup", "Fonds", "Subfonds", "Series", "Subseries", "File", "Item"}
)


@dataclass(frozen=True)
class ArchiveUnitSpec:
    """One normalized archive unit from the recursive YAML document."""

    unit_id: str
    iri: Iri
    level: str
    title: LangString
    parent_iri: Iri | None
    parent_is_external: bool = False
    identifier: str | None = None
    description: LangString | None = None
    dating: Dating | None = None
    extent: LangString | None = None
    creators: tuple[Iri, ...] = ()
    provenance: LangString | None = None
    access_conditions: LangString | None = None
    about: tuple[Iri, ...] = ()
    position: int | None = None


@dataclass(frozen=True)
class ArchiveDefinition:
    """Validated and flattened archive import definition."""

    version: int
    language: str
    units: tuple[ArchiveUnitSpec, ...]


@dataclass(frozen=True)
class ArchiveImportPlan:
    """Preflight result for a create-only archive import."""

    project_id: str
    units: tuple[ArchiveUnitSpec, ...]
    external_parent_iris: tuple[Iri, ...] = field(default_factory=tuple)


def archive_schema_path() -> Path:
    """Return the bundled Yamale schema path for archive YAML files."""

    return Path(str(resources.files("oldap_tools") / "schemas" / "archive_schema.yaml"))


def validate_archive_yaml(inf: Path, schema: Path | None = None) -> None:
    """Validate an archive YAML file against the structural schema.

    Args:
        inf: YAML document to validate.
        schema: Optional alternative Yamale schema.

    Raises:
        ValueError: If the document does not satisfy the schema.
    """

    try:
        schema_obj = yamale.make_schema(str(schema or archive_schema_path()))
        data = yamale.make_data(str(inf))
        yamale.validate(schema=schema_obj, data=data)
    except Exception as error:
        raise ValueError(f"Archive YAML validation failed: {error}") from error


def _lang_string(value: str | dict[str, str], default_language: str, field_name: str) -> LangString:
    """Convert scalar or language-map YAML text to an OLDAP LangString."""

    if isinstance(value, str):
        values = [f"{value}@{default_language}"]
    else:
        if not value:
            raise ValueError(f'Field "{field_name}" must not be an empty language map.')
        values = [f"{text}@{language}" for language, text in value.items()]
    try:
        return LangString(values)
    except Exception as error:
        raise ValueError(f'Invalid multilingual value in "{field_name}": {error}') from error


def _optional_lang_string(
    value: str | dict[str, str] | None,
    default_language: str,
    field_name: str,
) -> LangString | None:
    """Convert an optional YAML text value to an OLDAP LangString."""

    return None if value is None else _lang_string(value, default_language, field_name)


def _project_iri(project_shortname: Xsd_NCName, unit_id: str) -> Iri:
    """Build the stable project QName used as a unit's persistent IRI."""

    try:
        fragment = Xsd_NCName(unit_id, validate=True)
    except Exception as error:
        raise ValueError(f'Archive unit id "{unit_id}" is not a valid NCName.') from error
    return Iri(Xsd_QName(project_shortname, fragment))


def _as_iri(value: str, field_name: str) -> Iri:
    """Convert a YAML IRI/QName string and add field context to errors."""

    try:
        return Iri(value, validate=True)
    except Exception as error:
        raise ValueError(f'Invalid IRI "{value}" in "{field_name}".') from error


def _dating(value: dict[str, Any] | None, unit_id: str) -> Dating | None:
    """Convert the compact YAML date mapping to an OLDAP Dating value."""

    if value is None:
        return None
    try:
        return Dating(
            dateStart=value["start"],
            dateEnd=value.get("end"),
            verbatimDate=value.get("verbatim"),
            inCalendar=value.get("calendar", "GREGORIAN"),
        )
    except Exception as error:
        raise ValueError(f'Invalid date on archive unit "{unit_id}": {error}') from error


def read_archive_yaml(
    inf: Path,
    project_shortname: Xsd_NCName | str,
    schema: Path | None = None,
) -> ArchiveDefinition:
    """Read, semantically validate, and flatten an archive YAML document.

    Nested units receive their parent from the YAML hierarchy. Only top-level
    units may name an already existing OLDAP parent through ``parent``.

    Args:
        inf: Archive YAML file.
        project_shortname: Target project prefix used to construct unit IRIs.
        schema: Optional alternative Yamale schema.

    Returns:
        A normalized definition in parent-before-child order.

    Raises:
        ValueError: If schema or semantic validation fails.
    """

    validate_archive_yaml(inf, schema=schema)
    with inf.open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    archive = document["archive"]
    language = archive["language"]
    shortname = (
        project_shortname
        if isinstance(project_shortname, Xsd_NCName)
        else Xsd_NCName(project_shortname, validate=True)
    )
    seen_ids: set[str] = set()
    units: list[ArchiveUnitSpec] = []

    def visit(raw: dict[str, Any], nested_parent: Iri | None, *, top_level: bool) -> None:
        unit_id = raw["id"]
        if unit_id in seen_ids:
            raise ValueError(f'Duplicate archive unit id "{unit_id}".')
        seen_ids.add(unit_id)

        if not top_level and "parent" in raw:
            raise ValueError(
                f'Nested archive unit "{unit_id}" must not define "parent"; '
                "its parent is given by the YAML hierarchy."
            )
        unit_iri = _project_iri(shortname, unit_id)
        parent_iri = nested_parent
        if top_level and raw.get("parent"):
            parent_iri = _as_iri(raw["parent"], f"{unit_id}.parent")

        level = raw["level"]
        if level not in ARCHIVE_LEVELS:
            raise ValueError(f'Invalid archive level "{level}" on unit "{unit_id}".')

        units.append(
            ArchiveUnitSpec(
                unit_id=unit_id,
                iri=unit_iri,
                level=level,
                title=_lang_string(raw["title"], language, f"{unit_id}.title"),
                parent_iri=parent_iri,
                parent_is_external=top_level and bool(raw.get("parent")),
                identifier=raw.get("identifier"),
                description=_optional_lang_string(
                    raw.get("description"), language, f"{unit_id}.description"
                ),
                dating=_dating(raw.get("date"), unit_id),
                extent=_optional_lang_string(raw.get("extent"), language, f"{unit_id}.extent"),
                creators=tuple(
                    _as_iri(value, f"{unit_id}.creators") for value in raw.get("creators", [])
                ),
                provenance=_optional_lang_string(
                    raw.get("provenance"), language, f"{unit_id}.provenance"
                ),
                access_conditions=_optional_lang_string(
                    raw.get("access_conditions"), language, f"{unit_id}.access_conditions"
                ),
                about=tuple(_as_iri(value, f"{unit_id}.about") for value in raw.get("about", [])),
                position=raw.get("position"),
            )
        )
        for child in raw.get("children", []):
            visit(child, unit_iri, top_level=False)

    for root in archive["units"]:
        visit(root, None, top_level=True)

    return ArchiveDefinition(
        version=archive["version"],
        language=language,
        units=tuple(units),
    )


def _read_existing(factory: ResourceInstanceFactory, iri: Iri) -> ResourceInstance | None:
    """Read a visible resource, returning ``None`` only when it does not exist."""

    try:
        return factory.read(iri)
    except OldapErrorNotFound:
        return None


def prepare_archive_import(
    factory: ResourceInstanceFactory,
    project_id: str,
    definition: ArchiveDefinition,
) -> ArchiveImportPlan:
    """Verify collisions and external parents without changing OLDAP data.

    Args:
        factory: Resource factory for the target project.
        project_id: User-facing target project identifier.
        definition: Normalized archive document.

    Returns:
        A plan that is safe to apply with create-only semantics.

    Raises:
        ValueError: If a target IRI already exists or an external parent is
            missing or is not a ``shared:ArchiveUnit``.
    """

    for unit in definition.units:
        if _read_existing(factory, unit.iri) is not None:
            raise ValueError(
                f'Archive unit "{unit.unit_id}" already exists as {unit.iri}; '
                "existing resources are never overwritten."
            )

    external_parents = sorted(
        {
            unit.parent_iri
            for unit in definition.units
            if unit.parent_is_external and unit.parent_iri is not None
        },
        key=str,
    )
    for parent_iri in external_parents:
        parent = _read_existing(factory, parent_iri)
        if parent is None:
            raise ValueError(f'External parent archive unit "{parent_iri}" does not exist.')
        if parent.__class__.name != Xsd_QName("shared:ArchiveUnit", validate=False):
            raise ValueError(f'External parent "{parent_iri}" is not a shared:ArchiveUnit.')

    return ArchiveImportPlan(
        project_id=project_id,
        units=definition.units,
        external_parent_iris=tuple(external_parents),
    )


def _unit_values(unit: ArchiveUnitSpec) -> dict[str, Any]:
    """Build ResourceInstance constructor values for one normalized unit."""

    values: dict[str, Any] = {
        "schema:name": unit.title,
        "shared:archiveLevel": Iri(f"shared:{unit.level}", validate=False),
    }
    optional_values = {
        "shared:parentArchiveUnit": unit.parent_iri,
        "schema:identifier": unit.identifier,
        "schema:description": unit.description,
        "dcterms:temporal": unit.dating,
        "schema:materialExtent": unit.extent,
        "dcterms:creator": set(unit.creators) if unit.creators else None,
        "dcterms:provenance": unit.provenance,
        "schema:conditionsOfAccess": unit.access_conditions,
        "schema:about": set(unit.about) if unit.about else None,
        "schema:position": unit.position,
    }
    values.update({key: value for key, value in optional_values.items() if value is not None})
    return values


def apply_archive_import(
    factory: ResourceInstanceFactory,
    plan: ArchiveImportPlan,
) -> tuple[Iri, ...]:
    """Create all planned units and best-effort roll back on an error.

    Parents are created before children. If creation fails, successfully created
    units are deleted in reverse order so that incoming child references do not
    block cleanup.

    Args:
        factory: Resource factory for the target project.
        plan: Previously validated import plan.

    Returns:
        IRIs of all newly created units in creation order.

    Raises:
        RuntimeError: If creation fails. The message also reports any unit that
            could not be removed during rollback.
    """

    ArchiveUnit = factory.createObjectInstance("shared:ArchiveUnit")
    created: list[Iri] = []
    try:
        for unit in plan.units:
            instance = ArchiveUnit(iri=unit.iri, **_unit_values(unit))
            instance.create()
            created.append(unit.iri)
    except Exception as error:
        rollback_failures: list[str] = []
        for iri in reversed(created):
            try:
                factory.read(iri).delete()
            except Exception as rollback_error:
                rollback_failures.append(f"{iri}: {rollback_error}")
        rollback_note = (
            f" Rollback failed for: {'; '.join(rollback_failures)}"
            if rollback_failures
            else " Created units were rolled back."
        )
        raise RuntimeError(f"Archive import failed: {error}.{rollback_note}") from error
    return tuple(created)


def load_archive(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    project_id: str,
    inf: Path,
    dry_run: bool = True,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> ArchiveImportPlan:
    """Validate, preflight, and optionally create an archive tree in OLDAP.

    The authenticated user's default OLDAP roles are applied by
    ``ResourceInstance`` to every newly created unit.

    Args:
        graphdb_base: GraphDB base URL.
        repo: GraphDB repository name.
        user: OLDAP administration user.
        password: OLDAP user password.
        project_id: Existing target project shortname or IRI.
        inf: Archive YAML input file.
        dry_run: Perform all checks but do not create resources.
        graphdb_user: Optional GraphDB HTTP Basic Auth user.
        graphdb_password: Optional GraphDB HTTP Basic Auth password.

    Returns:
        The validated import plan.
    """

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        context_name="DEFAULT",
    )
    project = Project.read(connection, project_id, ignore_cache=True)
    definition = read_archive_yaml(inf, project.projectShortName)
    factory = ResourceInstanceFactory(con=connection, project=project)
    plan = prepare_archive_import(factory, project_id, definition)
    if not dry_run:
        apply_archive_import(factory, plan)
    return plan
