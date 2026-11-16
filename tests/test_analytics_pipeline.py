"""
Comprehensive Automated Test Suite (`pytest`)
==============================================
Tests all 17 critical verification domains across the end-to-end project:
  1. Raw data existence & row count integrity
  2. Cleaning pipeline row count preservation
  3. Primary & composite key uniqueness
  4. Quality flags & missing-value preservation (no silent deletions)
  5. Grain-safe aggregation & financial reconciliation (BRL)
  6. Revenue definitions (Rule D-1: Order Value Proxy vs Merchandise Revenue)
  7. Repeat customer definitions (Rule D-5 vs sensitivity options a & c)
  8. RFM customer segmentation exact match (93,358 customers)
  9. Monthly cohort retention matrix accuracy (Rule D-2 window)
 10. SQL safety validator (blocks DDL/DML/multi-statement/unapproved tables)
 11. Agentic orchestrator end-to-end Q&A and audit logging
 12. Deliverables existence check (Excel, Power BI, Charts, Notebooks)
 13. AI Business Analyst — All 6 required benchmark questions & Rule D-1 distinction
 14. AI Business Analyst — Safe handling of unsupported / out-of-scope questions
 15. Excel Executive Workbook — Sheet structure, formulas, number formats & reconciliation
 16. Power BI Star-Schema Package — Key uniqueness, date FK integrity & reconciliation
 17. Streamlit Application — Data loader, 8 navigation modules & BRL formatting helpers

Run:
    pytest tests/ -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.orchestrator import AnalyticsOrchestrator
from agents.tools.sql_safety_validator import validate_sql_query
from src.ingestion.check_files import check_files

PROCESSED = ROOT / "data" / "processed"
SQL_OUT = ROOT / "reports" / "sql_outputs"
CLEAN_LOG = ROOT / "reports" / "data_quality" / "cleaning_log.json"
SUMMARY_JSON = ROOT / "reports" / "analytics_summary.json"


def test_01_raw_files_exist() -> None:
    """Verify all 9 official Olist CSV files exist in data/raw/."""
    assert check_files() is True


def test_02_cleaning_row_counts_preserved() -> None:
    """Verify cleaned datasets preserve exact raw row counts with zero silent deletions."""
    log = json.loads(CLEAN_LOG.read_text(encoding="utf-8"))
    counts = log["output_row_counts"]
    assert counts["orders_clean"] == 99441
    assert counts["customers_clean"] == 99441
    assert counts["order_items_clean"] == 112650
    assert counts["payments_clean"] == 103886
    assert counts["reviews_clean"] == 99224
    assert counts["products_clean"] == 32951
    assert counts["sellers_clean"] == 3095
    assert counts["geolocation_zip_lookup"] == 17737
    assert counts["order_item_summary"] == 98666
    assert counts["order_payment_summary"] == 99440
    assert counts["order_review_summary"] == 98673
    assert counts["order_level"] == 99441
    assert log["validation_checks"]["raw_files_unchanged"] is True
    assert log["all_checks_passed"] is True


def test_03_key_uniqueness() -> None:
    """Verify primary and composite key uniqueness on processed tables."""
    pk_df = pd.read_csv(SQL_OUT / "02_key_and_reconciliation_checks_result_1.csv")
    assert (pk_df["duplicate_keys"] == 0).all()

    fk_df = pd.read_csv(SQL_OUT / "02_key_and_reconciliation_checks_result_2.csv")
    assert (fk_df["orphan_rows"] == 0).all()


def test_04_missing_value_and_quality_flags() -> None:
    """Verify documented quality flags match Phase 3/4 measurements."""
    log = json.loads(CLEAN_LOG.read_text(encoding="utf-8"))
    flags = log["quality_flag_counts"]
    assert flags["missing_delivery_date"] == 2965
    assert flags["status_date_conflict"] == 8
    assert flags["orders_without_items"] == 775
    assert flags["orders_without_payments"] == 1
    assert flags["shipping_limit_outliers"] == 12
    assert flags["invalid_installments"] == 2


def test_05_aggregation_and_financial_reconciliation() -> None:
    """Verify order_level financial totals reconcile to the cent with raw item & payment tables."""
    rec_df = pd.read_csv(SQL_OUT / "02_key_and_reconciliation_checks_result_3.csv")
    row = rec_df.iloc[0]
    assert np.isclose(row["raw_item_price_total_brl"], 13591643.70)
    assert np.isclose(row["order_level_item_revenue_total_brl"], 13591643.70)
    assert np.isclose(row["raw_freight_total_brl"], 2251909.54)
    assert np.isclose(row["order_level_freight_total_brl"], 2251909.54)
    assert np.isclose(row["raw_payment_total_brl"], 16008872.12)
    assert np.isclose(row["order_level_payment_total_brl"], 16008872.12)
    assert np.isclose(row["delivered_order_value_proxy_brl"], 15422461.77)


def test_06_revenue_definitions_and_category_totals() -> None:
    """Verify Rule D-1 revenue definitions across delivered orders and categories."""
    summary = json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    kf = summary["executive_kpis"]["full_dataset"]
    assert kf["delivered_orders"] == 96478
    assert np.isclose(kf["delivered_order_value_proxy_brl"], 15422461.77)
    assert np.isclose(kf["delivered_item_revenue_brl"], 13221498.11)

    cat_df = pd.read_csv(SQL_OUT / "02_product_and_category_performance_result_1.csv")
    assert len(cat_df) == 74
    assert cat_df.iloc[0]["category_name_en"] == "health_beauty"
    assert np.isclose(cat_df["item_revenue_brl"].sum(), 13221498.11)


def test_07_repeat_customer_definitions_d5() -> None:
    """Verify Rule D-5 repeat customer counts and sensitivity checks (a) and (c)."""
    clv_sens = pd.read_csv(SQL_OUT / "03_customer_lifetime_value_proxy_result_1.csv").iloc[0]
    assert int(clv_sens["total_unique_customers_all_statuses"]) == 96096
    assert int(clv_sens["total_delivered_customers"]) == 93358
    assert int(clv_sens["repeat_customers_d5_distinct_days"]) == 2015
    assert np.isclose(clv_sens["repeat_rate_d5_pct"], 2.16)
    assert int(clv_sens["repeat_customers_opt_a_delivered"]) == 2801
    assert np.isclose(clv_sens["repeat_rate_opt_a_pct"], 3.00)
    assert int(clv_sens["repeat_customers_opt_c_all_statuses"]) == 2997
    assert np.isclose(clv_sens["repeat_rate_opt_c_pct"], 3.12)


def test_08_rfm_segmentation_exact_baseline() -> None:
    """Verify RFM segmentation matches the exact validated MySQL baseline."""
    rfm_sum = pd.read_csv(SQL_OUT / "vw_rfm_segments_summary.csv")
    actual = dict(zip(rfm_sum["customer_segment"], rfm_sum["customer_count"].astype(int)))
    expected = {
        "Lost Customers": 37358,
        "Recent Customers": 37219,
        "Needs Attention": 18272,
        "Potential Loyalists": 449,
        "At Risk": 31,
        "Champions": 23,
        "Loyal Customers": 6,
    }
    assert actual == expected
    assert sum(actual.values()) == 93358


def test_09_cohort_retention_matrix() -> None:
    """Verify cohort retention matrix covers 20 cohorts (2017-01 to 2018-08) with 100% M0."""
    coh_df = pd.read_csv(SQL_OUT / "01_cohort_retention_analysis_result_2.csv")
    assert len(coh_df) == 20
    assert coh_df["cohort_month"].iloc[0] == "2017-01"
    assert coh_df["cohort_month"].iloc[-1] == "2018-08"
    assert np.allclose(coh_df["m0_pct"], 100.0)
    assert int(coh_df["cohort_size"].sum()) == 93104


def test_10_sql_safety_validator() -> None:
    """Verify SQL safety validator blocks destructive/write/unapproved queries and allows read-only SELECTs."""
    ok_res = validate_sql_query("SELECT customer_segment, customer_count FROM vw_rfm_segments_summary")
    assert ok_res.is_safe is True

    for bad_sql in [
        "DROP TABLE orders_clean",
        "DELETE FROM order_level WHERE is_delivered = 0",
        "UPDATE products_clean SET category_name_en = 'hacked'",
        "TRUNCATE TABLE payments_clean",
        "SELECT * FROM orders_clean; DROP TABLE orders_clean",
        "SELECT * FROM secret_users_table",
    ]:
        res = validate_sql_query(bad_sql)
        assert res.is_safe is False, f"Expected query to be blocked: {bad_sql}"


def test_11_agentic_orchestrator_end_to_end() -> None:
    """Verify orchestrator routes questions, returns verified numbers, and blocks unsafe SQL."""
    orch = AnalyticsOrchestrator()
    r1 = orch.ask("Which customer segments generate the most revenue?")
    assert r1.validation.is_safe is True
    assert r1.row_count == 7
    assert "Recent Customers" in r1.factual_summary

    r_bad = orch.ask("Malicious test", custom_sql="DELETE FROM orders_clean")
    assert r_bad.validation.is_safe is False
    assert r_bad.row_count == 0


def test_12_deliverables_exist() -> None:
    """Verify Excel report, Power BI exports, charts, and notebooks exist and are non-empty."""
    excel_file = ROOT / "reports" / "executive_summary" / "Ecommerce_Revenue_Retention_Intelligence_Report.xlsx"
    assert excel_file.exists() and excel_file.stat().st_size > 15000

    pbi_date = ROOT / "powerbi" / "data_exports" / "dim_date.csv"
    assert pbi_date.exists() and len(pd.read_csv(pbi_date)) == 1096

    charts = list((ROOT / "reports" / "charts").glob("*.png"))
    assert len(charts) >= 8

    notebooks = list((ROOT / "notebooks").glob("*.ipynb"))
    assert len(notebooks) == 6


def test_13_ai_six_benchmark_questions_and_governance() -> None:
    """Verify all benchmark and Copilot business questions route accurately and respect Rule D-1 & D-5."""
    orch = AnalyticsOrchestrator()
    cases = [
        ("Which customer segments generate the most order value?", "rfm_segments", 7, "6,269,299.23"),
        ("What is the repeat customer rate under the approved D-5 definition?", "repeat_purchase_rate", 2, "2.16%"),
        ("Which categories contribute the most merchandise revenue?", "category_performance", 15, "health_beauty"),
        ("Does late delivery relate to lower review scores?", "delivery_vs_reviews", 6, "-1.72"),
        ("Which sellers account for the largest share of merchandise sales?", "seller_performance", 20, "67.11%"),
        ("How has monthly order value changed?", "monthly_revenue_trend", 20, "15,375,875.44"),
        ("Why did order value decline in June 2018?", "june_2018_decline_analysis", 6, "-10.34%"),
        ("What business actions should management consider?", "executive_decision_actions", 7, "67.11%"),
    ]
    for question, expected_intent, expected_rows, expected_substring in cases:
        resp = orch.ask(question)
        assert resp.intent == expected_intent, f"Failed intent for: {question}"
        assert resp.validation.is_safe is True
        assert resp.row_count == expected_rows
        assert expected_substring in resp.factual_summary
        assert len(resp.source_tables) >= 1
        assert len(resp.metric_definitions) >= 1


def test_14_ai_unsupported_and_out_of_scope_questions() -> None:
    """Verify unsupported or unmeasured questions trigger ScopeGuardrail without fabricating results."""
    orch = AnalyticsOrchestrator()
    for out_of_scope_q in [
        "What is the company net profit margin after marketing CAC?",
        "What is the weather forecast in Sao Paulo tomorrow?",
        "Show me employee payroll salaries",
        "",
    ]:
        resp = orch.ask(out_of_scope_q)
        assert resp.intent == "unsupported_question"
        assert resp.row_count == 0
        assert resp.data_preview == []


def test_15_excel_workbook_structure_formulas_and_reconciliation() -> None:
    """Verify the 10-sheet Executive Excel Workbook sheets, tables, formulas, formats, and reconciled KPIs."""
    excel_file = ROOT / "reports" / "executive_summary" / "Ecommerce_Revenue_Retention_Intelligence_Report.xlsx"
    wb = load_workbook(excel_file, data_only=False)
    expected_sheets = [
        "Executive_Summary",
        "KPI_Overview",
        "Revenue_Trends",
        "Customer_Analytics",
        "RFM_Segmentation",
        "Cohort_Retention",
        "Product_Seller_Performance",
        "Delivery_Satisfaction",
        "Data_Quality",
        "Metric_Definitions",
    ]
    assert wb.sheetnames == expected_sheets

    ws_kpi = wb["KPI_Overview"]
    # Row 5: KPI-001 Total Orders = 99441 (formatted #,##0)
    assert ws_kpi["C5"].value == 99441
    assert ws_kpi["C5"].number_format == "#,##0"
    # Row 8: KPI-004 Delivered Order Value Proxy = 15422461.77 (formatted "R$" #,##0.00)
    assert np.isclose(ws_kpi["C8"].value, 15422461.77)
    assert ws_kpi["C8"].number_format == '"R$" #,##0.00'
    # Row 9: KPI-005 Delivered Merchandise Revenue = 13221498.11
    assert np.isclose(ws_kpi["C9"].value, 13221498.11)
    # Row 15: KPI-011 True Repeat Customer Rate = 2.16%
    assert np.isclose(ws_kpi["C15"].value, 2.16)
    assert ws_kpi["C15"].number_format == '0.00"%"'

    # Check SUM formula on Product_Seller_Performance item_revenue_brl (Column H, row 79) and revenue_share_pct (Column M, row 79)
    ws_ps = wb["Product_Seller_Performance"]
    assert ws_ps["H79"].value == "=SUM(H5:H78)"
    assert ws_ps["M79"].value == "=SUM(M5:M78)"

    # Check embedded charts exist on Revenue_Trends and RFM_Segmentation
    assert len(wb["Revenue_Trends"]._charts) == 1
    assert len(wb["RFM_Segmentation"]._charts) == 1


def test_16_powerbi_star_schema_exports_and_keys() -> None:
    """Verify Power BI exports, date key uniqueness, foreign key integrity, and relationship manifest."""
    pbi_dir = ROOT / "powerbi" / "data_exports"
    dim_date = pd.read_csv(pbi_dir / "dim_date.csv")
    assert len(dim_date) == 1096
    assert dim_date["date_key"].is_unique

    mon = pd.read_csv(pbi_dir / "pbi_monthly_kpis.csv")
    assert "month_start_date" in mon.columns
    assert set(mon["month_start_date"]).issubset(set(dim_date["date_key"]))
    assert np.isclose(mon["order_value_proxy_brl"].sum(), 15375875.44)

    coh = pd.read_csv(pbi_dir / "pbi_cohort_retention_matrix.csv")
    assert "cohort_start_date" in coh.columns
    assert set(coh["cohort_start_date"]).issubset(set(dim_date["date_key"]))

    rel_json = json.loads((pbi_dir / "star_schema_relationships.json").read_text(encoding="utf-8"))
    assert len(rel_json["granular_star_schema_relationships"]) == 7
    assert len(rel_json["summary_mart_relationships"]) == 3


def test_17_streamlit_data_loader_and_helpers() -> None:
    """Verify Streamlit application module imports, cached data loader, and 8 page renderers."""
    import app.streamlit_app as sa

    assert len(sa.PAGE_OPTIONS) == 8
    assert len(sa.COPILOT_QUESTIONS) == 8
    card_html = sa.render_kpi_card("Test KPI", "R$ 15,422,461.77", "Rule D-1", "blue")
    assert "R$ 15,422,461.77" in card_html

    data = sa.load_platform_data()
    assert len(data["monthly"]) == 20
    assert len(data["categories"]) == 74
    assert len(data["rfm"]) == 7
    assert len(data["states"]) == 27


def test_18_metric_catalogue_and_reconciliation_report() -> None:
    """Verify the 18-KPI Centralised Metric Catalogue, Cross-Platform Reconciliation Report, and PDF Report."""
    from src.analytics.metric_catalogue import get_metric_catalogue

    cat = get_metric_catalogue()
    assert len(cat) == 18

    recon_file = ROOT / "reports" / "reconciliation" / "reconciliation_report.json"
    assert recon_file.exists()
    recon = json.loads(recon_file.read_text(encoding="utf-8"))
    assert recon["total_kpis_checked"] == 18
    assert recon["kpis_passed"] == 18
    assert "PASS" in recon["overall_status"]

    pdf_file = ROOT / "reports" / "executive_summary" / "Ecommerce_Intelligence_OS_Executive_Report.pdf"
    assert pdf_file.exists() and pdf_file.stat().st_size > 20000

