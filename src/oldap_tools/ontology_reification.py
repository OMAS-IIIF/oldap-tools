"""Shared, read-only YAML reification preflight for both ontology transports.

Merge explicit changes before checking references. This keeps incremental input
and forward references independent of document order without introducing a
second persistence model. Transactional in-use checks remain in oldaplib.
"""
from copy import deepcopy
from typing import Callable

from oldaplib.src.xsd.xsd_qname import Xsd_QName
from oldaplib.src.xsd.iri import Iri
from oldaplib.src.enums.xsd_datatypes import XsdDatatypes
from oldaplib.src.dtypes.languagein import LanguageIn
from oldaplib.src.helpers.convert2datatype import convert2datatype

FIELD_KEYS = {
    'iri', 'datatype', 'to_class', 'node_kind', 'name', 'description',
    'language_in', 'unique_lang', 'in', 'min_length', 'max_length', 'pattern',
    'min_exclusive', 'min_inclusive', 'max_exclusive', 'max_inclusive',
    'min_count', 'max_count', 'order', 'group', 'editor',
}


def index_fields(fields: list[dict]) -> dict[str, dict]:
    """Require unique explicit QName identities for inline fields."""
    result = {}
    for field in fields:
        iri = field.get('iri')
        if not iri or iri in result:
            raise ValueError('Missing or duplicate annotation/property IRI.')
        Xsd_QName(iri, validate=True)
        result[iri] = field
    return result


def validate_reification_syntax(ontology: dict) -> None:
    """Check local identities and the supported annotation-field profile.

    Partial update fields may omit their type; complete merged fields are
    checked during connected preflight before any mutation.
    """
    project = ontology['project']['shortname']
    for iri, shape in (ontology.get('reifier_shapes') or {}).items():
        name = Xsd_QName(iri, validate=True)
        if str(name.prefix) != project:
            raise ValueError(f'Reifier shape {iri} must belong to project {project}.')
        if shape is None:
            continue
        if set(shape) - {'properties'}:
            raise ValueError(f'Unsupported shape attributes on {iri}.')
        for field in index_fields(shape.get('properties', [])).values():
            unknown = set(field) - FIELD_KEYS
            if unknown:
                raise ValueError(f'Unsupported annotation field constraints: {sorted(unknown)}.')
            for key in ('min_count', 'max_count', 'min_length', 'max_length'):
                value = field.get(key)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError(f'{key} must be a non-negative integer.')
    for spec in (ontology.get('classes') or {}).values():
        index_fields(spec.get('properties', []))


def validate_field_values(field: dict) -> None:
    """Validate complete field values with OLDAP's datatype converters."""
    datatype = None
    if field.get('datatype'):
        try:
            datatype = XsdDatatypes(field['datatype'])
        except ValueError:
            try:
                datatype = XsdDatatypes[field['datatype']]
            except KeyError as error:
                raise ValueError(f'Unknown datatype {field["datatype"]}.') from error
    if field.get('to_class'):
        if not field['to_class'].startswith('list:'):
            Xsd_QName(field['to_class'], validate=True)
        literal_keys = {'language_in', 'min_length', 'max_length', 'pattern',
                        'min_exclusive', 'min_inclusive', 'max_exclusive', 'max_inclusive', 'unique_lang'}
        if any(field.get(key) is not None and field.get(key) is not False for key in literal_keys):
            raise ValueError('Object annotation fields cannot have literal restrictions.')
    if field.get('language_in') is not None:
        LanguageIn(field['language_in'])
        if datatype not in {XsdDatatypes.string, XsdDatatypes.langString}:
            raise ValueError('language_in requires a string datatype.')
    if field.get('node_kind') is not None:
        Iri(field['node_kind'], validate=True)
    for value in field.get('in', []):
        if datatype:
            convert2datatype(value, XsdDatatypes.string if datatype == XsdDatatypes.langString else datatype, validate=True)
        else:
            Iri(value, validate=True)


def merge_fields(current: list[dict], desired: list[dict], *, remove_unused: bool) -> list[dict]:
    """Merge explicit attributes; null removes, omission retains, lists replace."""
    old = index_fields(current)
    wanted = index_fields(desired)
    result = {} if remove_unused else deepcopy(old)
    for iri, field in wanted.items():
        merged = deepcopy(old.get(iri, {}))
        merged.update(field)
        result[iri] = {key: value for key, value in merged.items() if value is not None}
    return [result[iri] for iri in sorted(result)]


