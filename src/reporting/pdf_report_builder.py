"""
Executive PDF Business Report Builder
=====================================
Generates a 3-page enterprise PDF business report using matplotlib PdfPages:
  `reports/executive_summary/Ecommerce_Intelligence_OS_Executive_Report.pdf`
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SQL_OUT = ROOT / "reports" / "sql_outputs"
OUT_DIR = ROOT / "reports" / "executive_summary"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def build_pdf_report() -> Path:
    summary = json.loads((ROOT / "reports" / "analytics_summary.json").read_text(encoding="utf-8"))
    kf = summary["executive_kpis"]["full_dataset"]
    kw = summary["executive_kpis"]["analysis_window_2017_01_to_2018_08"]
    ret = summary["retention_metrics"]["full_dataset_delivered"]
    mw = summary["statistical_tests"]["on_time_vs_late_review_score_mann_whitney"]

    mon_df = pd.read_csv(SQL_OUT / "vw_executive_monthly_kpis.csv")
    rfm_df = pd.read_csv(SQL_OUT / "vw_rfm_segments_summary.csv").sort_values(
        "total_order_value_brl", ascending=True
    )
    cat_df = pd.read_csv(SQL_OUT / "02_product_and_category_performance_result_1.csv").head(10).sort_values(
        "item_revenue_brl", ascending=True
    )
    del_df = pd.read_csv(SQL_OUT / "04_delivery_and_satisfaction_analysis_result_2.csv")

    out_pdf = OUT_DIR / "Ecommerce_Intelligence_OS_Executive_Report.pdf"

    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#CBD5E1"
    plt.rcParams["axes.linewidth"] = 0.8

    with PdfPages(out_pdf) as pdf:
        # ---------------- PAGE 1: EXECUTIVE COVER & KPI SCORECARD ----------------
        fig1 = plt.figure(figsize=(11.69, 8.27), facecolor="#FFFFFF")
        ax1 = fig1.add_axes([0, 0, 1, 1])
        ax1.axis("off")

        # Top header bar
        ax1.add_patch(plt.Rectangle((0.04, 0.86), 0.92, 0.09, color="#0F172A", transform=ax1.transAxes))
        ax1.text(
            0.06,
            0.915,
            "E-COMMERCE INTELLIGENCE OS",
            fontsize=18,
            fontweight="bold",
            color="#FFFFFF",
            transform=ax1.transAxes,
        )
        ax1.text(
            0.06,
            0.88,
            "AI-Powered Business Intelligence & Decision Platform | Executive Report (Olist Brazilian E-Commerce, BRL / R$)",
            fontsize=10,
            color="#94A3B8",
            transform=ax1.transAxes,
        )

        # Executive Summary Narrative
        ax1.text(
            0.04,
            0.82,
            "1. EXECUTIVE BUSINESS SUMMARY & GOVERNANCE SCOPE",
            fontsize=12,
            fontweight="bold",
            color="#0F172A",
            transform=ax1.transAxes,
        )
        summary_text = (
            f"• Scope: 99,441 total orders (96,478 delivered, 97.02% completion) across 93,358 unique delivered customers (Sep 2016 – Oct 2018).\n"
            f"• Primary Trend Window (Rule D-2): Jan 2017 – Aug 2018 covers 96,211 delivered orders and R$ {kw['delivered_order_value_proxy_brl']:,.2f} Delivered Order Value Proxy.\n"
            f"• Financial Reconciliation (Rule D-1): Full-dataset Delivered Order Value Proxy = R$ {kf['delivered_order_value_proxy_brl']:,.2f} | "
            f"Item Merchandise Revenue = R$ {kf['delivered_item_revenue_brl']:,.2f} | Freight = R$ {kf['delivered_freight_value_brl']:,.2f}.\n"
            f"• Retention Bottleneck (Rule D-5): True multi-day repeat purchase rate is {ret['repeat_rate_d5_pct']}% (2,015 customers), yet repeaters generate 2.0x CLV (R$ 320.82 vs R$ 160.76).\n"
            f"• Logistics Satisfaction Cliff: 8.11% late deliveries suffer a -1.73 star review drop (4.29 on-time vs 2.57 late; Mann-Whitney U p < 0.0001)."
        )
        ax1.text(
            0.04,
            0.66,
            summary_text,
            fontsize=9.5,
            color="#1E293B",
            linespacing=1.55,
            transform=ax1.transAxes,
        )

        # Canonical KPI Table
        ax1.text(
            0.04,
            0.61,
            "2. CANONICAL RECONCILED KPI SCORECARD (SQL = PYTHON = EXCEL = STREAMLIT = POWER BI)",
            fontsize=12,
            fontweight="bold",
            color="#0F172A",
            transform=ax1.transAxes,
        )
        table_data = [
            ["KPI ID", "Metric Name", "Full Dataset Value", "Jan 17–Aug 18 Window", "Governance Rule / Note"],
            ["KPI-001", "Total Orders (All Statuses)", f"{kf['total_orders_all_statuses']:,}", f"{kw['total_orders_all_statuses']:,}", "8 order statuses"],
            ["KPI-002", "Delivered Orders", f"{kf['delivered_orders']:,} (97.02%)", f"{kw['delivered_orders']:,}", "order_status = 'delivered'"],
            ["KPI-004", "Delivered Order Value Proxy", f"R$ {kf['delivered_order_value_proxy_brl']:,.2f}", f"R$ {kw['delivered_order_value_proxy_brl']:,.2f}", "Rule D-1: SUM(payment_value)"],
            ["KPI-005", "Delivered Item Revenue", f"R$ {kf['delivered_item_revenue_brl']:,.2f}", f"R$ {kw['delivered_item_revenue_brl']:,.2f}", "Rule D-1: SUM(price)"],
            ["KPI-006", "Delivered Freight Value", f"R$ {kf['delivered_freight_value_brl']:,.2f}", f"R$ {kw['delivered_freight_value_brl']:,.2f}", "Rule D-1: SUM(freight_value)"],
            ["KPI-008", "Mean / Median Order Value", f"R$ {kf['average_order_value_proxy_brl']:,.2f} / R$ {kf['median_order_value_proxy_brl']:,.2f}", f"R$ {kw['average_order_value_brl'] if 'average_order_value_brl' in kw else kw['average_order_value_proxy_brl']:,.2f}", "IQR: R$ 114.45"],
            ["KPI-010", "Unique Delivered Customers", f"{kf['unique_delivered_customers']:,}", f"{kw['unique_delivered_customers']:,}", "customer_unique_id (96,096 all)"],
            ["KPI-011", "True Repeat Rate (Rule D-5)", f"{ret['repeat_rate_d5_pct']}% (2,015)", "2.15% (2,005)", "2+ delivered orders on 2+ dates"],
            ["KPI-013", "Avg / Median Delivery Days", f"{kf['avg_delivery_days']:.2f}d / {kf['median_delivery_days']:.2f}d", "12.50d", "96,470 delivered with date"],
            ["KPI-014", "Late Delivery Rate", f"{kf['late_delivery_rate_timestamp_pct']}% (7,826)", "8.12%", "Calendar-day strict: 6.77%"],
            ["KPI-015", "Avg Review Score (Delivered)", f"{kf['avg_review_score_delivered']:.2f} / 5.00", "4.16 / 5.00", f"On-time {mw['on_time_mean_score']:.2f} vs Late {mw['late_mean_score']:.2f}"],
            ["KPI-018", "Top 10% Seller Revenue Share", "67.11% (R$ 8,873,076.37)", "—", "Top 297 of 2,970 active sellers"],
        ]

        tbl_ax = fig1.add_axes([0.04, 0.06, 0.92, 0.52])
        tbl_ax.axis("off")
        tbl = tbl_ax.table(
            cellText=table_data[1:],
            colLabels=table_data[0],
            loc="center",
            cellLoc="left",
            colWidths=[0.09, 0.27, 0.22, 0.18, 0.24],
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8.8)
        tbl.scale(1, 1.48)
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor("#CBD5E1")
            if row == 0:
                cell.set_facecolor("#0F172A")
                cell.set_text_props(color="#FFFFFF", fontweight="bold")
            elif row % 2 == 0:
                cell.set_facecolor("#F8FAFC")
            else:
                cell.set_facecolor("#FFFFFF")

        pdf.savefig(fig1)
        plt.close(fig1)

        # ---------------- PAGE 2: REVENUE TRENDS & RFM SEGMENTATION ----------------
        fig2 = plt.figure(figsize=(11.69, 8.27), facecolor="#FFFFFF")
        fig2.suptitle(
            "E-COMMERCE INTELLIGENCE OS — REVENUE TRAJECTORY & RFM SEGMENTATION",
            fontsize=14,
            fontweight="bold",
            color="#0F172A",
            y=0.96,
        )

        ax_rev = fig2.add_axes([0.07, 0.54, 0.88, 0.35])
        ax_rev.plot(
            mon_df["sales_month"],
            mon_df["order_value_proxy_brl"] / 1e6,
            marker="o",
            color="#2563EB",
            linewidth=2.2,
            label="Delivered Order Value Proxy (R$ Millions)",
        )
        ax_rev.plot(
            mon_df["sales_month"],
            mon_df["item_revenue_brl"] / 1e6,
            marker="s",
            color="#0D9488",
            linewidth=1.8,
            linestyle="--",
            label="Delivered Item Revenue SUM(price) (R$ Millions)",
        )
        ax_rev.set_title("Monthly Delivered Order Value Proxy vs Item Revenue (Jan 2017 – Aug 2018)", fontsize=11, fontweight="bold", color="#0F172A")
        ax_rev.set_ylabel("BRL (R$ Millions)", fontsize=9.5)
        ax_rev.tick_params(axis="x", rotation=45, labelsize=8.5)
        ax_rev.grid(True, linestyle=":", alpha=0.5, color="#CBD5E1")
        ax_rev.legend(loc="upper left", frameon=True, fontsize=8.5)

        ax_rfm = fig2.add_axes([0.20, 0.09, 0.75, 0.34])
        bars = ax_rfm.barh(
            rfm_df["customer_segment"],
            rfm_df["total_order_value_brl"] / 1e6,
            color="#1E40AF",
            height=0.62,
        )
        ax_rfm.set_title("Delivered Order Value Proxy by Validated RFM Customer Segment (R$ Millions)", fontsize=11, fontweight="bold", color="#0F172A")
        ax_rfm.set_xlabel("Total Order Value Proxy (R$ Millions)", fontsize=9.5)
        ax_rfm.grid(True, axis="x", linestyle=":", alpha=0.5, color="#CBD5E1")
        for bar, (_, r) in zip(bars, rfm_df.iterrows()):
            ax_rfm.text(
                bar.get_width() + 0.08,
                bar.get_y() + bar.get_height() / 2,
                f"R$ {r['total_order_value_brl']:,.0f} ({int(r['customer_count']):,} cust | {r['revenue_share_pct']:.1f}%)",
                va="center",
                fontsize=8,
                color="#0F172A",
            )
        ax_rfm.set_xlim(0, 8.2)

        pdf.savefig(fig2)
        plt.close(fig2)

        # ---------------- PAGE 3: CATEGORIES, LOGISTICS & DECISION PLAYBOOK ----------------
        fig3 = plt.figure(figsize=(11.69, 8.27), facecolor="#FFFFFF")
        fig3.suptitle(
            "E-COMMERCE INTELLIGENCE OS — CATEGORY DRIVERS, SLA IMPACT & DECISION PLAYBOOK",
            fontsize=14,
            fontweight="bold",
            color="#0F172A",
            y=0.96,
        )

        ax_cat = fig3.add_axes([0.18, 0.55, 0.34, 0.34])
        cat_col = "category_name_en" if "category_name_en" in cat_df.columns else "category_english"
        ax_cat.barh(cat_df[cat_col], cat_df["item_revenue_brl"] / 1e6, color="#0284C7")
        ax_cat.set_title("Top 10 Categories by Item Revenue (R$ M)", fontsize=10.5, fontweight="bold", color="#0F172A")
        ax_cat.set_xlabel("Item Revenue (R$ Millions)", fontsize=8.5)
        ax_cat.tick_params(labelsize=8)
        ax_cat.grid(True, axis="x", linestyle=":", alpha=0.5)

        ax_del = fig3.add_axes([0.62, 0.55, 0.33, 0.34])
        short_labels = [b.split("(")[0].strip() for b in del_df["delivery_timing_bucket"]]
        colors_del = ["#16A34A", "#22C55E", "#65A30D", "#F59E0B", "#EA580C", "#DC2626"]
        ax_del.bar(short_labels, del_df["avg_review_score"], color=colors_del[: len(del_df)])
        ax_del.set_title("Avg Review Score by Delivery Timing Bucket", fontsize=10.5, fontweight="bold", color="#0F172A")
        ax_del.set_ylabel("Mean Review Stars (1–5)", fontsize=8.5)
        ax_del.set_ylim(0, 5.0)
        ax_del.tick_params(axis="x", rotation=28, labelsize=7.5)
        ax_del.grid(True, axis="y", linestyle=":", alpha=0.5)

        ax_dec = fig3.add_axes([0.05, 0.05, 0.90, 0.38])
        ax_dec.axis("off")
        ax_dec.text(
            0.0,
            0.94,
            "3. EVIDENCE-BACKED EXECUTIVE DECISION PLAYBOOK",
            fontsize=11.5,
            fontweight="bold",
            color="#0F172A",
            transform=ax_dec.transAxes,
        )
        playbook_text = (
            "1. SECOND-PURCHASE RETENTION AUTOMATION (Target: 37,219 'Recent Customers' = R$ 6.27M + 18,272 'Needs Attention' = R$ 2.80M)\n"
            "   • Evidence: True multi-day repeat rate is 2.16% (2,015 customers), yet repeaters spend R$ 320.82 vs R$ 160.76 (2.0x multiplier).\n"
            "   • Action & Impact: Trigger 30-day category replenishment vouchers; lifting repeat rate to 3.5%–4.0% adds +R$ 200K to +R$ 275K order value.\n\n"
            "2. CORRIDOR-SPECIFIC EDD BUFFERING & PROACTIVE DELAY ALERTS (Target: 7,826 Late Orders = 8.11% Late Rate)\n"
            "   • Evidence: Late delivery causes a -1.73 star drop (4.29 -> 2.57 stars, p < 0.0001); 8+ days late (2,862 orders) hits 69.87% 1-star share.\n"
            "   • Action & Impact: Recalibrate EDD promises on SP->RJ (13.47% late) & SP->BA/CE/AL corridors; cutting late rate by 50% prevents ~1,400+ 1-star reviews.\n\n"
            "3. TOP-DECILE SELLER KEY-ACCOUNT SLA GOVERNANCE (Target: Top 297 Sellers = 67.11% / R$ 8,873,076.37 of Merchandise Revenue)\n"
            "   • Evidence: Decile 1 (297 of 2,970 active sellers) drives 67.11% of item revenue; Deciles 1–2 (594 sellers) drive 82.29% (R$ 10.88M).\n"
            "   • Action & Impact: Pair VIP account retention incentives with strict dispatch SLA monitoring to safeguard core marketplace supply."
        )
        ax_dec.text(
            0.0,
            0.08,
            playbook_text,
            fontsize=8.8,
            color="#1E293B",
            linespacing=1.45,
            transform=ax_dec.transAxes,
        )

        pdf.savefig(fig3)
        plt.close(fig3)

    return out_pdf


if __name__ == "__main__":
    p = build_pdf_report()
    print(f"Saved PDF executive report -> {p.relative_to(ROOT)} ({p.stat().st_size / 1024:.1f} KB)")
