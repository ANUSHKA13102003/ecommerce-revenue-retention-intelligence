"""
Phase 6 — Reproducible Executive Chart Generator
=================================================
Generates 8 high-resolution charts in `reports/charts/` from the
validated analytical outputs. All charts include clear titles,
axis labels, BRL units, legends, and data source notes.

Usage:
    python src/analytics/chart_generator.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
SQL_OUT = ROOT / "reports" / "sql_outputs"
CHARTS_DIR = ROOT / "reports" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 180,
        "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)

SOURCE_NOTE = (
    "Source: Olist Brazilian E-Commerce Dataset (ecommerce_analytics) | "
    "Currency: BRL | Validated Pipeline Output"
)


def _add_footer(fig: plt.Figure, extra: str = "") -> None:
    note = f"{SOURCE_NOTE}  {extra}".strip()
    fig.text(0.01, 0.005, note, fontsize=8, color="#555555", style="italic")


def generate_all_charts() -> list[Path]:
    saved: list[Path] = []

    # 1. Monthly Revenue Proxy & Delivered Orders Trend (Jan 2017 - Aug 2018)
    m_df = pd.read_csv(SQL_OUT / "vw_executive_monthly_kpis.csv").sort_values("sales_month")
    fig, ax1 = plt.subplots(figsize=(12, 5.5))
    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)

    bars = ax1.bar(
        m_df["sales_month"],
        m_df["order_value_proxy_brl"] / 1e6,
        color="#1f77b4",
        alpha=0.82,
        label="Delivered Order Value Proxy (Million BRL)",
    )
    ax2.plot(
        m_df["sales_month"],
        m_df["delivered_orders"],
        color="#d62728",
        marker="o",
        linewidth=2.3,
        label="Delivered Orders Count",
    )
    ax1.set_title(
        "Monthly Delivered Order Value Proxy (BRL) & Order Volume (Jan 2017 – Aug 2018)",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax1.set_xlabel("Purchase Month (YYYY-MM)", fontsize=10)
    ax1.set_ylabel("Delivered Order Value Proxy (Million BRL)", fontsize=10, color="#1f77b4")
    ax2.set_ylabel("Delivered Orders", fontsize=10, color="#d62728")
    ax1.tick_params(axis="x", rotation=45)
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("R$ %.2fM"))
    ax2.yaxis.set_major_formatter(mticker.StrMethodFormatter("{x:,.0f}"))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=True)
    _add_footer(fig, "| Window: D-2 Approved (2017-01 to 2018-08)")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p1 = CHARTS_DIR / "01_monthly_revenue_and_orders_trend.png"
    fig.savefig(p1)
    plt.close(fig)
    saved.append(p1)

    # 2. Top 15 Product Categories by Delivered Item Revenue (BRL)
    c_df = (
        pd.read_csv(SQL_OUT / "02_product_and_category_performance_result_1.csv")
        .sort_values("item_revenue_brl", ascending=False)
        .head(15)
        .iloc[::-1]
    )
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    bars = ax.barh(
        c_df["category_name_en"],
        c_df["item_revenue_brl"] / 1e3,
        color="#2b5c8f",
        alpha=0.9,
    )
    for bar, share in zip(bars, c_df["revenue_share_pct"]):
        ax.text(
            bar.get_width() + 12,
            bar.get_y() + bar.get_height() / 2,
            f"R$ {bar.get_width():,.0f}K ({share:.1f}%)",
            va="center",
            fontsize=8.5,
        )
    ax.set_xlim(0, (c_df["item_revenue_brl"].max() / 1e3) * 1.22)
    ax.set_title(
        "Top 15 Product Categories by Delivered Item Revenue — SUM(price) in BRL",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Delivered Item Revenue (Thousand BRL)", fontsize=10)
    ax.set_ylabel("Product Category (English)", fontsize=10)
    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("R$ %.0fK"))
    _add_footer(fig, "| Rule D-1: Category analysis uses item price (excludes freight)")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p2 = CHARTS_DIR / "02_top_15_product_categories_revenue.png"
    fig.savefig(p2)
    plt.close(fig)
    saved.append(p2)

    # 3. RFM Customer Segmentation Distribution (93,358 Delivered Customers)
    rfm_df = pd.read_csv(SQL_OUT / "vw_rfm_segments_summary.csv").sort_values(
        "customer_count", ascending=True
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    colors = sns.color_palette("Blues_r", len(rfm_df))[::-1]
    b1 = ax1.barh(rfm_df["customer_segment"], rfm_df["customer_count"], color=colors)
    for bar, pct in zip(b1, rfm_df["customer_share_pct"]):
        ax1.text(
            bar.get_width() + 500,
            bar.get_y() + bar.get_height() / 2,
            f"{int(bar.get_width()):,} ({pct:.2f}%)",
            va="center",
            fontsize=8.5,
        )
    ax1.set_xlim(0, rfm_df["customer_count"].max() * 1.28)
    ax1.set_title("Customer Count by RFM Segment (N = 93,358)", fontsize=11.5, fontweight="bold")
    ax1.set_xlabel("Unique Delivered Customers", fontsize=10)

    b2 = ax2.barh(
        rfm_df["customer_segment"],
        rfm_df["total_order_value_brl"] / 1e6,
        color="#2ca02c",
        alpha=0.85,
    )
    for bar, pct in zip(b2, rfm_df["revenue_share_pct"]):
        ax2.text(
            bar.get_width() + 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"R$ {bar.get_width():.2f}M ({pct:.2f}%)",
            va="center",
            fontsize=8.5,
        )
    ax2.set_xlim(0, (rfm_df["total_order_value_brl"].max() / 1e6) * 1.32)
    ax2.set_title("Order Value Proxy (Million BRL) by RFM Segment", fontsize=11.5, fontweight="bold")
    ax2.set_xlabel("Delivered Order Value Proxy (Million BRL)", fontsize=10)
    fig.suptitle(
        "Validated RFM Customer Segmentation — Volume vs Monetary Contribution",
        fontsize=13,
        fontweight="bold",
    )
    _add_footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    p3 = CHARTS_DIR / "03_rfm_customer_segments_distribution.png"
    fig.savefig(p3)
    plt.close(fig)
    saved.append(p3)

    # 4. Monthly Acquisition Cohort Retention Heatmap (M1 to M12 %)
    coh_df = pd.read_csv(SQL_OUT / "01_cohort_retention_analysis_result_2.csv")
    coh_cols = [f"m{i}_pct" for i in range(1, 13)]
    heat_data = coh_df.set_index("cohort_month")[coh_cols].copy()
    heat_data.columns = [f"M+{i}" for i in range(1, 13)]
    # Mask structural right-censored zeros at bottom-right triangle
    n_cohorts = len(heat_data)
    mask = np.zeros_like(heat_data.values, dtype=bool)
    for r_idx in range(n_cohorts):
        for c_idx in range(12):
            if r_idx + (c_idx + 1) >= n_cohorts:
                mask[r_idx, c_idx] = True

    fig, ax = plt.subplots(figsize=(12, 7.5))
    sns.heatmap(
        heat_data,
        mask=mask,
        annot=True,
        fmt=".2f",
        cmap="YlGnBu",
        cbar_kws={"label": "Monthly Repeat Retention Rate (%)"},
        ax=ax,
        linewidths=0.4,
    )
    ax.set_title(
        "Monthly Acquisition Cohort Retention Rate (%) — Months M+1 through M+12 (Jan 2017 – Aug 2018)",
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Months Since First Delivered Purchase (M+1 to M+12)", fontsize=10)
    ax.set_ylabel("Acquisition Cohort Month (YYYY-MM)", fontsize=10)
    _add_footer(fig, "| Blank cells in lower-right triangle are right-censored (beyond Aug 2018)")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p4 = CHARTS_DIR / "04_cohort_retention_heatmap.png"
    fig.savefig(p4)
    plt.close(fig)
    saved.append(p4)

    # 5. Delivery Delay Timing Buckets vs Review Score & 1-Star / 5-Star Share
    del_df = pd.read_csv(SQL_OUT / "04_delivery_and_satisfaction_analysis_result_2.csv")
    fig, ax1 = plt.subplots(figsize=(11.5, 5.5))
    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)

    x = np.arange(len(del_df))
    w = 0.35
    ax1.bar(
        x - w / 2,
        del_df["five_star_share_pct"],
        width=w,
        color="#2ca02c",
        alpha=0.85,
        label="5-Star Review Share (%)",
    )
    ax1.bar(
        x + w / 2,
        del_df["one_star_share_pct"],
        width=w,
        color="#d62728",
        alpha=0.85,
        label="1-Star Review Share (%)",
    )
    ax2.plot(
        x,
        del_df["avg_review_score"],
        color="#1f2937",
        marker="s",
        linewidth=2.5,
        label="Average Review Score (1–5)",
    )
    for xi, score in zip(x, del_df["avg_review_score"]):
        ax2.annotate(
            f"{score:.2f} / 5",
            (xi, score),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontweight="bold",
            fontsize=9,
        )

    ax1.set_xticks(x)
    ax1.set_xticklabels(del_df["delivery_timing_bucket"], rotation=20, ha="right")
    ax1.set_ylabel("Share of Reviewed Orders (%)", fontsize=10)
    ax2.set_ylabel("Average Review Score (Stars)", fontsize=10)
    ax2.set_ylim(1.0, 5.0)
    ax1.set_title(
        "Impact of Delivery Timing vs Estimated Date on Customer Review Scores",
        fontsize=13,
        fontweight="bold",
        pad=12,
    )
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="center left", frameon=True)
    _add_footer(fig, "| Mann-Whitney U p < 0.0001 (On-Time 4.29 vs Late 2.57)")
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p5 = CHARTS_DIR / "05_delivery_delay_vs_review_score.png"
    fig.savefig(p5)
    plt.close(fig)
    saved.append(p5)

    # 6. Top 15 Brazilian States by Order Value Proxy vs Late Delivery Rate %
    st_df = (
        pd.read_csv(SQL_OUT / "vw_delivery_and_reviews_by_state.csv")
        .sort_values("order_value_proxy_brl", ascending=False)
        .head(15)
    )
    fig, ax1 = plt.subplots(figsize=(11.5, 5.5))
    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)

    ax1.bar(
        st_df["customer_state"],
        st_df["order_value_proxy_brl"] / 1e6,
        color="#3b82f6",
        alpha=0.85,
        label="Order Value Proxy (Million BRL)",
    )
    ax2.plot(
        st_df["customer_state"],
        st_df["late_delivery_rate_pct"],
        color="#e11d48",
        marker="o",
        linewidth=2.2,
        label="Late Delivery Rate (%)",
    )
    ax1.set_title(
        "Top 15 Customer States by Delivered Order Value Proxy (BRL) & Late Delivery Rate (%)",
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax1.set_xlabel("Customer State (UF)", fontsize=10)
    ax1.set_ylabel("Delivered Order Value Proxy (Million BRL)", fontsize=10, color="#3b82f6")
    ax2.set_ylabel("Late Delivery Rate (%)", fontsize=10, color="#e11d48")
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="upper right", frameon=True)
    _add_footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p6 = CHARTS_DIR / "06_state_revenue_and_late_delivery.png"
    fig.savefig(p6)
    plt.close(fig)
    saved.append(p6)

    # 7. Payment Methods & Credit Card Installment Tiers
    pay_df = pd.read_csv(SQL_OUT / "05_payment_and_installment_analysis_result_1.csv")
    inst_df = pd.read_csv(SQL_OUT / "05_payment_and_installment_analysis_result_2.csv")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2))
    ax1.bar(
        pay_df["payment_type"],
        pay_df["total_payment_value_brl"] / 1e6,
        color=["#1d4ed8", "#0284c7", "#0d9488", "#64748b"],
    )
    for idx, row in pay_df.iterrows():
        ax1.text(
            idx,
            row["total_payment_value_brl"] / 1e6 + 0.25,
            f"R$ {row['total_payment_value_brl']/1e6:.2f}M\n({row['share_of_payment_value_pct']:.1f}%)",
            ha="center",
            fontsize=8.5,
        )
    ax1.set_ylim(0, (pay_df["total_payment_value_brl"].max() / 1e6) * 1.22)
    ax1.set_title("Delivered Payment Value by Method (Million BRL)", fontsize=11.5, fontweight="bold")
    ax1.set_ylabel("Payment Value (Million BRL)", fontsize=10)

    ax2.barh(
        inst_df["installment_tier"],
        inst_df["avg_payment_value_brl"],
        color="#7c3aed",
        alpha=0.85,
    )
    for i, row in inst_df.iterrows():
        ax2.text(
            row["avg_payment_value_brl"] + 5,
            i,
            f"R$ {row['avg_payment_value_brl']:.2f} ({row['share_of_cc_value_pct']:.1f}% val)",
            va="center",
            fontsize=8.5,
        )
    ax2.set_xlim(0, inst_df["avg_payment_value_brl"].max() * 1.32)
    ax2.set_title("Credit Card Avg Payment Value by Installment Tier (BRL)", fontsize=11.5, fontweight="bold")
    ax2.set_xlabel("Average Payment Value (BRL)", fontsize=10)
    fig.suptitle("Payment Method Mix & Credit Card Installment Behaviour", fontsize=13, fontweight="bold")
    _add_footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    p7 = CHARTS_DIR / "07_payment_methods_and_installments.png"
    fig.savefig(p7)
    plt.close(fig)
    saved.append(p7)

    # 8. Seller Revenue Concentration by Decile (Pareto)
    sel_dec = pd.read_csv(SQL_OUT / "03_seller_performance_analysis_result_2.csv").sort_values(
        "revenue_decile"
    )
    sel_dec["cum_share_pct"] = sel_dec["share_of_total_item_revenue_pct"].cumsum()
    fig, ax1 = plt.subplots(figsize=(10.5, 5.2))
    ax2 = ax1.twinx()
    ax2.spines["top"].set_visible(False)
    ax2.grid(False)

    labels = [f"D{int(d)}" for d in sel_dec["revenue_decile"]]
    ax1.bar(
        labels,
        sel_dec["share_of_total_item_revenue_pct"],
        color="#0f766e",
        alpha=0.85,
        label="Decile Share of Item Revenue (%)",
    )
    ax2.plot(
        labels,
        sel_dec["cum_share_pct"],
        color="#b45309",
        marker="o",
        linewidth=2.4,
        label="Cumulative Share of Item Revenue (%)",
    )
    ax1.set_title(
        "Seller Revenue Concentration Across Deciles (2,970 Active Delivered Sellers)",
        fontsize=12.5,
        fontweight="bold",
        pad=12,
    )
    ax1.set_xlabel("Seller Revenue Decile (D1 = Top 10% Sellers)", fontsize=10)
    ax1.set_ylabel("Decile Share of Item Revenue (%)", fontsize=10, color="#0f766e")
    ax2.set_ylabel("Cumulative Revenue Share (%)", fontsize=10, color="#b45309")
    ax2.set_ylim(0, 105)
    l1, lb1 = ax1.get_legend_handles_labels()
    l2, lb2 = ax2.get_legend_handles_labels()
    ax1.legend(l1 + l2, lb1 + lb2, loc="center right", frameon=True)
    _add_footer(fig)
    fig.tight_layout(rect=[0, 0.03, 1, 1])
    p8 = CHARTS_DIR / "08_seller_pareto_concentration.png"
    fig.savefig(p8)
    plt.close(fig)
    saved.append(p8)

    return saved


if __name__ == "__main__":
    paths = generate_all_charts()
    print(f"Generated {len(paths)} charts in {CHARTS_DIR.relative_to(ROOT)}:")
    for p in paths:
        print(f"  ✓ {p.name} ({p.stat().st_size / 1024:.1f} KB)")
