
"""
Load all 14 processed Olist CSV datasets into MySQL.
Raw CSV files are never modified.
"""

from pathlib import Path
from getpass import getpass

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


# Project paths
ROOT = Path(__file__).resolve().parents[2]
DATA_FOLDER = ROOT / "data" / "processed"

DATABASE = "ecommerce_analytics"

# CSV filename -> MySQL table name
DATASETS = {
    "customers_clean.csv": "customers_clean",
    "customers_with_geolocation.csv": "customers_with_geolocation",
    "geolocation_zip_lookup.csv": "geolocation_zip_lookup",
    "order_item_summary.csv": "order_item_summary",
    "order_items_clean.csv": "order_items_clean",
    "order_level.csv": "order_level",
    "order_payment_summary.csv": "order_payment_summary",
    "order_review_summary.csv": "order_review_summary",
    "orders_clean.csv": "orders_clean",
    "payments_clean.csv": "payments_clean",
    "products_clean.csv": "products_clean",
    "reviews_clean.csv": "reviews_clean",
    "sellers_clean.csv": "sellers_clean",
    "sellers_with_geolocation.csv": "sellers_with_geolocation",
}

# Parse these columns as dates during import.
DATE_COLUMNS = {
    "orders_clean.csv": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "order_items_clean.csv": ["shipping_limit_date"],
    "reviews_clean.csv": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "order_review_summary.csv": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
}

# Preserve ZIP prefixes as text.
TEXT_COLUMNS = {
    "customers_clean.csv": ["customer_zip_code_prefix"],
    "customers_with_geolocation.csv": ["customer_zip_code_prefix"],
    "sellers_clean.csv": ["seller_zip_code_prefix"],
    "sellers_with_geolocation.csv": ["seller_zip_code_prefix"],
    "geolocation_zip_lookup.csv": ["zip_code_prefix"],
}


def main():
    print("\nMYSQL DATA IMPORT")
    print("-" * 45)

    host = input("MySQL host [127.0.0.1]: ").strip() or "127.0.0.1"
    port_text = input("MySQL port (use the port shown by Workbench): ").strip()
    port = int(port_text)
    username = input("MySQL username [root]: ").strip() or "root"
    password = getpass("MySQL password (input is hidden): ")

    connection_url = URL.create(
        drivername="mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=port,
        database=DATABASE,
        query={"charset": "utf8mb4"},
    )

    engine = create_engine(
        connection_url,
        pool_pre_ping=True,
    )

    try:
        # Test the connection and database.
        with engine.connect() as connection:
            active_db = connection.execute(
                text("SELECT DATABASE()")
            ).scalar_one()

        print(f"\nConnected to database: {active_db}")

        if active_db != DATABASE:
            raise RuntimeError("Connected to the wrong database.")

        imported = {}

        for filename, table_name in DATASETS.items():
            file_path = DATA_FOLDER / filename

            if not file_path.exists():
                raise FileNotFoundError(
                    f"Processed CSV not found: {file_path}"
                )

            print(f"\nImporting {filename}...")

            options = {"low_memory": False}

            if filename in DATE_COLUMNS:
                options["parse_dates"] = DATE_COLUMNS[filename]

            if filename in TEXT_COLUMNS:
                options["dtype"] = {
                    column: "string"
                    for column in TEXT_COLUMNS[filename]
                }

            df = pd.read_csv(file_path, **options)

            # Do not overwrite an existing table.
            df.to_sql(
                name=table_name,
                con=engine,
                if_exists="fail",
                index=False,
                chunksize=5000,
                method="multi",
            )

            # Verify the imported row count.
            with engine.connect() as connection:
                count = connection.execute(
                    text(f"SELECT COUNT(*) FROM `{table_name}`")
                ).scalar_one()

            if count != len(df):
                raise RuntimeError(
                    f"Row mismatch in {table_name}: "
                    f"CSV={len(df)}, MySQL={count}"
                )

            imported[table_name] = count
            print(f"PASS: {table_name}: {count:,} rows")

        print("\n" + "=" * 50)
        print("MYSQL IMPORT SUMMARY")
        print("=" * 50)

        total_rows = 0

        for table_name, count in imported.items():
            print(f"{table_name:35} {count:>12,}")
            total_rows += count

        print("-" * 50)
        print(f"{'TOTAL ROWS IMPORTED':35} {total_rows:>12,}")
        print(f"TABLES IMPORTED: {len(imported)}")
        print("RESULT: SUCCESS")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
