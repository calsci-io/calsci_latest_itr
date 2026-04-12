from data_modules.db_instance import fun_db
from tinydb import Query


Function = Query()

SCOPE_DEFAULT = "default"
SCOPE_USER = "user"

DEFAULT_FUNCTIONS = (
    {
        "name": "circle_area",
        "variables": ["r"],
        "expression": "pi * r**2",
    },
)

_DEFAULT_FUNCTION_NAMES = set(row["name"] for row in DEFAULT_FUNCTIONS)


def _clean_name(name):
    return str(name or "").strip()


def _clean_expression(expression):
    return str(expression or "").strip()


def _clean_variables(variables):
    cleaned = []
    for value in variables or []:
        value = _clean_name(value)
        if value != "":
            cleaned.append(value)
    return cleaned


def _record_scope(row):
    scope = str((row or {}).get("scope") or "").strip().lower()
    if scope == SCOPE_USER:
        return SCOPE_USER
    if scope == SCOPE_DEFAULT:
        return SCOPE_DEFAULT
    if _clean_name((row or {}).get("name")) in _DEFAULT_FUNCTION_NAMES:
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
        "variables": _clean_variables(row.get("variables")),
        "expression": _clean_expression(row.get("expression")),
        "scope": _record_scope(row),
    }

    doc_id = getattr(row, "doc_id", None)
    if doc_id is not None:
        record["doc_id"] = doc_id

    expression_state = row.get("expression_state")
    if isinstance(expression_state, dict):
        record["expression_state"] = expression_state

    return record


def _rows_by_scope(scope=None):
    ensure_default_functions()

    rows_by_name = {}
    for row in fun_db.all():
        record = _normalize_record(row)
        if record is None:
            continue
        if scope is not None and record["scope"] != scope:
            continue
        rows_by_name[record["name"]] = record

    rows = list(rows_by_name.values())
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def ensure_default_functions():
    for seed in DEFAULT_FUNCTIONS:
        seed_name = _clean_name(seed.get("name"))
        if seed_name == "":
            continue

        existing_default = None
        for row in fun_db.search(Function.name == seed_name):
            record = _normalize_record(row)
            if record is None:
                continue
            if record["scope"] == SCOPE_DEFAULT:
                existing_default = record
                break

        payload = {
            "name": seed_name,
            "variables": _clean_variables(seed.get("variables")),
            "expression": _clean_expression(seed.get("expression")),
            "scope": SCOPE_DEFAULT,
        }

        if existing_default is None:
            fun_db.insert(payload)
            continue

        updates = {}
        for key, value in payload.items():
            if existing_default.get(key) != value:
                updates[key] = value

        if updates and existing_default.get("doc_id") is not None:
            fun_db.update(updates, doc_ids=[existing_default["doc_id"]])


def list_default_functions():
    return _rows_by_scope(SCOPE_DEFAULT)


def list_user_functions():
    return _rows_by_scope(SCOPE_USER)


def list_runtime_functions():
    runtime = {}

    for row in list_default_functions():
        runtime[row["name"]] = row

    for row in list_user_functions():
        runtime[row["name"]] = row

    rows = list(runtime.values())
    rows.sort(key=lambda row: row["name"].lower())
    return rows


def get_function(name, scope=None):
    name = _clean_name(name)
    if name == "":
        return None

    rows = list_runtime_functions() if scope is None else _rows_by_scope(scope)
    for row in rows:
        if row["name"] == name:
            return row
    return None


def user_function_exists(name, exclude_name=None):
    name = _clean_name(name)
    exclude_name = _clean_name(exclude_name)
    if name == "":
        return False

    for row in list_user_functions():
        row_name = row["name"]
        if row_name == exclude_name:
            continue
        if row_name == name:
            return True
    return False


def default_function_exists(name):
    return get_function(name, scope=SCOPE_DEFAULT) is not None


def upsert_user_function(name, variables, expression, expression_state=None, original_name=None):
    name = _clean_name(name)
    original_name = _clean_name(original_name) or name

    payload = {
        "name": name,
        "variables": _clean_variables(variables),
        "expression": _clean_expression(expression),
        "scope": SCOPE_USER,
    }

    if isinstance(expression_state, dict):
        payload["expression_state"] = expression_state

    target = get_function(original_name, scope=SCOPE_USER)
    if target is None and original_name != name:
        target = get_function(name, scope=SCOPE_USER)

    if target is not None and target.get("doc_id") is not None:
        fun_db.update(payload, doc_ids=[target["doc_id"]])
    else:
        fun_db.insert(payload)


def delete_user_function(name):
    row = get_function(name, scope=SCOPE_USER)
    if row is None or row.get("doc_id") is None:
        return False
    fun_db.remove(doc_ids=[row["doc_id"]])
    return True
