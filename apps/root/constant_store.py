from data_modules.db_instance import const_db
from tinydb import Query


Constant = Query()

SCOPE_DEFAULT = "default"
SCOPE_USER = "user"

DEFAULT_CONSTANTS = (
    {"name": "pi", "value": "3.141592653589793", "description": "Pi"},
    {"name": "e", "value": "2.718281828459045", "description": "Euler's Number"},
    {"name": "g", "value": "9.80665", "description": "Gravitational Acceleration"},
    {"name": "G", "value": "6.67430e-11", "description": "Gravitational Constant"},
    {"name": "c", "value": "2.99792458e8", "description": "Speed of Light"},
    {"name": "h", "value": "6.62607015e-34", "description": "Planck's Constant"},
    {"name": "k", "value": "1.380649e-23", "description": "Boltzmann Constant"},
    {"name": "R", "value": "8.314462618", "description": "Gas Constant"},
    {"name": "N_A", "value": "6.02214076e23", "description": "Avogadro's Number"},
    {"name": "eps_0", "value": "8.8541878128e-12", "description": "Permittivity of Free Space"},
    {"name": "mu_0", "value": "1.25663706212e-6", "description": "Permeability of Free Space"},
    {"name": "phi", "value": "1.618033988749895", "description": "Golden Ratio"},
)

_DEFAULT_CONSTANT_NAMES = set(row["name"] for row in DEFAULT_CONSTANTS)


def _clean_name(name):
    return str(name or "").strip()


def _clean_value(value):
    return str(value or "").strip()


def _clean_description(description):
    return str(description or "").strip()


def _record_scope(row):
    scope = str((row or {}).get("scope") or "").strip().lower()
    if scope == SCOPE_USER:
        return SCOPE_USER
    if scope == SCOPE_DEFAULT:
        return SCOPE_DEFAULT
    if _clean_name((row or {}).get("name")) in _DEFAULT_CONSTANT_NAMES:
        return SCOPE_DEFAULT
    return SCOPE_USER


def _normalize_record(row):
    if not isinstance(row, dict):
        return None

    name = _clean_name(row.get("name"))
    if name == "":
        return None

    record = {
        "name": name,
        "value": _clean_value(row.get("value")),
        "scope": _record_scope(row),
    }

    description = _clean_description(row.get("description"))
    if description != "":
        record["description"] = description

    expression_state = row.get("expression_state")
    if isinstance(expression_state, dict):
        record["expression_state"] = expression_state

    doc_id = getattr(row, "doc_id", None)
    if doc_id is not None:
        record["doc_id"] = doc_id

    return record


def _rows_by_scope(scope=None):
    ensure_default_constants()

    rows_by_name = {}
    for row in const_db.all():
        record = _normalize_record(row)
        if record is None:
            continue
        if scope is not None and record["scope"] != scope:
            continue
        rows_by_name[record["name"]] = record

    rows = list(rows_by_name.values())
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def ensure_default_constants():
    for seed in DEFAULT_CONSTANTS:
        seed_name = _clean_name(seed.get("name"))
        if seed_name == "":
            continue

        existing_default = None
        for row in const_db.search(Constant.name == seed_name):
            record = _normalize_record(row)
            if record is None:
                continue
            if record["scope"] == SCOPE_DEFAULT:
                existing_default = record
                break

        payload = {
            "name": seed_name,
            "value": _clean_value(seed.get("value")),
            "description": _clean_description(seed.get("description")),
            "scope": SCOPE_DEFAULT,
        }

        if existing_default is None:
            const_db.insert(payload)
            continue

        updates = {}
        for key, value in payload.items():
            if existing_default.get(key) != value:
                updates[key] = value

        if updates and existing_default.get("doc_id") is not None:
            const_db.update(updates, doc_ids=[existing_default["doc_id"]])


def list_default_constants():
    return _rows_by_scope(SCOPE_DEFAULT)


def list_user_constants():
    return _rows_by_scope(SCOPE_USER)


def list_runtime_constants():
    runtime = {}

    for row in list_default_constants():
        runtime[row["name"]] = row

    for row in list_user_constants():
        runtime[row["name"]] = row

    rows = list(runtime.values())
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def get_constant(name, scope=None):
    name = _clean_name(name)
    if name == "":
        return None

    rows = list_runtime_constants() if scope is None else _rows_by_scope(scope)
    for row in rows:
        if row["name"] == name:
            return row
    return None


def user_constant_exists(name, exclude_name=None):
    name = _clean_name(name)
    exclude_name = _clean_name(exclude_name)
    if name == "":
        return False

    for row in list_user_constants():
        row_name = row["name"]
        if row_name == exclude_name:
            continue
        if row_name == name:
            return True
    return False


def default_constant_exists(name):
    return get_constant(name, scope=SCOPE_DEFAULT) is not None


def upsert_user_constant(name, value, description="", original_name=None, expression_state=None):
    name = _clean_name(name)
    original_name = _clean_name(original_name) or name

    payload = {
        "name": name,
        "value": _clean_value(value),
        "scope": SCOPE_USER,
    }

    description = _clean_description(description)
    if description != "":
        payload["description"] = description

    if isinstance(expression_state, dict):
        payload["expression_state"] = expression_state

    current = get_constant(original_name, scope=SCOPE_USER)
    replacement = current
    if original_name != name:
        replacement = get_constant(name, scope=SCOPE_USER)

    if (
        current is not None
        and replacement is not None
        and current.get("doc_id") is not None
        and replacement.get("doc_id") is not None
        and current["doc_id"] != replacement["doc_id"]
    ):
        const_db.update(payload, doc_ids=[replacement["doc_id"]])
        const_db.remove(doc_ids=[current["doc_id"]])
        return

    target = current or replacement
    if target is not None and target.get("doc_id") is not None:
        const_db.update(payload, doc_ids=[target["doc_id"]])
        return

    const_db.insert(payload)


def delete_user_constant(name):
    row = get_constant(name, scope=SCOPE_USER)
    if row is None or row.get("doc_id") is None:
        return False
    const_db.remove(doc_ids=[row["doc_id"]])
    return True
