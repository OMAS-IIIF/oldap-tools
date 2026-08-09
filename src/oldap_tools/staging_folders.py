"""Provision application-managed folders for existing OLDAP StagingAreas."""

from dataclasses import dataclass
from typing import Any

from oldaplib.src.enums.datapermissions import DataPermission
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.connection import create_connection


TOP_FOLDER_NAME = "top"
MOBILE_FOLDER_NAME = "Mobile"
STAGING_AREA_CLASS = "fasnacht:StagingArea"
STAGING_FOLDER_CLASS = "shared:StagingFolder"


@dataclass(frozen=True)
class StagingAreaRecord:
    """Minimal StagingArea data needed by the migration."""

    iri: str
    default_role_iri: str


@dataclass(frozen=True)
class StagingFolderRecord:
    """Minimal StagingFolder data needed to validate the system hierarchy."""

    iri: str
    staging_area_iri: str
    name: str
    parent_iri: str


@dataclass(frozen=True)
class MobileFolderPlan:
    """Validated action for one StagingArea."""

    area: StagingAreaRecord
    top_folder_iri: str
    existing_mobile_folder_iri: str | None

    @property
    def needs_creation(self) -> bool:
        """Return whether the Mobile system folder is missing."""

        return self.existing_mobile_folder_iri is None


def plan_mobile_folder(
    area: StagingAreaRecord,
    folders: list[StagingFolderRecord],
) -> MobileFolderPlan:
    """Validate one StagingArea and determine whether Mobile must be created.

    Args:
        area: StagingArea being migrated.
        folders: All visible StagingFolder records for the project.

    Returns:
        A validated, idempotent migration plan.

    Raises:
        ValueError: If the StagingArea has no unique top folder, lacks its
            default role, or contains an ambiguous Mobile folder.
    """

    if not area.default_role_iri:
        raise ValueError(f"StagingArea {area.iri} has no shared:stagingDefaultRole.")

    area_folders = [folder for folder in folders if folder.staging_area_iri == area.iri]
    top_folders = [
        folder
        for folder in area_folders
        if folder.name == TOP_FOLDER_NAME and not folder.parent_iri
    ]
    if len(top_folders) != 1:
        raise ValueError(
            f"StagingArea {area.iri} must contain exactly one root folder named "
            f'"{TOP_FOLDER_NAME}"; found {len(top_folders)}.'
        )

    top_folder = top_folders[0]
    named_mobile_folders = [
        folder
        for folder in area_folders
        if folder.name.casefold() == MOBILE_FOLDER_NAME.casefold()
    ]
    misplaced_mobile_folders = [
        folder
        for folder in named_mobile_folders
        if folder.name != MOBILE_FOLDER_NAME or folder.parent_iri != top_folder.iri
    ]
    if misplaced_mobile_folders:
        locations = ", ".join(folder.iri for folder in misplaced_mobile_folders)
        raise ValueError(
            f"StagingArea {area.iri} has a noncanonical Mobile folder name or position: {locations}."
        )

    if len(named_mobile_folders) > 1:
        raise ValueError(
            f"StagingArea {area.iri} contains multiple Mobile system folders."
        )

    return MobileFolderPlan(
        area=area,
        top_folder_iri=top_folder.iri,
        existing_mobile_folder_iri=(named_mobile_folders[0].iri if named_mobile_folders else None),
    )


def _record_values(record: dict[Any, Any], property_iri: str) -> list[Any]:
    if property_iri == "iri":
        value = record.get("iri", [])
    else:
        value = record.get(Xsd_QName(property_iri), record.get(property_iri, []))
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def _first_string(record: dict[Any, Any], property_iri: str) -> str:
    values = _record_values(record, property_iri)
    return str(values[0]).strip() if values else ""


def _load_staging_areas(connection: Any, project_id: str) -> list[StagingAreaRecord]:
    records = ResourceInstance.all_resources(
        con=connection,
        project=project_id,
        resClass=Xsd_QName(STAGING_AREA_CLASS),
        includeProperties=[Xsd_QName("shared:stagingDefaultRole")],
        limit=5000,
    )
    return [
        StagingAreaRecord(
            iri=_first_string(record, "iri"),
            default_role_iri=_first_string(record, "shared:stagingDefaultRole"),
        )
        for record in records
    ]


def _load_staging_folders(connection: Any, project_id: str) -> list[StagingFolderRecord]:
    records = ResourceInstance.all_resources(
        con=connection,
        project=project_id,
        resClass=Xsd_QName(STAGING_FOLDER_CLASS),
        includeProperties=[
            Xsd_QName("schema:name"),
            Xsd_QName("shared:inStagingArea"),
            Xsd_QName("shared:inStagingFolder"),
        ],
        limit=5000,
    )
    return [
        StagingFolderRecord(
            iri=_first_string(record, "iri"),
            staging_area_iri=_first_string(record, "shared:inStagingArea"),
            name=_first_string(record, "schema:name"),
            parent_iri=_first_string(record, "shared:inStagingFolder"),
        )
        for record in records
    ]


def ensure_mobile_folders(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    project_id: str = "fasnacht",
    staging_area_iris: list[str] | None = None,
    all_areas: bool = False,
    dry_run: bool = True,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> list[MobileFolderPlan]:
    """Ensure the Mobile system folder for selected existing StagingAreas.

    The operation is idempotent. Dry-run is enabled by default and performs all
    hierarchy validation without writing to GraphDB.

    Args:
        graphdb_base: GraphDB base URL.
        repo: GraphDB repository name.
        user: OLDAP administration user.
        password: OLDAP user password.
        project_id: Project containing the StagingArea data graph.
        staging_area_iris: Explicit StagingArea IRIs to process.
        all_areas: Process every StagingArea in the project.
        dry_run: Validate and report without creating folders.
        graphdb_user: Optional GraphDB HTTP Basic Auth user.
        graphdb_password: Optional GraphDB HTTP Basic Auth password.

    Returns:
        The validated plan for every selected StagingArea.

    Raises:
        ValueError: If target selection or a folder hierarchy is invalid.
    """

    requested_iris = {iri.strip() for iri in staging_area_iris or [] if iri.strip()}
    if all_areas == bool(requested_iris):
        raise ValueError("Choose either --all or at least one --staging-area.")

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
    )
    areas = _load_staging_areas(connection, project_id)
    if requested_iris:
        known_iris = {area.iri for area in areas}
        missing_iris = sorted(requested_iris - known_iris)
        if missing_iris:
            raise ValueError(f"Unknown StagingArea(s): {', '.join(missing_iris)}")
        areas = [area for area in areas if area.iri in requested_iris]

    folders = _load_staging_folders(connection, project_id)
    plans = [plan_mobile_folder(area, folders) for area in areas]
    if dry_run:
        return plans

    factory = ResourceInstanceFactory(con=connection, project=project_id)
    StagingFolder = factory.createObjectInstance(STAGING_FOLDER_CLASS)
    for plan in plans:
        if not plan.needs_creation:
            continue
        folder = StagingFolder(**{
            "schema:name": MOBILE_FOLDER_NAME,
            "shared:inStagingArea": Iri(plan.area.iri, validate=False),
            "shared:inStagingFolder": Iri(plan.top_folder_iri, validate=False),
            "oldap:attachedToRole": {
                Xsd_QName(plan.area.default_role_iri): DataPermission.DATA_VIEW,
            },
        })
        folder.create()

    return plans
