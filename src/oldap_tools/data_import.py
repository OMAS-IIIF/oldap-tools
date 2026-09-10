"""Preflight and create-only execution for OLDAP instance-data documents.

The preflight deliberately delegates ontology constraints to dynamic
``oldaplib`` resource classes. It resolves the live project model, builds each
proposed resource in memory, and verifies referenced resources and roles. The
preflight never invokes a write method; apply is deliberately limited to one
RDF resource and may then invoke the separately recoverable media workflow.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from oldaplib.src.enums.adminpermissions import AdminPermission
from oldaplib.src.helpers.context import Context
from oldaplib.src.helpers.langstring import LangString
from oldaplib.src.helpers.oldaperror import OldapErrorNotFound
from oldaplib.src.objectfactory import ResourceInstance, ResourceInstanceFactory
from oldaplib.src.project import Project
from oldaplib.src.role import Role
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.xsd.xsd_ncname import Xsd_NCName
from oldaplib.src.xsd.xsd_qname import Xsd_QName

from oldap_tools.connection import create_connection
from oldap_tools.data_yaml import (
    DataDocument,
    DataResource,
    DataValue,
    require_prepared_document,
)
from oldap_tools.media_ingest import (
    MediaAttachResult,
    MediaIngestError,
    attach_media_copy,
    authenticate_media_user,
    prepare_document_media,
)


@dataclass(frozen=True)
class DataResourcePreflight:
    """One new or resumably verified resource that passed live preflight."""

    iri: str
    resource_class: str
    property_count: int
    reference_count: int
    media_action: str | None = None
    disposition: str = "create"
    reference_iris: tuple[str, ...] = ()


@dataclass(frozen=True)
class DataImportPreflight:
    """Validated create-only or resumable plan for one data document."""

    project: str
    resources: tuple[DataResourcePreflight, ...]


@dataclass(frozen=True)
class DataImportExecution:
    """Result of a dry-run or one-resource create-only execution."""

    plan: DataImportPreflight
    created_iris: tuple[str, ...] = ()
    media_results: tuple[MediaAttachResult, ...] = ()


class DataImportPreflightError(ValueError):
    """Raised when local data does not conform to the live OLDAP project."""


RoleReader = Callable[[Xsd_QName], Any]
_ROLE_CLASS = Xsd_QName("oldap:Role", validate=False)


def _qname(identifier: str, context: Context, path: str) -> Xsd_QName:
    """Resolve a QName or absolute IRI through the active OLDAP context."""

    if identifier.startswith(("http://", "https://", "urn:")):
        resolved = context.iri2qname(identifier)
        if resolved is None:
            raise DataImportPreflightError(
                f"{path} uses an absolute IRI whose namespace is unknown: {identifier}."
            )
        return resolved
    try:
        return Xsd_QName(identifier, validate=True)
    except Exception as error:
        raise DataImportPreflightError(f"{path} is not a usable QName: {identifier}.") from error


def _resource_iri(resource: DataResource, project: Xsd_NCName) -> Iri:
    """Resolve a document resource identity to its target OLDAP IRI."""

    try:
        if ":" not in resource.iri:
            return Iri(Xsd_QName(project, resource.iri, validate=True))
        return Iri(resource.iri, validate=True)
    except Exception as error:
        raise DataImportPreflightError(
            f"Resource {resource.iri!r} cannot be resolved in project {project}."
        ) from error


def _class_is_or_extends(instance_class: type, expected: Xsd_QName) -> bool:
    """Return whether a dynamic OLDAP class equals or extends ``expected``."""

    if instance_class.name == expected:
        return True

    def contains(superclasses: dict[Any, Any] | None) -> bool:
        for iri, superclass in (superclasses or {}).items():
            if iri == expected:
                return True
            if superclass is not None and contains(getattr(superclass, "superclass", {})):
                return True
        return False

    return contains(getattr(instance_class, "superclass", {}))


def _read_visible(
    factory: ResourceInstanceFactory,
    iri: Iri,
) -> ResourceInstance | None:
    """Read a visible resource and treat only OLDAP not-found as absence."""

    try:
        return factory.read(iri)
    except OldapErrorNotFound:
        return None


def _is_dating_property(property_definition: Any) -> bool:
    """Return whether a property targets OLDAP's structured Dating value."""

    return (
        getattr(property_definition, "datatype", None) is None
        and str(getattr(property_definition, "toClass", "")) == "oldap:Dating"
    )


