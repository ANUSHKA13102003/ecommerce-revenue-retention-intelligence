"""
Enterprise Excel Business Report Builder (10 Worksheets)
========================================================
Builds a 10-sheet executive Excel workbook using `openpyxl`:
  `reports/executive_summary/Ecommerce_Revenue_Retention_Intelligence_Report.xlsx`

Sheets Included:
  1. Executive_Summary
  2. KPI_Overview
  3. Revenue_Trends
  4. Customer_Analytics
  5. RFM_Segmentation
  6. Cohort_Retention
  7. Product_Seller_Performance
  8. Delivery_Satisfaction
  9. Data_Quality
  10. Metric_Definitions
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analytics.metric_catalogue import get_metric_catalogue

SQL_OUT = ROOT / "reports" / "sql_outputs"
OUT_DIR = ROOT / "reports" / "executive_summary"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADER_FILL = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
SUBHEADER_FILL = PatternFill(start_color="E2E8F0", end_color="E2E8F0", fill_type="solid")
TOTAL_FILL = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="0F172A")
SUBTITLE_FONT = Font(name="Calibri", size=10, italic=True, color="475569")
BOLD_FONT = Font(name="Calibri", size=10, bold=True, color="0F172A")
REGULAR_FONT = Font(name="Calibri", size=10, color="1E293B")
THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def _style_sheet_banner(ws, title: str, subtitle: str) -> None:
    ws.views.sheetView[0].showGridLines = True
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    ws["A2"] = subtitle
    ws["A2"].font = SUBTITLE_FONT


def _write_dataframe_table(
    ws,
    df: pd.DataFrame,
    table_name: str,
    start_row: int = 4,
    currency_cols: set[str] | None = None,
    pct_cols: set[str] | None = None,
    sum_pct_cols: set[str] | None = None,
    int_cols: set[str] | None = None,
    add_totals_row: bool = False,
) -> int:
    currency_cols = currency_cols or set()
    pct_cols = pct_cols or set()
    sum_pct_cols = sum_pct_cols or set()
    int_cols = int_cols or set()

    for col_idx, col_name in enumerate(df.columns, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=str(col_name))
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for r_offset, row_vals in enumerate(df.itertuples(index=False), start=1):
        r_idx = start_row + r_offset
        for c_idx, (col_name, val) in enumerate(zip(df.columns, row_vals), start=1):
            if pd.isna(val):
                cell_val = None
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                cell_val = (
                    float(val)
                    if not float(val).is_integer()
                    or col_name in currency_cols
                    or col_name in pct_cols
                    or col_name in sum_pct_cols
                    else int(val)
                )
            else:
                cell_val = val
            cell = ws.cell(row=r_idx, column=c_idx, value=cell_val)
            cell.font = REGULAR_FONT
            cell.border = THIN_BORDER

            if col_name in currency_cols:
                cell.number_format = '"R$" #,##0.00'
            elif col_name in pct_cols or col_name in sum_pct_cols:
                cell.number_format = '0.00"%"'
            elif col_name in int_cols:
                cell.number_format = "#,##0"
            elif isinstance(cell_val, float):
                cell.number_format = "#,##0.00"

    end_data_row = start_row + len(df)
    last_col_letter = get_column_letter(len(df.columns))
    tab_ref = f"A{start_row}:{last_col_letter}{end_data_row}"
    tab = Table(displayName=table_name, ref=tab_ref)
    tab.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(tab)

    if add_totals_row and len(df) > 0:
        tot_row = end_data_row + 1
        ws.cell(row=tot_row, column=1, value="TOTAL / AVERAGE").font = BOLD_FONT
        ws.cell(row=tot_row, column=1).fill = TOTAL_FILL
        for c_idx, col_name in enumerate(df.columns, start=1):
            col_let = get_column_letter(c_idx)
            c_cell = ws.cell(row=tot_row, column=c_idx)
            c_cell.fill = TOTAL_FILL
            c_cell.font = BOLD_FONT
            c_cell.border = THIN_BORDER
            if c_idx == 1:
                continue
            if col_name in currency_cols or col_name in int_cols:
                c_cell.value = f"=SUM({col_let}{start_row+1}:{col_let}{end_data_row})"
                c_cell.number_format = (
                    '"R$" #,##0.00' if col_name in currency_cols else "#,##0"
                )
            elif col_name in sum_pct_cols:
                c_cell.value = f"=SUM({col_let}{start_row+1}:{col_let}{end_data_row})"
                c_cell.number_format = '0.00"%"'
            elif col_name in pct_cols:
                c_cell.value = f"=AVERAGE({col_let}{start_row+1}:{col_let}{end_data_row})"
                c_cell.number_format = '0.00"%"'

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row < start_row:
                continue
            val_str = str(cell.value or "")
            if val_str.startswith("="):
                val_str = "R$ 99,999,999.99"
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(min(max_len + 5, 48), 14)

    ws.freeze_panes = f"A{start_row + 1}"
    return end_data_row


def build_excel_report() -> Path:
    summary = json.loads((ROOT / "reports" / "analytics_summary.json").read_text(encoding="utf-8"))
    kpis_full = summary["executive_kpis"]["full_dataset"]
    kpis_win = summary["executive_kpis"]["analysis_window_2017_01_to_2018_08"]
    ret_full = summary["retention_metrics"]["full_dataset_delivered"]
    stat_tests = summary["statistical_tests"]["on_time_vs_late_review_score_mann_whitney"]

    wb = Workbook()

    # 1. Executive_Summary
    ws_exec = wb.active
    ws_exec.title = "Executive_Summary"
    _style_sheet_banner(
        ws_exec,
        "E-COMMERCE INTELLIGENCE OS — EXECUTIVE BUSINESS SUMMARY & DECISION CENTRE",
        "Dataset: Olist Brazilian E-Commerce (99,441 Orders | R$ 15,422,461.77 Delivered Order Value Proxy | Jan 2017 – Aug 2018 Primary Window)",
    )
    exec_rows = [
        (
            "DEC-01",
            "Customer Retention & Lifecycle CRM",
            "97.84% of delivered customers (91,343 of 93,358) never make a repeat multi-day purchase (D-5 repeat rate = 2.16%, 2,015 customers). True repeaters generate 2.0x higher CLV (R$ 320.82 vs R$ 160.76).",
            "Launch automated 30-to-45 day post-delivery replenishment vouchers targeting 37,219 'Recent Customers' (R$ 6,269,299.23) and win-back flows for 18,272 'Needs Attention' customers (R$ 2,798,239.09).",
            "Lift D-5 repeat rate from 2.16% to 3.50%–4.00% (+R$ 200,000 to +R$ 275,000 incremental order value proxy).",
            "High (Verified SQL + Python RFM & CLV)",
        ),
        (
            "DEC-02",
            "Inter-State Logistics SLA & EDD Recalibration",
            "8.11% of delivered orders (7,826 orders) arrive past the promised EDD, causing a -1.73 star review collapse (4.29 on-time vs 2.57 late; p < 0.0001). Orders 8+ days late (2,862) suffer a 69.87% 1-star rate.",
            "Add +2 to +3 business day EDD buffers on high-delay corridors (RJ 13.47% late, BA 14.04%, CE 15.32%, AL 23.93%) and trigger proactive carrier exception alerts 48h prior to EDD breach.",
            "Cut late delivery rate from 8.11% to <4.50%, preventing ~1,400+ 1-star reviews and lifting platform rating from 4.16 to ~4.22 stars.",
            "High (Mann-Whitney U = 524.6M, p < 0.0001)",
        ),
        (
            "DEC-03",
            "Top-Decile Seller Key-Account Governance",
            "Out of 2,970 active delivered sellers, the Top 10% (297 sellers, Decile 1) generate 67.11% (R$ 8,873,076.37) of all R$ 13,221,498.11 delivered merchandise revenue; Top 20% (594 sellers) generate 82.29%.",
            "Establish dedicated key-account retention treaties for the top 297 sellers and enforce dispatch SLA audits on high-volume merchants exceeding the 8.11% late-delivery threshold.",
            "Protect R$ 8.87M core merchandise supply and reduce seller-originated dispatch bottlenecks.",
            "High (Exact NTILE(10) Seller Decile Census)",
        ),
        (
            "DEC-04",
            "Core Category Merchandising & Regional 3PL",
            "Top 5 of 74 categories (health_beauty R$ 1.23M, watches_gifts R$ 1.17M, bed_bath_table R$ 1.02M, sports_leisure R$ 0.95M, computers_accessories R$ 0.89M) drive 39.83% (R$ 5.27M) of item revenue.",
            "Prioritize regional Northeast/RJ 3PL inventory placement for top-5 fast-moving categories and promote interest-free credit card installments on baskets >R$ 150.",
            "Reduce inter-state freight ratios (20%–29% in North/Northeast vs 12% in SP) and shorten transit times by 4–6 days.",
            "High (74-Category Census & State Matrix)",
        ),
    ]
    exec_df = pd.DataFrame(
        exec_rows,
        columns=[
            "Decision_ID",
            "Strategic_Domain",
            "Empirical_Evidence_From_Data",
            "Recommended_Management_Action",
            "Quantified_Expected_Impact_Range",
            "Confidence_Level",
        ],
    )
    _write_dataframe_table(ws_exec, exec_df, "tbl_ExecutiveDecisions", start_row=4)

    # 2. KPI_Overview
    ws_kpi = wb.create_sheet("KPI_Overview")
    _style_sheet_banner(
        ws_kpi,
        "E-COMMERCE INTELLIGENCE OS — CANONICAL KPI OVERVIEW (18 RECONCILED METRICS)",
        "Single Source of Truth Across MySQL, Python, Excel, Streamlit & Power BI | Currency: BRL (R$)",
    )
    kpi_rows = [
        ("KPI-001", "Total Orders (All Statuses)", kpis_full["total_orders_all_statuses"], "Orders", "Full Dataset (Sep 2016 – Oct 2018); Window: 99,092"),
        ("KPI-002", "Delivered Orders", kpis_full["delivered_orders"], "Orders", "Full Dataset: 96,478 | Jan 2017 – Aug 2018 Window: 96,211"),
        ("KPI-003", "Delivery Completion Rate", kpis_full["delivery_completion_rate_pct"], "%", "96,478 / 99,441 total orders"),
        ("KPI-004", "Delivered Order Value (Revenue Proxy)", kpis_full["delivered_order_value_proxy_brl"], "BRL", "Rule D-1: SUM(payment_value) on delivered orders (Window: R$ 15,375,875.44)"),
        ("KPI-005", "Delivered Item Merchandise Revenue", kpis_full["delivered_item_revenue_brl"], "BRL", "Rule D-1: SUM(price) on delivered orders (Window: R$ 13,181,027.13)"),
        ("KPI-006", "Delivered Freight Value", kpis_full["delivered_freight_value_brl"], "BRL", "Rule D-1: SUM(freight_value) on delivered orders (Window: R$ 2,192,092.88)"),
        ("KPI-007", "Gross Payment Value (All Statuses)", kpis_full["all_orders_payment_total_brl"], "BRL", "All 99,441 orders prior to delivered status filter"),
        ("KPI-008", "Mean Order Value (AOV Proxy)", kpis_full["average_order_value_proxy_brl"], "BRL", "Delivered Order Value / 96,478 (Window: R$ 159.81)"),
        ("KPI-009", "Median Order Value Proxy", kpis_full["median_order_value_proxy_brl"], "BRL", "50th percentile (IQR: R$ 114.45; P25 R$ 61.85 – P75 R$ 176.30)"),
        ("KPI-010", "Unique Delivered Customers", kpis_full["unique_delivered_customers"], "Customers", "Distinct customer_unique_id (All Statuses: 96,096; Window: 93,104)"),
        ("KPI-011", "True Repeat Customer Rate (Rule D-5)", ret_full["repeat_rate_d5_pct"], "%", "2,015 customers with 2+ delivered orders on 2+ distinct calendar days"),
        ("KPI-012", "Repeat Customer Revenue Share (D-5)", ret_full["repeat_customer_revenue_share_d5_pct"], "%", "R$ 646,454.25 / R$ 15,422,461.77 (Avg CLV R$ 320.82 vs R$ 160.76)"),
        ("KPI-013", "Average Delivery Days", kpis_full["avg_delivery_days"], "Days", "Median: 10.22 days across 96,470 delivered orders with valid date"),
        ("KPI-014", "Late Delivery Rate (Timestamp)", kpis_full["late_delivery_rate_timestamp_pct"], "%", "7,826 / 96,470 delivered orders (Calendar-day rate: 6.77%)"),
        ("KPI-015", "Average Customer Review Score", kpis_full["avg_review_score_delivered"], "Stars (1-5)", "95,832 reviewed delivered orders (Rule D-3 latest review)"),
        ("KPI-016", "Late Delivery Review Score Drop", round(stat_tests["score_drop_when_late"], 2), "Stars (1-5)", "On-Time 4.29 stars (88,163) vs Late 2.57 stars (7,661), p < 0.0001"),
        ("KPI-017", "Top Category Item Revenue (health_beauty)", 1233131.72, "BRL", "Rank #1 of 74 categories (9.33% of delivered item revenue)"),
        ("KPI-018", "Top 10% Seller Revenue Share (Decile 1)", 67.11, "%", "Top 297 of 2,970 active delivered sellers generate R$ 8,873,076.37"),
    ]
    kpi_df = pd.DataFrame(
        kpi_rows, columns=["KPI_ID", "KPI_Metric", "Measured_Value", "Unit", "Methodology_and_Scope_Note"]
    )
    _write_dataframe_table(ws_kpi, kpi_df, "tbl_KPIOverview", start_row=4)
    for r_offset, (_, _, _, unit_label, _) in enumerate(kpi_rows, start=1):
        val_cell = ws_kpi.cell(row=4 + r_offset, column=3)
        if unit_label == "BRL":
            val_cell.number_format = '"R$" #,##0.00'
        elif unit_label in ("Orders", "Customers"):
            val_cell.number_format = "#,##0"
        elif unit_label == "%":
            val_cell.number_format = '0.00"%"'
        else:
            val_cell.number_format = "0.00"

    # 3. Revenue_Trends
    ws_mon = wb.create_sheet("Revenue_Trends")
    _style_sheet_banner(
        ws_mon,
        "MONTHLY REVENUE PROXY & ORDER TRENDS (JAN 2017 – AUG 2018)",
        "Approved Analysis Window (Rule D-2: 96,211 Delivered Orders, R$ 15,375,875.44 Order Value Proxy)",
    )
    mon_df = pd.read_csv(SQL_OUT / "vw_executive_monthly_kpis.csv")
    end_r = _write_dataframe_table(
        ws_mon,
        mon_df,
        "tbl_RevenueTrends",
        start_row=4,
        currency_cols={
            "order_value_proxy_brl",
            "item_revenue_brl",
            "freight_value_brl",
            "average_order_value_brl",
            "prev_month_order_value_brl",
        },
        pct_cols={"mom_growth_pct", "late_delivery_rate_pct"},
        int_cols={"delivered_orders", "active_customers"},
        add_totals_row=True,
    )
    chart_mon = LineChart()
    chart_mon.title = "Monthly Delivered Order Value Proxy (BRL)"
    chart_mon.y_axis.title = "Order Value Proxy (BRL)"
    chart_mon.x_axis.title = "Sales Month"
    chart_mon.width = 18
    chart_mon.height = 10
    chart_mon.add_data(Reference(ws_mon, min_col=4, min_row=4, max_row=end_r), titles_from_data=True)
    chart_mon.set_categories(Reference(ws_mon, min_col=1, min_row=5, max_row=end_r))
    ws_mon.add_chart(chart_mon, "N4")

    # 4. Customer_Analytics
    ws_cust = wb.create_sheet("Customer_Analytics")
    _style_sheet_banner(
        ws_cust,
        "CUSTOMER RETENTION, REPEAT PURCHASE SENSITIVITY (D-5) & INACTIVITY WINDOWS",
        "Customer Grain: customer_unique_id (93,358 Delivered Customers | 96,096 Total Customers)",
    )
    cust_rows = [
        ("Approved Rule D-5 (2+ Delivered Orders on 2+ Distinct Dates)", 93358, 2015, 2.16, 646454.25, 320.82, "Primary repeat metric; excludes 786 same-day split checkouts"),
        ("Sensitivity Option A (2+ Delivered Orders on Any Date)", 93358, 2801, 3.00, 864357.21, 308.59, "Includes 786 customers with multiple orders on the same day"),
        ("Same-Day Split-Checkout Buyers Only (2+ Orders, 1 Calendar Day)", 93358, 786, 0.84, 217902.96, 277.23, "Multi-seller cart splits placed on a single purchase day"),
        ("Strictly Single-Order Delivered Buyers (1 Delivered Order)", 93358, 90557, 97.00, 14558104.56, 160.76, "Baseline one-time delivered customer population"),
        ("Sensitivity Option C (All Order Statuses, Any Date)", 96096, 2997, 3.12, 912450.15, 304.45, "Includes non-delivered repeat attempts across all 8 statuses"),
        ("Analytical Inactivity > 90 Days (Not Observed Churn, D-6)", 93358, 74838, 80.16, 12310450.12, 164.49, "Recency > 90 days relative to 2018-10-17 dataset cutoff"),
        ("Analytical Inactivity > 180 Days (Not Observed Churn, D-6)", 93358, 55132, 59.05, 9055124.80, 164.24, "Recency > 180 days relative to 2018-10-17 dataset cutoff"),
        ("Analytical Inactivity > 270 Days (Not Observed Churn, D-6)", 93358, 36645, 39.25, 6050412.35, 165.11, "Recency > 270 days relative to 2018-10-17 dataset cutoff"),
        ("Analytical Inactivity > 365 Days (Not Observed Churn, D-6)", 93358, 20680, 22.15, 3389120.40, 163.88, "Recency > 365 days relative to 2018-10-17 dataset cutoff"),
    ]
    cust_df = pd.DataFrame(
        cust_rows,
        columns=[
            "Customer_Cohort_or_Rule",
            "Denominator_Customers",
            "Customer_Count",
            "Share_Pct",
            "Total_Order_Value_BRL",
            "Avg_Historical_CLV_BRL",
            "Governance_and_Analytical_Note",
        ],
    )
    _write_dataframe_table(
        ws_cust,
        cust_df,
        "tbl_CustomerAnalytics",
        start_row=4,
        currency_cols={"Total_Order_Value_BRL", "Avg_Historical_CLV_BRL"},
        pct_cols={"Share_Pct"},
        int_cols={"Denominator_Customers", "Customer_Count"},
    )

    # 5. RFM_Segmentation
    ws_rfm = wb.create_sheet("RFM_Segmentation")
    _style_sheet_banner(
        ws_rfm,
        "VALIDATED RFM CUSTOMER SEGMENTATION SUMMARY (93,358 DELIVERED CUSTOMERS)",
        "Exact Reconciled Segment Counts & Delivered Order Value Proxy (R$ 15,422,461.77 Total)",
    )
    rfm_df = pd.read_csv(SQL_OUT / "vw_rfm_segments_summary.csv").sort_values(
        "customer_count", ascending=False
    )
    end_rfm = _write_dataframe_table(
        ws_rfm,
        rfm_df,
        "tbl_RFMSegments",
        start_row=4,
        currency_cols={"avg_monetary_brl", "total_order_value_brl"},
        sum_pct_cols={"customer_share_pct", "revenue_share_pct"},
        int_cols={"customer_count"},
        add_totals_row=True,
    )
    chart_rfm = BarChart()
    chart_rfm.title = "Customer Count by RFM Segment"
    chart_rfm.y_axis.title = "Customers"
    chart_rfm.x_axis.title = "RFM Segment"
    chart_rfm.width = 16
    chart_rfm.height = 10
    chart_rfm.add_data(Reference(ws_rfm, min_col=2, min_row=4, max_row=end_rfm), titles_from_data=True)
    chart_rfm.set_categories(Reference(ws_rfm, min_col=1, min_row=5, max_row=end_rfm))
    ws_rfm.add_chart(chart_rfm, "J4")

    # 6. Cohort_Retention
    ws_coh = wb.create_sheet("Cohort_Retention")
    _style_sheet_banner(
        ws_coh,
        "MONTHLY ACQUISITION COHORT RETENTION MATRIX (M0 TO M12 %)",
        "Window: Jan 2017 – Aug 2018 (Rule D-2) | Customer Identity: customer_unique_id",
    )
    coh_df = pd.read_csv(SQL_OUT / "01_cohort_retention_analysis_result_2.csv")
    end_coh = _write_dataframe_table(
        ws_coh,
        coh_df,
        "tbl_CohortRetention",
        start_row=4,
        pct_cols={f"m{i}_pct" for i in range(0, 13)},
        int_cols={"cohort_size"},
        add_totals_row=True,
    )
    ws_coh.conditional_formatting.add(
        f"D5:O{end_coh}",
        ColorScaleRule(
            start_type="num",
            start_value=0.0,
            start_color="FFFFFF",
            mid_type="num",
            mid_value=0.35,
            mid_color="BFDBFE",
            end_type="num",
            end_value=0.75,
            end_color="1D4ED8",
        ),
    )

    # 7. Product_Seller_Performance
    ws_ps = wb.create_sheet("Product_Seller_Performance")
    _style_sheet_banner(
        ws_ps,
        "PRODUCT CATEGORY PERFORMANCE (74 CATEGORIES) & SELLER PARETO CONCENTRATION",
        "Rule D-1: Ranked by Delivered Item Merchandise Revenue SUM(price) = R$ 13,221,498.11 | Top 10% Sellers = 67.11% (R$ 8,873,076.37)",
    )
    cat_df = pd.read_csv(SQL_OUT / "02_product_and_category_performance_result_1.csv")
    _write_dataframe_table(
        ws_ps,
        cat_df,
        "tbl_ProductSellerPerf",
        start_row=4,
        currency_cols={
            "item_revenue_brl",
            "freight_value_brl",
            "total_item_gmv_brl",
            "avg_item_price_brl",
            "avg_freight_brl",
        },
        sum_pct_cols={"revenue_share_pct"},
        pct_cols={"cumulative_revenue_share_pct"},
        int_cols={
            "revenue_rank",
            "delivered_orders",
            "items_sold",
            "distinct_products",
            "distinct_sellers",
        },
        add_totals_row=True,
    )

    # 8. Delivery_Satisfaction
    ws_del = wb.create_sheet("Delivery_Satisfaction")
    _style_sheet_banner(
        ws_del,
        "DELIVERY TIMING BUCKETS VS CUSTOMER SATISFACTION & STATE LOGISTICS",
        "Primary Review Score: Most Recent Review per Order (Rule D-3) | On-Time 4.29 vs Late 2.57 Stars (-1.73 Drop, p < 0.0001)",
    )
    rev_df = pd.read_csv(SQL_OUT / "04_delivery_and_satisfaction_analysis_result_2.csv")
    _write_dataframe_table(
        ws_del,
        rev_df,
        "tbl_DeliverySatisfaction",
        start_row=4,
        currency_cols={"order_value_proxy_brl"},
        sum_pct_cols={"order_share_pct"},
        pct_cols={"one_star_share_pct", "five_star_share_pct"},
        int_cols={"delivered_orders"},
        add_totals_row=True,
    )

    # 9. Data_Quality
    ws_dq = wb.create_sheet("Data_Quality")
    _style_sheet_banner(
        ws_dq,
        "DATA QUALITY AUDIT, ANOMALY FLAGS & GOVERNANCE LOG",
        "Zero Silent Deletions Policy | All Raw Records Preserved & Flagged in data/processed/",
    )
    dq_rows = [
        ("DQ-01", "orders_clean", "flag_missing_delivery_date", 2965, 8, "Medium", "8 delivered orders + 2,957 non-delivered orders lack customer delivery timestamp", "Retained in delivered order count (96,478); excluded from delivery_days denominator (96,470)"),
        ("DQ-02", "order_level_analytics", "flag_missing_payment", 1, 1, "Low", "1 delivered order (bfbd0f9bdef84302105ad712db648a6c) has 0 payment rows (R$ 143.46 item price)", "Retained with payment_value = R$ 0.00 and flagged via flag_missing_payment"),
        ("DQ-03", "order_payments_clean", "flag_zero_payment_value", 9, 0, "Low", "6 voucher rows and 3 canceled not_defined rows have R$ 0.00 payment_value", "Flagged; 0 impact on delivered order value totals"),
        ("DQ-04", "order_items_clean", "flag_zero_freight", 383, 383, "Info", "383 order items have R$ 0.00 freight_value (free-shipping promotions)", "Valid promotional free shipping; retained and flagged"),
        ("DQ-05", "order_items_clean", "flag_shipping_limit_after_2018", 4, 4, "Low", "4 rows have shipping_limit_date in 2020 (2020-02 to 2020-04) while orders delivered in 2017/2018", "Flagged as seller deadline timestamp entry error; purchase & delivery dates valid"),
        ("DQ-06", "products_clean", "flag_missing_category", 610, 610, "Medium", "610 products have NULL product_category_name in raw products table", "Mapped to 'uncategorized' (R$ 175,952.71 delivered item revenue across 1,451 orders)"),
        ("DQ-07", "products_clean", "flag_manual_translation_d4", 15, 15, "Low", "2 Portuguese categories (pc_gamer, portateis_cozinha_e_preparadores_de_alimentos) missing in official translation CSV", "Mapped via approved Rule D-4 with translation_source = 'manual_project_mapping'"),
        ("DQ-08", "order_reviews_clean", "duplicate_review_id_and_multi_review_orders", 814, 547, "Medium", "99,224 raw review rows contain 98,410 unique review_ids across 98,673 orders (547 multi-review orders)", "Deduplicated to 1 row per order_id using latest review timestamp (Rule D-3); mean sensitivity = 4.16"),
        ("DQ-09", "geolocation_clean", "duplicate_zip_prefix_coordinates", 738332, 19015, "Low", "1,000,163 raw geolocation pings collapse to 19,015 unique zip_code_prefix centroids", "Aggregated to median lat/lng centroid per zip prefix with outlier coordinate bounding"),
    ]
    dq_df = pd.DataFrame(
        dq_rows,
        columns=[
            "Issue_ID",
            "Target_Table",
            "Quality_Flag_Column",
            "Total_Affected_Rows",
            "Delivered_Scope_Rows",
            "Severity",
            "Empirical_Description",
            "Approved_Governance_Treatment",
        ],
    )
    _write_dataframe_table(
        ws_dq,
        dq_df,
        "tbl_DataQuality",
        start_row=4,
        int_cols={"Total_Affected_Rows", "Delivered_Scope_Rows"},
    )

    # 10. Metric_Definitions
    ws_def = wb.create_sheet("Metric_Definitions")
    _style_sheet_banner(
        ws_def,
        "CENTRALISED KPI CATALOGUE & METRIC GOVERNANCE DEFINITIONS",
        "Source: src/analytics/metric_catalogue.py | 18 Enterprise KPIs Reconciled Across All Reporting Layers",
    )
    cat_list = get_metric_catalogue()
    def_rows = [
        (
            m["metric_id"],
            m["metric_name"],
            m["category"],
            m["formatted_value"],
            m["unit"],
            m["grain"],
            m["business_definition"],
            m["sql_formula"],
            m["filters"],
            m["known_limitations"],
        )
        for m in cat_list
    ]
    def_df = pd.DataFrame(
        def_rows,
        columns=[
            "Metric_ID",
            "Metric_Name",
            "Domain_Category",
            "Canonical_Value",
            "Unit",
            "Grain",
            "Business_Definition",
            "SQL_Formula",
            "Filters_and_Governance",
            "Known_Limitations",
        ],
    )
    _write_dataframe_table(ws_def, def_df, "tbl_MetricDefinitions", start_row=4)

    out_file = OUT_DIR / "Ecommerce_Revenue_Retention_Intelligence_Report.xlsx"
    wb.save(out_file)
    return out_file


if __name__ == "__main__":
    out = build_excel_report()
    print(f"Saved 10-sheet Excel executive report -> {out.relative_to(ROOT)} ({out.stat().st_size / 1024:.1f} KB)")
