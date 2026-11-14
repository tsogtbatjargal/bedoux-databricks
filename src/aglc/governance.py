"""Unity Catalog governance for Track 3, as generated SQL and DLT clauses.

Order matters because Silver and Gold tables are owned by their DLT pipelines:
1. function_statements(): mask and filter functions, created before the pipelines.
2. The pipelines declare masks and the row filter in their table definitions
   (players_schema(), retail_row_filter()). A pipeline-managed table can't be
   ALTERed to add them afterwards.
3. grant_statements(): applied after the pipelines create the tables.

Groups are checked with is_account_group_member(). Whether Free Edition supports
these groups, masks and filters is unverified; see
docs/adr/0004-uc-masks-not-separate-pii-table.md. Pipelines take
`aglc.enforce_governance` so they still run if it isn't supported.
"""

import re

GROUPS = {
    "engineer": "aglc_engineer",
    "compliance": "aglc_compliance",
    "liquor_analyst": "aglc_liquor_analyst",
    "cannabis_analyst": "aglc_cannabis_analyst",
}

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def ident(name):
    if not _IDENT.match(name or ""):
        raise ValueError(f"unsafe identifier: {name!r}")
    return name


def _gov(catalog):
    return f"{ident(catalog)}.aglc_governance"


def function_statements(catalog="workspace"):
    gov, g = _gov(catalog), GROUPS
    return [
        f"CREATE SCHEMA IF NOT EXISTS {gov}",
        f"""CREATE OR REPLACE FUNCTION {gov}.mask_email(email STRING) RETURNS STRING
RETURN CASE WHEN is_account_group_member('{g['compliance']}') THEN email
            ELSE concat('***@', substring_index(email, '@', -1)) END""",
        f"""CREATE OR REPLACE FUNCTION {gov}.mask_dob(dob STRING) RETURNS STRING
RETURN CASE WHEN is_account_group_member('{g['compliance']}') THEN dob
            ELSE concat(substring(dob, 1, 4), '-**-**') END""",
        f"""CREATE OR REPLACE FUNCTION {gov}.filter_domain(domain STRING) RETURNS BOOLEAN
RETURN is_account_group_member('{g['engineer']}')
    OR is_account_group_member('{g['compliance']}')
    OR (domain = 'liquor' AND is_account_group_member('{g['liquor_analyst']}'))
    OR (domain = 'cannabis' AND is_account_group_member('{g['cannabis_analyst']}'))""",
    ]


def players_schema(catalog="workspace", enforce=True):
    """DLT schema for gaming_players_clean, with column masks when enforced."""
    gov = _gov(catalog)
    email = f"email STRING MASK {gov}.mask_email" if enforce else "email STRING"
    dob = f"date_of_birth STRING MASK {gov}.mask_dob" if enforce else "date_of_birth STRING"
    return (f"player_id BIGINT, {email}, {dob}, region STRING, signup_date DATE, "
            "self_excluded BOOLEAN, _ingest_ts TIMESTAMP, _source_table STRING")


def retail_row_filter(catalog="workspace", enforce=True):
    """DLT row_filter clause for gold_retail_sales_daily, or None when not enforced."""
    return f"ROW FILTER {_gov(catalog)}.filter_domain ON (domain)" if enforce else None


def grant_statements(catalog="workspace"):
    c, g = ident(catalog), GROUPS
    gold, silver = f"{c}.aglc_gold", f"{c}.aglc_silver"
    return [
        *[f"GRANT USE CATALOG ON CATALOG {c} TO `{grp}`" for grp in g.values()],
        # Analysts read Gold only; the row filter narrows retail rows to their domain.
        *[f"GRANT USE SCHEMA, SELECT ON SCHEMA {gold} TO `{grp}`" for grp in g.values()],
        # Compliance also reads the PII table, where masks show it clear values.
        f"GRANT USE SCHEMA ON SCHEMA {silver} TO `{g['compliance']}`",
        f"GRANT SELECT ON TABLE {silver}.gaming_players_clean TO `{g['compliance']}`",
        # Engineers read every layer.
        *[f"GRANT USE SCHEMA, SELECT ON SCHEMA {c}.{s} TO `{g['engineer']}`"
          for s in ("aglc_bronze", "aglc_silver", "aglc_legacy")],
    ]


def as_bool(value):
    v = str(value).strip().lower()
    if v not in ("true", "false"):
        raise ValueError(f"expected 'true' or 'false', got {value!r}")
    return v == "true"