def _is_controlled_iri_value(value: Iri, property_definition: Any) -> bool:
    """Return whether an object-property value is fixed by the shape's ``sh:in``.

    Named individuals such as ``shared:ArchiveGroup`` live in ontology graphs,
    not in the importing project's data graph. Dynamic instance construction
    already validates the property's allowed-value set. Such fixed vocabulary
    values therefore must not be treated as ordinary linked project resources
    requiring a permission-aware instance read.

    Args:
        value: Converted IRI reference from the data document.
        property_definition: Resolved OLDAP property definition.

    Returns:
        ``True`` when the IRI occurs in the property's configured ``sh:in`` set.
    """

    allowed_values = getattr(property_definition, "inSet", None)
    if not allowed_values:
        return False
    return str(value) in {str(allowed) for allowed in allowed_values}


def _literal_value(
    value: DataValue,
    property_definition: Any,
    context: Context,
    path: str,
) -> Any:
    """Validate and convert one literal for dynamic-instance construction."""

    expected_datatype = getattr(property_definition, "datatype", None)
    if expected_datatype is None and not _is_dating_property(property_definition):
        raise DataImportPreflightError(
            f"{path} must be an IRI reference for this ontology property."
        )
    if value.datatype is not None:
        declared_datatype = _qname(value.datatype, context, f"{path}.datatype")
        if expected_datatype is None or str(declared_datatype) != str(expected_datatype):
            raise DataImportPreflightError(
                f"{path}.datatype is {declared_datatype}, but the ontology expects "
                f"{expected_datatype or 'an IRI reference'}."
            )
    if value.language is not None and str(expected_datatype) != "rdf:langString":
        raise DataImportPreflightError(
            f"{path}.language is allowed only for an rdf:langString property."
        )
    if str(expected_datatype) == "rdf:langString" and value.language is None:
        raise DataImportPreflightError(
            f"{path} requires a language because the ontology datatype is rdf:langString."
        )
    return value.value


def _property_value(
    value: DataValue,
    property_definition: Any,
    context: Context,
    path: str,
) -> Any:
    """Resolve one explicit document value against an ontology property."""

    if value.iri is not None:
        if getattr(property_definition, "datatype", None) is not None or _is_dating_property(
            property_definition
        ):
            raise DataImportPreflightError(
                f"{path} must be a literal for this ontology property."
            )
        try:
            return Iri(value.iri, validate=True)
        except Exception as error:
            raise DataImportPreflightError(f"{path}.iri is invalid: {value.iri}.") from error
    return _literal_value(value, property_definition, context, path)


def _instance_values(
    resource: DataResource,
    resource_type: type,
    context: Context,
) -> tuple[dict[str, Any], list[tuple[Iri, Xsd_QName]]]:
    """Build constructor values and typed links from a validated resource."""

    properties = resource_type.resolved_properties()
    constructor_values: dict[str, Any] = {}
    references: list[tuple[Iri, Xsd_QName]] = []
    for property_identifier, values in resource.properties.items():
        property_iri = _qname(
            property_identifier,
            context,
            f"Resource {resource.iri} property {property_identifier}",
        )
        property_definition = properties.get(property_iri)
        if property_definition is None:
            raise DataImportPreflightError(
                f"Resource {resource.iri} uses property {property_iri}, which is not "
                f"defined for {resource.resource_class}."
            )
        converted = [
            _property_value(
                value,
                property_definition,
                context,
                f"Resource {resource.iri} property {property_iri}[{index}]",
            )
            for index, value in enumerate(values)
        ]

        if str(getattr(property_definition, "datatype", None)) == "rdf:langString":
            languages = [value.language for value in values]
            if len(languages) != len(set(languages)):
                raise DataImportPreflightError(
                    f"Resource {resource.iri} property {property_iri} repeats a language."
                )
            constructor_values[str(property_iri)] = LangString(
                {
                    value.language: converted_value
                    for value, converted_value in zip(values, converted, strict=True)
                }
            )
        else:
            constructor_values[str(property_iri)] = (
                converted[0] if len(converted) == 1 else converted
            )

        expected_class = getattr(property_definition, "toClass", None)
        if expected_class is not None and not _is_dating_property(property_definition):
            expected_class_iri = _qname(
                str(expected_class),
                context,
                f"Resource {resource.iri} property {property_iri} target class",
            )
            references.extend(
                (value, expected_class_iri)
                for value in converted
                if not _is_controlled_iri_value(value, property_definition)
            )

    # Omitting ``permissions`` delegates role assignment to OLDAPLIB's
    # authenticated-user defaults. Passing an empty mapping would suppress
    # those defaults and serialize an object-less ``oldap:attachedToRole``
    # predicate during create.
    if resource.permissions:
        constructor_values["attachedToRole"] = dict(resource.permissions)
    return constructor_values, references


