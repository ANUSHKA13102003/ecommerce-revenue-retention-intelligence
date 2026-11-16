"""
Configuration Module
====================
Loads project settings from environment variables.
Uses python-dotenv to read from a .env file if present.

SECURITY: Never hardcode credentials. Always use .env or
system environment variables.
"""

import os
from pathlib import Path

# ------------------------------------
# Attempt to load .env file
# ------------------------------------
try:
    from dotenv import load_dotenv

    # Walk up to find the project root .env
    _project_root = Path(__file__).resolve().parent.parent
    _env_path = _project_root / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    # python-dotenv not installed; rely on system env vars
    pass


# ------------------------------------
# Project paths
# ------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_RAW_PATH = PROJECT_ROOT / os.getenv("DATA_RAW_PATH", "data/raw")
DATA_PROCESSED_PATH = PROJECT_ROOT / os.getenv("DATA_PROCESSED_PATH", "data/processed")
DATA_EXTERNAL_PATH = PROJECT_ROOT / os.getenv("DATA_EXTERNAL_PATH", "data/external")


# ------------------------------------
# MySQL database
# ------------------------------------
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "ecommerce_analytics")


def get_mysql_connection_string() -> str:
    """
    Build a SQLAlchemy connection URL for MySQL.
    Uses PyMySQL as the driver.

    Returns
    -------
    str
        SQLAlchemy-compatible connection string.

    Raises
    ------
    ValueError
        If MYSQL_PASSWORD is empty (not set).
    """
    if not MYSQL_PASSWORD:
        raise ValueError(
            "MYSQL_PASSWORD is not set. "
            "Create a .env file from .env.example and add your password."
        )
    return (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )


# ------------------------------------
# Optional LLM configuration
# ------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", None)
LLM_API_KEY = os.getenv("LLM_API_KEY", None)
LLM_MODEL = os.getenv("LLM_MODEL", None)


def is_llm_configured() -> bool:
    """Check whether an external LLM provider is configured."""
    return all([LLM_PROVIDER, LLM_API_KEY, LLM_MODEL])


# ------------------------------------
# Logging
# ------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# ------------------------------------
# Expected raw data files
# ------------------------------------
EXPECTED_RAW_FILES = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