def prepare_reification(ontology: dict, current: dict, *, remove_unused: bool = False,
                        read_project: Callable[[str], dict] | None = None) -> tuple[dict, set[str]]:
    """Return merged local shapes and explicit deletions after reference checks.

    read_project supplies fresh foreign model YAML for shared definitions and
    inherited class policies. No callback may write. Omitted shapes are retained;
    a null shape requests deletion and requires remove_unused.
    """
    validate_reification_syntax(ontology)
    project = ontology['project']['shortname']
    shapes = deepcopy(current.get('reifier_shapes') or {})
    deleted = set()
    for iri, spec in (ontology.get('reifier_shapes') or {}).items():
        if spec is None:
            if not remove_unused:
                raise ValueError(f'Deleting {iri} requires --remove-unused.')
            shapes.pop(iri, None)
            deleted.add(iri)
        elif 'properties' in spec:
            shapes[iri] = {'properties': merge_fields(shapes.get(iri, {}).get('properties', []),
                                                      spec['properties'], remove_unused=remove_unused)}
        else:
            shapes.setdefault(iri, {'properties': []})
    for iri, shape in shapes.items():
        validate_reification_syntax({'project': {'shortname': project}, 'reifier_shapes': {iri: shape}})
        for field in shape['properties']:
            if bool(field.get('datatype')) == bool(field.get('to_class')):
                raise ValueError(f'Annotation field {field["iri"]} requires exactly one of datatype or to_class.')
            validate_field_values(field)
            if field.get('min_count', 0) > field.get('max_count', float('inf')):
                raise ValueError(f'Invalid cardinality on {field["iri"]}.')
    classes = deepcopy(current.get('classes') or {})
    for iri, spec in (ontology.get('classes') or {}).items():
        old = classes.get(iri, {})
        merged = old | deepcopy(spec)
        if 'properties' in spec:
            merged['properties'] = merge_fields(old.get('properties', []), spec['properties'], remove_unused=remove_unused)
        classes[iri] = merged
    if set(shapes) & {iri + 'Shape' for iri in classes}:
        raise ValueError('Reifier shape identity collides with a resource class shape.')
    kinds = {}
    for spec in [*classes.values(), *shapes.values()]:
        for prop in spec.get('properties', []):
            if prop.get('datatype') or prop.get('to_class'):
                kinds.setdefault(prop['iri'], set()).add(bool(prop.get('datatype')))
    old_standalone = current.get('standalone_properties') or {}
    new_standalone = ontology.get('standalone_properties') or {}
    for iri in old_standalone.keys() | new_standalone.keys():
        prop = old_standalone.get(iri, {}) | new_standalone.get(iri, {})
        if prop.get('datatype') or prop.get('to_class'):
            kinds.setdefault(iri, set()).add(bool(prop.get('datatype')))
    for shape in shapes.values():
        for prop in shape['properties']:
            if len(kinds[prop['iri']]) > 1:
                raise ValueError(f'Conflicting OWL property kinds for {prop["iri"]}.')
    foreign = {}
    def remote(prefix):
        if prefix not in foreign:
            if read_project is None:
                raise ValueError(f'Cannot resolve reification model in {prefix}.')
            foreign[prefix] = read_project(prefix)
        return foreign[prefix]
    def refs_for(prop, inherited=()):
        refs = set(prop.get('reifier_shapes') or ()) | set(inherited)
        if prop.get('reification_required') is not None and not refs:
            raise ValueError(f'{prop["iri"]}: reification_required requires reifier_shapes.')
        if refs and (prop.get('inverse_path') or prop.get('applies_to_property')):
            raise ValueError('Reifier shapes require a forward property path.')
        for ref in refs:
            prefix = str(Xsd_QName(ref, validate=True).prefix)
            if prefix not in {project, 'shared'}:
                raise ValueError(f'Reifier shape {ref} must be local or shared.')
            definitions = shapes if prefix == project else remote(prefix).get('reifier_shapes', {})
            if ref not in definitions:
                raise ValueError(f'Unknown or deleted reifier shape {ref}.')
        return refs
    active, done = set(), {}
    def visit(iri):
        if iri in done:
            return done[iri]
        if iri in active:
            raise ValueError('Cyclic superclass definitions.')
        active.add(iri)
        spec = classes.get(iri)
        if spec is None and iri != 'oldap:Thing':
            prefix = str(Xsd_QName(iri, validate=True).prefix)
            if prefix in {'shared', 'oldap'} and prefix != project:
                spec = remote(prefix).get('classes', {}).get(iri)
        policies = {}
        for parent in (spec or {}).get('superclass', []):
            for predicate, refs in visit(parent).items():
                policies.setdefault(predicate, set()).update(refs)
        for prop in (spec or {}).get('properties', []):
            policies[prop['iri']] = refs_for(prop, policies.get(prop['iri'], ()))
        active.remove(iri)
        done[iri] = policies
        return policies
    # Plain legacy imports need no additional remote reads.
    relevant = bool(shapes or deleted or ontology.get('reifier_shapes')) or any(
        'reifier_shapes' in prop or 'reification_required' in prop
        for spec in classes.values() for prop in spec.get('properties', []))
    if relevant:
        for iri in classes:
            visit(iri)
    standalone = deepcopy(current.get('standalone_properties') or {})
    for iri, spec in (ontology.get('standalone_properties') or {}).items():
        standalone[iri] = {key: value for key, value in (standalone.get(iri, {}) | spec).items() if value is not None}
    for iri, prop in standalone.items():
        refs_for({'iri': iri} | prop)
    return shapes, deleted