def _verify_existing_resource(
    resource: DataResource,
    existing: ResourceInstance,
    resource_type: type,
    values: dict[str, Any],
    context: Context,
) -> None:
    """Require an existing resource to match all YAML-declared state.

    Additional server-managed properties are allowed. For a copied media item,
    ``shared:protocol`` may have advanced from the YAML staging value ``custom``
    to the verified delivery value ``iiif``.
    """

    if getattr(existing.__class__, "name", None) != getattr(resource_type, "name", None):
        raise DataImportPreflightError(
            f"Resource {resource.iri} already exists with class "
            f"{getattr(existing.__class__, 'name', existing.__class__.__name__)}, "
            f"not {resource.resource_class}."
        )
    expected = resource_type(iri=existing.iri, **values)
    mismatches: list[str] = []
    for property_identifier in resource.properties:
        property_iri = _qname(
            property_identifier,
            context,
            f"Resource {resource.iri} property {property_identifier}",
        )
        expected_value = expected.get(property_iri)
        actual_value = existing.get(property_iri)
        if (
            property_identifier == "shared:protocol"
            and resource.media is not None
            and resource.media.handling == "copy"
            and "custom" in {str(value) for value in expected_value or ()}
            and "iiif" in {str(value) for value in actual_value or ()}
        ):
            continue
        if actual_value != expected_value:
            mismatches.append(
                f"{property_identifier} (YAML {expected_value!s}; OLDAP {actual_value!s})"
            )

    # Permissions are verified only when the document declares them. When the
    # field is omitted, role assignment belongs to OLDAPLIB's user defaults and
    # is intentionally outside the YAML state compared on resumable reruns.
    if resource.permissions:
        expected_roles = expected.get(
            Xsd_QName("oldap:attachedToRole", validate=False)
        )
        actual_roles = existing.get(Xsd_QName("oldap:attachedToRole", validate=False))
        if actual_roles != expected_roles:
            mismatches.append(
                f"permissions (YAML {expected_roles!s}; OLDAP {actual_roles!s})"
            )
    if mismatches:
        raise DataImportPreflightError(
            f"Resource {resource.iri} already exists but does not match the YAML: "
            + "; ".join(mismatches)
        )


