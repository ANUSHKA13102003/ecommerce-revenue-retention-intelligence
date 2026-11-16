# Step-by-Step Setup & Reproduction Guide

## 1. Prerequisites

| Tool | Recommended Version | Notes |
|---|---|---|
| **Python** | `3.10+` (tested on `3.14`) | Used for data cleaning, SQL execution, analytics, Streamlit, and AI agents |
| **MySQL Server** | `8.0+` *(Optional)* | Used for primary relational storage; `AnalyticsDBEngine` automatically falls back to **DuckDB** if MySQL is not running |
| **Power BI Desktop** | Latest *(Optional)* | For opening the star-schema exports in `powerbi/data_exports/` |
| **Git** | Latest | Version control |

---

## 2. Environment Setup

```bash
# 1. Navigate to the project directory
cd ecommerce-revenue-retention-intelligence

# 2. Activate the virtual environment (or create one)
..\.venv\Scripts\activate      # Windows PowerShell / CMD
pip install -r requirements.txt

# 3. Configure environment variables (optional if using automatic DuckDB mode)
copy .env.example .env
# Edit .env and set MYSQL_PASSWORD=<your_mysql_password> if running local MySQL 8
```

---

## 3. Dataset Placement (`data/raw/`)

Download the [Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) from Kaggle and extract all **9 CSV files** into `data/raw/`:

- `olist_customers_dataset.csv` (`99,441` rows)
- `olist_geolocation_dataset.csv` (`1,000,163` rows)
- `olist_order_items_dataset.csv` (`112,650` rows)
- `olist_order_payments_dataset.csv` (`103,886` rows)
- `olist_order_reviews_dataset.csv` (`99,224` rows)
- `olist_orders_dataset.csv` (`99,441` rows)
- `olist_products_dataset.csv` (`32,951` rows)
- `olist_sellers_dataset.csv` (`3,095` rows)
- `product_category_name_translation.csv` (`71` rows)

---

## 4. Running the Complete Pipeline

Run the pipeline stages in order from the `ecommerce-revenue-retention-intelligence/` directory:

```bash
# Phase 2 & 3: Verify raw files and generate data quality assessment
python src/ingestion/verify_and_profile_raw_data.py
python src/ingestion/phase3_quality_assessment.py

# Phase 4: Clean & transform data into data/processed/ (14 CSVs)
python src/cleaning/run_phase4_cleaning.py

# Phase 5: Load MySQL (if running) & execute all 14 SQL scripts + 8 analytical views
python src/database/execute_and_validate_sql.py

# Phase 6: Generate KPI summary JSON, 8 publication PNG charts, and 6 Jupyter notebooks
python src/analytics/kpi_engine.py
python src/analytics/chart_generator.py
python src/analytics/generate_notebooks.py

# Phase 7 & 8: Generate 8-tab Executive Excel Workbook & 12 Power BI star-schema exports
python src/reporting/excel_report_builder.py
python src/reporting/powerbi_package_builder.py

# Phase 9: Run AI Multi-Agent Orchestrator Demo & generate Executive Markdown Report
python agents/orchestrator.py --demo

# Ask a custom natural-language question via CLI
python agents/orchestrator.py --question "Which regions have the highest delivery delay rate?"

# Phase 10: Launch the 8-Page Interactive Streamlit Application
streamlit run app/streamlit_app.py

# Phase 11: Run Automated Pytest Suite (12 end-to-end tests)
pytest tests/ -v
```
