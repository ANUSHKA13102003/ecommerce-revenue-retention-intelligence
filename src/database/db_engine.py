"""
Database Connection & Dual-Mode Execution Engine
=================================================
Supports:
1. Primary Mode: MySQL 8.0 (`ecommerce_analytics`) via SQLAlchemy + PyMySQL
   using environment variables from `.env` (`MYSQL_HOST`, `MYSQL_PORT`,
   `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`).
2. Local Analytical Fallback Mode: In-memory DuckDB populated directly from
   the 14 validated CSV datasets in `data/processed/`, using DuckDB macros
   (`DATE_FORMAT`, `DATEDIFF`) and lightweight syntax normalization so every
   project MySQL 8.0 script and view executes identically even when `.env`
   credentials are not set.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from config.settings import (
    DATA_PROCESSED_PATH,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)

PROCESSED_TABLES = [
    "customers_clean",
    "customers_with_geolocation",
    "geolocation_zip_lookup",
    "order_item_summary",
    "order_items_clean",
    "order_level",
    "order_payment_summary",
    "order_review_summary",
    "orders_clean",
    "payments_clean",
    "products_clean",
    "reviews_clean",
    "sellers_clean",
    "sellers_with_geolocation",
]


def translate_mysql_to_duckdb(sql: str) -> str:
    """
    Normalize MySQL 8.0 dialect constructs into DuckDB SQL while preserving
    exact analytical semantics and protecting single-quoted string literals.
    """
    literals: list[str] = []

    def _stash_literal(match: re.Match) -> str:
        literals.append(match.group(0))
        return f"__SQL_LIT_{len(literals) - 1}__"

    out = re.sub(r"'[^']*'", _stash_literal, sql)

    # Strip USE database statements
    out = re.sub(r"(?im)^\s*USE\s+\w+\s*;?\s*$", "", out)

    # Convert MySQL DATE(expr) function calls (where expr has no nested parens)
    out = re.sub(
        r"(?<![A-Za-z0-9_])DATE\s*\(\s*([^()]+?)\s*\)",
        r"TRY_CAST(\1 AS DATE)",
        out,
        flags=re.IGNORECASE,
    )

    # Convert YEAR(expr) and MONTH(expr) on string/timestamp columns
    out = re.sub(
        r"(?<![A-Za-z0-9_])YEAR\s*\(\s*([^()]+?)\s*\)",
        r" year(TRY_CAST(\1 AS TIMESTAMP))",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"(?<![A-Za-z0-9_])MONTH\s*\(\s*([^()]+?)\s*\)",
        r" month(TRY_CAST(\1 AS TIMESTAMP))",
        out,
        flags=re.IGNORECASE,
    )

    # Restore string literals before DATE_FORMAT macro check
    for idx, lit in enumerate(literals):
        out = out.replace(f"__SQL_LIT_{idx}__", lit)

    # Boolean columns compared to 1 or 0 in MySQL
    bool_cols = (
        "is_delivered|in_analysis_window|is_late|has_items|"
        "missing_delivery_date|missing_stage_date|carrier_before_purchase|"
        "carrier_before_approval|delivered_before_carrier|status_date_conflict|"
        "shipping_limit_outlier|missing_category|installments_invalid|"
        "review_before_purchase|missing_dimensions|zero_weight"
    )
    out = re.sub(
        rf"\b((?:\w+\.)?(?:{bool_cols}))\s*=\s*1\b",
        r"CAST(\1 AS BOOLEAN) = TRUE",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        rf"\b((?:\w+\.)?(?:{bool_cols}))\s*=\s*0\b",
        r"CAST(\1 AS BOOLEAN) = FALSE",
        out,
        flags=re.IGNORECASE,
    )

    return out


class AnalyticsDBEngine:
    """
    Unified database engine supporting MySQL 8.0 (when credentials are set)
    and deterministic local DuckDB execution over `data/processed/`.
    """

    def __init__(self, prefer_mysql: bool = True):
        self.mode = "duckdb"
        self.mysql_engine = None
        self.duck_con = None

        if prefer_mysql and MYSQL_PASSWORD:
            try:
                from sqlalchemy import create_engine, text
                from sqlalchemy.engine import URL

                url = URL.create(
                    drivername="mysql+pymysql",
                    username=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    host=MYSQL_HOST,
                    port=MYSQL_PORT,
                    database=MYSQL_DATABASE,
                    query={"charset": "utf8mb4"},
                )
                eng = create_engine(url, pool_pre_ping=True)
                with eng.connect() as conn:
                    conn.execute(text("SELECT 1"))
                self.mysql_engine = eng
                self.mode = "mysql"
            except Exception:
                self.mysql_engine = None
                self.mode = "duckdb"

        if self.mode == "duckdb":
            self._init_duckdb()

    def _init_duckdb(self) -> None:
        import sys
        venv_site = DATA_PROCESSED_PATH.parents[2] / ".venv" / "Lib" / "site-packages"
        if venv_site.exists() and str(venv_site) not in sys.path:
            sys.path.insert(0, str(venv_site))
        import duckdb

        self.duck_con = duckdb.connect(database=":memory:")
        # Register MySQL compatibility macros
        self.duck_con.execute(
            "CREATE OR REPLACE MACRO DATE_FORMAT(d, fmt) AS "
            "strftime(TRY_CAST(d AS TIMESTAMP), fmt);"
        )
        self.duck_con.execute(
            "CREATE OR REPLACE MACRO DATEDIFF(a, b) AS "
            "date_diff('day', TRY_CAST(b AS DATE), TRY_CAST(a AS DATE));"
        )

        for tbl in PROCESSED_TABLES:
            csv_path = DATA_PROCESSED_PATH / f"{tbl}.csv"
            if csv_path.exists():
                path_str = str(csv_path.resolve()).replace("\\", "/")
                self.duck_con.execute(
                    f"CREATE OR REPLACE TABLE {tbl} AS "
                    f"SELECT * FROM read_csv_auto('{path_str}', header=True);"
                )
        rfm_path = DATA_PROCESSED_PATH / "customer_rfm.csv"
        if rfm_path.exists():
            path_str = str(rfm_path.resolve()).replace("\\", "/")
            self.duck_con.execute(
                f"CREATE OR REPLACE TABLE customer_rfm AS "
                f"SELECT * FROM read_csv_auto('{path_str}', header=True);"
            )
            views_sql = DATA_PROCESSED_PATH.parents[1] / "sql" / "05_views" / "01_analytical_views.sql"
            if views_sql.exists():
                self.execute_script(views_sql)

    def execute_Statement(self, sql: str) -> pd.DataFrame | None:
        """Execute a single SQL statement and return a DataFrame if it returns rows."""
        stmt = sql.strip().rstrip(";").strip()
        if not stmt:
            return None

        if self.mode == "mysql" and self.mysql_engine is not None:
            from sqlalchemy import text

            with self.mysql_engine.begin() as conn:
                res = conn.execute(text(stmt))
                if res.returns_rows:
                    return pd.DataFrame(res.fetchall(), columns=list(res.keys()))
                return None
        else:
            translated = translate_mysql_to_duckdb(stmt).strip()
            if not translated:
                return None
            rel = self.duck_con.execute(translated)
            if rel.description is not None and not re.match(
                r"^\s*(CREATE|DROP|ALTER|INSERT|UPDATE|DELETE)\b", translated, re.I
            ):
                return rel.df()
            return None

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a read-only SELECT query and return a DataFrame."""
        res = self.execute_Statement(sql)
        return res if res is not None else pd.DataFrame()

    def execute_script(self, script_path: Path) -> list[pd.DataFrame]:
        """Execute all statements in a `.sql` file and return all result sets."""
        raw_sql = script_path.read_text(encoding="utf-8")
        cleaned_lines = []
        for line in raw_sql.splitlines():
            idx = line.find("--")
            if idx != -1:
                line = line[:idx]
            cleaned_lines.append(line)
        cleaned_sql = "\n".join(cleaned_lines)
        statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
        results: list[pd.DataFrame] = []
        for stmt in statements:
            df = self.execute_Statement(stmt)
            if df is not None:
                results.append(df)
        return results