def prepare_data_import(
    connection: Any,
    factory: ResourceInstanceFactory,
    document: DataDocument,
    *,
    role_reader: RoleReader | None = None,
    allow_existing: bool = False,
) -> DataImportPreflight:
    """Validate a data document against a live model without writing.

    Args:
        connection: Authenticated OLDAP connection used only for reads.
        factory: Factory already bound to the target project and model.
        document: Locally validated version-1 data document.
        role_reader: Optional test seam for resolving role QNames.

    Returns:
        A create-only preflight plan containing every proposed resource.

    Raises:
        DataImportPreflightError: If the live model, data, links, roles, or
            create-only collision checks fail.
    """

    require_prepared_document(document)
    project = Xsd_NCName(document.project, validate=True)
    context = Context(name=connection.context_name)
    resolve_role = role_reader or (
        lambda role_iri: Role.read(con=connection, qname=role_iri, ignore_cache=True)
    )

    resource_types: dict[str, type] = {}
    resource_iris: dict[str, Iri] = {}
    for resource in document.resources:
        class_iri = _qname(
            resource.resource_class,
            context,
            f"Resource {resource.iri} class",
        )
        try:
            resource_types[resource.iri] = factory.createObjectInstance(class_iri)
        except Exception as error:
            raise DataImportPreflightError(
                f"Resource {resource.iri} class {class_iri} is not available in "
                f"project {project}: {error}"
            ) from error
        resource_iris[resource.iri] = _resource_iri(resource, project)

    planned_by_iri = {
        str(resource_iris[resource.iri]): resource for resource in document.resources
    }
    visible_cache: dict[str, ResourceInstance | None] = {}
    validated_roles: set[Xsd_QName] = set()
    plans: list[DataResourcePreflight] = []
    permission_checked = False

    for resource in document.resources:
        iri = resource_iris[resource.iri]
        existing = _read_visible(factory, iri)
        visible_cache[str(iri)] = existing
        if existing is not None and not allow_existing:
            raise DataImportPreflightError(
                f"Resource {iri} already exists; version 1 preflight is create-only."
            )

        for role_identifier in resource.permissions:
            role_iri = _qname(
                role_identifier,
                context,
                f"Resource {resource.iri} permission role",
            )
            if role_iri in validated_roles:
                continue
            try:
                resolve_role(role_iri)
            except Exception as error:
                raise DataImportPreflightError(
                    f"Resource {resource.iri} references unknown role {role_iri}: {error}"
                ) from error
            validated_roles.add(role_iri)

        resource_type = resource_types[resource.iri]
        values, references = _instance_values(resource, resource_type, context)
        try:
            instance = resource_type(iri=iri, **values)
        except Exception as error:
            raise DataImportPreflightError(
                f"Resource {resource.iri} violates {resource.resource_class}: {error}"
            ) from error
        if existing is not None:
            _verify_existing_resource(
                resource,
                existing,
                resource_type,
                values,
                context,
            )
        elif not permission_checked:
            try:
                allowed, message = instance.check_for_permissions(AdminPermission.ADMIN_CREATE)
            except Exception as error:
                raise DataImportPreflightError(
                    f"Could not verify ADMIN_CREATE for project {project}: {error}"
                ) from error
            if not allowed:
                raise DataImportPreflightError(message)
            permission_checked = True

        for reference_iri, expected_class in references:
            # Roles are administrative resources in ``oldap:admin``, not
            # permission-filtered instances in the project's data graph. Use
            # the same authoritative resolver as YAML permission keys for
            # object properties such as ``shared:stagingDefaultRole``.
            if expected_class == _ROLE_CLASS:
                role_iri = _qname(
                    str(reference_iri),
                    context,
                    f"Resource {resource.iri} linked role",
                )
                if role_iri not in validated_roles:
                    try:
                        resolve_role(role_iri)
                    except Exception as error:
                        raise DataImportPreflightError(
                            f"Resource {resource.iri} links role {role_iri}, which does not "
                            "exist or is not visible to the authenticated user."
                        ) from error
                    validated_roles.add(role_iri)
                continue
            planned_resource = planned_by_iri.get(str(reference_iri))
            if planned_resource is not None:
                target_type = resource_types[planned_resource.iri]
                if not _class_is_or_extends(target_type, expected_class):
                    raise DataImportPreflightError(
                        f"Resource {resource.iri} links {reference_iri} through a property "
                        f"requiring {expected_class}, but the planned class is "
                        f"{planned_resource.resource_class}."
                    )
                continue
            if str(reference_iri) not in visible_cache:
                visible_cache[str(reference_iri)] = _read_visible(factory, reference_iri)
            target = visible_cache[str(reference_iri)]
            if target is None:
                raise DataImportPreflightError(
                    f"Resource {resource.iri} links {reference_iri}, which does not exist "
                    "or is not visible to the authenticated user."
                )
            if not _class_is_or_extends(target.__class__, expected_class):
                raise DataImportPreflightError(
                    f"Resource {resource.iri} links {reference_iri}, but the ontology "
                    f"requires an instance of {expected_class}."
                )

        plans.append(
            DataResourcePreflight(
                iri=str(iri),
                resource_class=resource.resource_class,
                property_count=len(resource.properties),
                reference_count=len(references),
                media_action=(
                    f"{resource.media.handling} {resource.media.ingest_profile}"
                    if resource.media is not None and resource.media.ingest_profile
                    else resource.media.handling if resource.media is not None else None
                ),
                disposition="existing_verified" if existing is not None else "create",
                reference_iris=tuple(str(reference) for reference, _class in references),
            )
        )

    return DataImportPreflight(project=str(project), resources=tuple(plans))


