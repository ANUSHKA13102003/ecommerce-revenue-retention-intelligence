"""
SQL Safety & Schema Allow-List Validator
=========================================
Enforces strict read-only query execution for the AI SQL Analyst Agent:
1. Only single-statement `SELECT` or `WITH ... SELECT` queries are allowed.
2. Any DDL/DML/administrative keyword (`DROP`, `DELETE`, `UPDATE`, `INSERT`,
   `TRUNCATE`, `ALTER`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`,
   `EXEC`, `LOAD`, `OUTFILE`, `COPY`, `ATTACH`, `DETACH`, `PRAGMA`) is rejected.
3. Only approved tables and views in `ecommerce_analytics` may be queried.
"""

from __future__ import annotations

import re

from agents.schemas.agent_schemas import SQLValidationResult

APPROVED_TABLES_AND_VIEWS = {
    "orders_clean",
    "customers_clean",
    "customers_with_geolocation",
    "geolocation_zip_lookup",
    "order_item_summary",
    "order_items_clean",
    "order_level",
    "order_payment_summary",
    "order_review_summary",
    "payments_clean",
    "products_clean",
    "reviews_clean",
    "sellers_clean",
    "sellers_with_geolocation",
    "customer_rfm",
    "vw_executive_monthly_kpis",
    "vw_category_performance",
    "vw_seller_performance",
    "vw_customer_lifecycle",
    "vw_rfm_segments_summary",
    "vw_delivery_and_reviews_by_state",
    "vw_payment_method_summary",
    "vw_order_status_summary",
}

FORBIDDEN_KEYWORDS = {
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "TRUNCATE",
    "ALTER",
    "CREATE",
    "REPLACE",
    "GRANT",
    "REVOKE",
    "CALL",
    "EXEC",
    "EXECUTE",
    "OUTFILE",
    "DUMPFILE",
    "LOAD_FILE",
    "INTO",
    "ATTACH",
    "DETACH",
    "COPY",
    "PRAGMA",
}


def validate_sql_query(sql: str) -> SQLValidationResult:
    """Validate that a SQL query is read-only, single-statement, and uses only approved tables."""
    if not sql or not sql.strip():
        return SQLValidationResult(is_safe=False, reason="Empty SQL query.")

    # Strip SQL comments
    no_comments = re.sub(r"--[^\n]*", "", sql)
    no_comments = re.sub(r"/\*.*?\*/", "", no_comments, flags=re.DOTALL).strip()

    # Remove trailing semicolon and verify no embedded semicolons remain
    cleaned = no_comments.rstrip(";").strip()
    if ";" in cleaned:
        return SQLValidationResult(
            is_safe=False,
            reason="Multiple SQL statements separated by ';' are forbidden.",
        )

    # Remove string literals before keyword scanning
    without_literals = re.sub(r"'[^']*'", "''", cleaned)

    # Must start with SELECT or WITH
    if not re.match(r"^\s*(SELECT|WITH)\b", without_literals, flags=re.IGNORECASE):
        return SQLValidationResult(
            is_safe=False,
            reason="Query must begin with SELECT or WITH (read-only query required).",
        )

    # Check forbidden keywords as whole words
    tokens = {t.upper() for t in re.findall(r"\b[A-Za-z_]+\b", without_literals)}
    blocked = sorted(tokens.intersection(FORBIDDEN_KEYWORDS))
    if blocked:
        return SQLValidationResult(
            is_safe=False,
            reason=f"Forbidden destructive or write keyword(s) detected: {', '.join(blocked)}",
        )

    # Extract CTE names defined via `WITH name AS (` or `, name AS (`
    cte_names = {
        m.lower()
        for m in re.findall(
            r"(?:\bWITH\b|,)\s*([A-Za-z_][A-Za-z0-9_]*)\s+AS\s*\(",
            without_literals,
            flags=re.IGNORECASE,
        )
    }

    # Extract table references after FROM or JOIN
    raw_table_refs = [
        m.lower()
        for m in re.findall(
            r"\b(?:FROM|JOIN)\s+`?([A-Za-z_][A-Za-z0-9_]*)`?",
            without_literals,
            flags=re.IGNORECASE,
        )
    ]
    referenced = sorted(set(raw_table_refs) - cte_names)
    unapproved = [t for t in referenced if t not in APPROVED_TABLES_AND_VIEWS]
    if unapproved:
        return SQLValidationResult(
            is_safe=False,
            reason=f"Unapproved table(s) referenced: {', '.join(unapproved)}",
            referenced_tables=referenced,
        )

    return SQLValidationResult(
        is_safe=True,
        reason="Read-only SELECT query verified against schema allow-list.",
        referenced_tables=referenced,
        normalized_sql=cleaned,
    )