def create_data_resource(
    connection: Any,
    factory: ResourceInstanceFactory,
    document: DataDocument,
    resource: DataResource,
) -> str:
    """Create one already-preflighted resource and return its resolved IRI."""

    project = Xsd_NCName(document.project, validate=True)
    context = Context(name=connection.context_name)
    class_iri = _qname(
        resource.resource_class,
        context,
        f"Resource {resource.iri} class",
    )
    resource_type = factory.createObjectInstance(class_iri)
    iri = _resource_iri(resource, project)
    values, _references = _instance_values(resource, resource_type, context)
    instance = resource_type(iri=iri, **values)
    instance.create()
    return str(iri)


def apply_data_import(
    connection: Any,
    factory: ResourceInstanceFactory,
    document: DataDocument,
    *,
    role_reader: RoleReader | None = None,
) -> DataImportExecution:
    """Re-preflight and atomically create exactly one resource.

    Version 1 intentionally refuses multi-resource apply. ``ResourceInstance``
    commits each create separately, and a generic compensating delete cannot
    yet guarantee removal of every structured-value helper node. Restricting an
    apply execution to one resource preserves OLDAP's transaction boundary.

    Args:
        connection: Authenticated OLDAP connection used for reads and one create.
        factory: Factory bound to the target project and current model.
        document: Locally validated version-1 data document.
        role_reader: Optional test seam for resolving role QNames.

    Returns:
        The repeated preflight and the one newly created IRI.

    Raises:
        DataImportPreflightError: If the document contains more than one
            resource or the repeated live preflight fails.
        OldapError: If OLDAP rejects or cannot commit the atomic create.
    """

    if len(document.resources) != 1:
        raise DataImportPreflightError(
            "Version 1 --apply requires exactly one resource per document; "
            f"received {len(document.resources)}."
        )

    # Recheck immediately before constructing the object that will be written.
    plan = prepare_data_import(
        connection,
        factory,
        document,
        role_reader=role_reader,
    )
    iri = create_data_resource(connection, factory, document, document.resources[0])
    return DataImportExecution(plan=plan, created_iris=(iri,))


def preflight_data_import(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    document: DataDocument,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> DataImportPreflight:
    """Connect to OLDAP and prepare a read-only data import plan."""

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        context_name="DEFAULT",
    )
    project = Project.read(connection, document.project, ignore_cache=True)
    factory = ResourceInstanceFactory(con=connection, project=project)
    return prepare_data_import(connection, factory, document)


def run_data_import(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    document: DataDocument,
    apply: bool = False,
    api_base: str = "http://localhost:8000",
    media_base: str = "http://localhost:8088",
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
) -> DataImportExecution:
    """Run a dry preflight or one-resource create plus declared media ingest.

    RDF creation and media attachment use separate service transactions. If
    attachment fails after RDF creation, the resource remains deliberately
    recoverable through ``data media-attach --apply``.
    """

    media_plans = prepare_document_media(document)

    connection = create_connection(
        graphdb_base=graphdb_base,
        repo=repo,
        user=user,
        password=password,
        graphdb_user=graphdb_user,
        graphdb_password=graphdb_password,
        context_name="DEFAULT",
    )
    project = Project.read(connection, document.project, ignore_cache=True)
    factory = ResourceInstanceFactory(con=connection, project=project)
    initial_plan = prepare_data_import(connection, factory, document)
    if apply:
        execution = apply_data_import(connection, factory, document)
        if not media_plans:
            return execution
        try:
            token = authenticate_media_user(api_base, user, password)
            media_results = tuple(
                attach_media_copy(
                    media_plan,
                    api_base=api_base,
                    media_base=media_base,
                    token=token,
                )
                for media_plan in media_plans
            )
        except MediaIngestError as error:
            created = ", ".join(execution.created_iris)
            raise MediaIngestError(
                f"RDF resource {created} was created, but media attachment failed: "
                f"{error} Retry safely with data media-attach --apply."
            ) from error
        return DataImportExecution(
            plan=execution.plan,
            created_iris=execution.created_iris,
            media_results=media_results,
        )
    return DataImportExecution(plan=initial_plan)
