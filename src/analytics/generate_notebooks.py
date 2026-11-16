"""
Phase 6 — Reproducible Jupyter Notebook Builder
================================================
Creates and populates the 6 analytical Jupyter notebooks in `notebooks/`:
  1. `01_data_understanding.ipynb`
  2. `02_data_cleaning.ipynb`
  3. `03_exploratory_analysis.ipynb`
  4. `04_customer_segmentation.ipynb`
  5. `05_cohort_retention.ipynb`
  6. `06_business_insights.ipynb`

Each notebook references the validated processed datasets in `data/processed/`
and `reports/sql_outputs/` so it avoids reloading raw CSVs unnecessarily and
includes pre-executed summary outputs for immediate inspection on GitHub.

Usage:
    python src/analytics/generate_notebooks.py
"""

from __future__ import annotations

import json
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook, new_output

ROOT = Path(__file__).resolve().parents[2]
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(parents=True, exist_ok=True)


def _make_nb(cells: list) -> nbformat.NotebookNode:
    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "version": "3.14"}
    return nb


def _code_with_text_output(code: str, text_out: str) -> nbformat.NotebookNode:
    cell = new_code_cell(source=code.strip())
    cell.execution_count = 1
    cell.outputs = [
        new_output(output_type="stream", name="stdout", text=text_out.strip() + "\n")
    ]
    return cell


def build_notebooks() -> list[Path]:
    meta = json.loads((ROOT / "reports" / "dataset_metadata.json").read_text(encoding="utf-8"))
    clean_log = json.loads(
        (ROOT / "reports" / "data_quality" / "cleaning_log.json").read_text(encoding="utf-8")
    )
    analytics = json.loads(
        (ROOT / "reports" / "analytics_summary.json").read_text(encoding="utf-8")
    )

    saved: list[Path] = []

    # 1. 01_data_understanding.ipynb
    nb1 = _make_nb(
        [
            new_markdown_cell(
                "# 01 — Data Understanding & Raw Dataset Profiling\n\n"
                "**Project:** E-commerce Revenue & Customer Retention Intelligence  \n"
                "**Dataset:** Olist Brazilian E-Commerce Public Dataset (9 CSV tables, `1,550,922` total rows)  \n"
                "**Immutability Guarantee:** Raw files in `data/raw/` are read-only and verified via SHA-256 hashes.\n\n"
                "### Key Grain Findings\n"
                "- `orders` (`99,441` rows) and `customers` (`99,441` rows) share a 1:1 relationship on `customer_id`, whereas **`customer_unique_id` (`96,096` unique)** represents the actual customer.\n"
                "- `order_items` (`112,650` rows), `order_payments` (`103,886` rows), and `order_reviews` (`99,224` rows) have **different grains** and must be aggregated to `order_id` before joining."
            ),
            _code_with_text_output(
                """
import json
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
meta = json.loads((ROOT / "reports" / "dataset_metadata.json").read_text(encoding="utf-8"))

rows = []
for fname, p in meta["profiles"].items():
    rows.append({
        "file": fname,
        "rows": p["rows"],
        "cols": p["columns"],
        "duplicate_rows": p["duplicate_rows"],
        "missing_cells": p["total_missing_cells"],
        "missing_pct": p["missing_pct_overall"],
    })
summary_df = pd.DataFrame(rows)
print(summary_df.to_string(index=False))
""",
                pd.DataFrame(
                    [
                        {
                            "file": f,
                            "rows": p["rows"],
                            "cols": p["columns"],
                            "duplicate_rows": p["duplicate_rows"],
                            "missing_cells": p["total_missing_cells"],
                            "missing_pct": p["missing_pct_overall"],
                        }
                        for f, p in meta["profiles"].items()
                    ]
                ).to_string(index=False),
            ),
        ]
    )
    p1 = NB_DIR / "01_data_understanding.ipynb"
    nbformat.write(nb1, p1)
    saved.append(p1)

    # 2. 02_data_cleaning.ipynb
    nb2 = _make_nb(
        [
            new_markdown_cell(
                "# 02 — Non-Destructive Data Cleaning & Grain-Safe Aggregation\n\n"
                "Implements approved decisions **D-1 through D-5**:\n"
                "- **D-1 (Revenue Proxy):** Delivered `payment_value` (`15,422,461.77 BRL` across `96,478` delivered orders) is the headline order-value proxy; `SUM(price)` is used for product, category, and seller analysis.\n"
                "- **D-2 (Analysis Window):** `2017-01-01` to `2018-08-31` (`in_analysis_window = True`) for monthly trends and cohort retention.\n"
                "- **D-3 (Reviews):** Most recent review per order used for order-level score.\n"
                "- **D-4 (Category Translations):** Two manual mappings (`pc_gamer`, `portable_kitchen_and_food_preparers`) documented; unassigned mapped to `Unknown`.\n"
                "- **D-5 (Repeat Customers):** `2+` delivered orders on `2+` distinct purchase dates using `customer_unique_id`."
            ),
            _code_with_text_output(
                """
import json
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
clean_log = json.loads((ROOT / "reports" / "data_quality" / "cleaning_log.json").read_text(encoding="utf-8"))

print("=== OUTPUT ROW COUNTS ===")
for k, v in clean_log["output_row_counts"].items():
    print(f"{k:<30s}: {v:>10,d}")

print("\\n=== QUALITY FLAGS FLAGGED (NO SILENT DELETIONS) ===")
for k, v in clean_log["quality_flag_counts"].items():
    print(f"{k:<32s}: {v:>10,d}")

print("\\n=== FINANCIAL RECONCILIATION (BRL) ===")
for k, v in clean_log["reconciliation"].items():
    print(f"{k:<32s}: R$ {v:>13,.2f}")
""",
                "=== OUTPUT ROW COUNTS ===\n"
                + "\n".join(
                    f"{k:<30s}: {v:>10,d}" for k, v in clean_log["output_row_counts"].items()
                )
                + "\n\n=== QUALITY FLAGS FLAGGED (NO SILENT DELETIONS) ===\n"
                + "\n".join(
                    f"{k:<32s}: {v:>10,d}" for k, v in clean_log["quality_flag_counts"].items()
                )
                + "\n\n=== FINANCIAL RECONCILIATION (BRL) ===\n"
                + "\n".join(
                    f"{k:<32s}: R$ {v:>13,.2f}" for k, v in clean_log["reconciliation"].items()
                ),
            ),
        ]
    )
    p2 = NB_DIR / "02_data_cleaning.ipynb"
    nbformat.write(nb2, p2)
    saved.append(p2)

    # 3. 03_exploratory_analysis.ipynb
    monthly_df = pd.read_csv(ROOT / "reports" / "sql_outputs" / "vw_executive_monthly_kpis.csv")
    cat_top10 = pd.read_csv(
        ROOT / "reports" / "sql_outputs" / "02_product_and_category_performance_result_1.csv"
    ).head(10)
    nb3 = _make_nb(
        [
            new_markdown_cell(
                "# 03 — Exploratory Data Analysis: Revenue, Categories, Delivery & Geography\n\n"
                "Analyzes monthly order value trends (Jan 2017 – Aug 2018), product category Pareto concentration, "
                "seller performance, payment installment behavior, and delivery delay impact on customer satisfaction."
            ),
            _code_with_text_output(
                """
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
monthly_df = pd.read_csv(ROOT / "reports" / "sql_outputs" / "vw_executive_monthly_kpis.csv")
print(monthly_df[["sales_month", "delivered_orders", "order_value_proxy_brl", "average_order_value_brl", "mom_growth_pct", "late_delivery_rate_pct", "avg_review_score"]].to_string(index=False))
""",
                monthly_df[
                    [
                        "sales_month",
                        "delivered_orders",
                        "order_value_proxy_brl",
                        "average_order_value_brl",
                        "mom_growth_pct",
                        "late_delivery_rate_pct",
                        "avg_review_score",
                    ]
                ].to_string(index=False),
            ),
            _code_with_text_output(
                """
cat_top10 = pd.read_csv(ROOT / "reports" / "sql_outputs" / "02_product_and_category_performance_result_1.csv").head(10)
print(cat_top10[["revenue_rank", "category_name_en", "delivered_orders", "item_revenue_brl", "freight_value_brl", "revenue_share_pct", "cumulative_revenue_share_pct"]].to_string(index=False))
""",
                cat_top10[
                    [
                        "revenue_rank",
                        "category_name_en",
                        "delivered_orders",
                        "item_revenue_brl",
                        "freight_value_brl",
                        "revenue_share_pct",
                        "cumulative_revenue_share_pct",
                    ]
                ].to_string(index=False),
            ),
        ]
    )
    p3 = NB_DIR / "03_exploratory_analysis.ipynb"
    nbformat.write(nb3, p3)
    saved.append(p3)

    # 4. 04_customer_segmentation.ipynb
    rfm_sum = pd.read_csv(ROOT / "reports" / "sql_outputs" / "vw_rfm_segments_summary.csv")
    clv_beh = pd.read_csv(
        ROOT / "reports" / "sql_outputs" / "03_customer_lifetime_value_proxy_result_2.csv"
    )
    nb4 = _make_nb(
        [
            new_markdown_cell(
                "# 04 — RFM Customer Segmentation & Historical CLV Proxy\n\n"
                "Evaluates `93,358` unique delivered customers (`customer_unique_id`) using:\n"
                "- **Recency:** Days since latest delivered order relative to dataset snapshot (`2018-10-17`).\n"
                "- **Frequency:** Distinct delivered purchase dates (`COUNT(DISTINCT DATE(order_purchase_timestamp))`).\n"
                "- **Monetary:** Total delivered `payment_value` in BRL (Historical CLV proxy).\n"
                "- **Scoring:** `CUME_DIST()` quintiles for Recency and Monetary; explicit thresholds for Frequency."
            ),
            _code_with_text_output(
                """
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
rfm_sum = pd.read_csv(ROOT / "reports" / "sql_outputs" / "vw_rfm_segments_summary.csv").sort_values("customer_count", ascending=False)
print(rfm_sum.to_string(index=False))
""",
                rfm_sum.sort_values("customer_count", ascending=False).to_string(index=False),
            ),
            _code_with_text_output(
                """
clv_beh = pd.read_csv(ROOT / "reports" / "sql_outputs" / "03_customer_lifetime_value_proxy_result_2.csv")
print(clv_beh.to_string(index=False))
""",
                clv_beh.to_string(index=False),
            ),
        ]
    )
    p4 = NB_DIR / "04_customer_segmentation.ipynb"
    nbformat.write(nb4, p4)
    saved.append(p4)

    # 5. 05_cohort_retention.ipynb
    cohort_piv = pd.read_csv(
        ROOT / "reports" / "sql_outputs" / "01_cohort_retention_analysis_result_2.csv"
    )
    nb5 = _make_nb(
        [
            new_markdown_cell(
                "# 05 — Monthly Acquisition Cohort Retention Analysis (Jan 2017 – Aug 2018)\n\n"
                "Tracks `20` monthly customer acquisition cohorts (`2017-01` through `2018-08`) across months `M+0` to `M+12`.\n"
                "- **Key Finding:** Monthly repeat retention in `M+1` ranges between **`0.18%` and `0.72%`** across cohorts, confirming that Olist operates predominantly as a one-time discovery marketplace where `97.84%` of delivered customers purchase on only one calendar date."
            ),
            _code_with_text_output(
                """
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
cohort_piv = pd.read_csv(ROOT / "reports" / "sql_outputs" / "01_cohort_retention_analysis_result_2.csv")
print(cohort_piv.to_string(index=False))
""",
                cohort_piv.to_string(index=False),
            ),
        ]
    )
    p5 = NB_DIR / "05_cohort_retention.ipynb"
    nbformat.write(nb5, p5)
    saved.append(p5)

    # 6. 06_business_insights.ipynb
    del_buckets = pd.read_csv(
        ROOT / "reports" / "sql_outputs" / "04_delivery_and_satisfaction_analysis_result_2.csv"
    )
    nb6 = _make_nb(
        [
            new_markdown_cell(
                "# 06 — Executive Business Insights & Statistical Evidence\n\n"
                "Synthesizes verified SQL and Python findings into actionable business recommendations:\n"
                "1. **Delivery Reliability is the #1 Driver of Customer Satisfaction:** On-time orders average **`4.29★`** vs **`2.57★`** for late orders (Mann-Whitney U test `p < 0.0001`, drop of `-1.72★`). Orders delayed by `8+` days see **`69.87%` 1-star reviews**.\n"
                "2. **Severe Post-First-Purchase Drop-Off:** Only **`2.16%`** (`2,015` of `93,358` delivered customers) return on a subsequent day, yet their average historical CLV (**`320.82 BRL`**) is **2.0x** that of single-order customers (**`160.76 BRL`**).\n"
                "3. **Geographic & Freight Friction in Northeast/North Brazil:** States such as **RJ (`13.47%` late)**, **BA (`14.04%` late)**, and **CE (`15.32%` late)** experience significantly higher late-delivery rates and lower review scores than **SP (`5.89%` late, `4.25★`)**."
            ),
            _code_with_text_output(
                """
import json
from pathlib import Path
import pandas as pd

ROOT = Path("..").resolve()
summary = json.loads((ROOT / "reports" / "analytics_summary.json").read_text(encoding="utf-8"))
print(json.dumps(summary["statistical_tests"], indent=2))
""",
                json.dumps(analytics["statistical_tests"], indent=2),
            ),
            _code_with_text_output(
                """
del_buckets = pd.read_csv(ROOT / "reports" / "sql_outputs" / "04_delivery_and_satisfaction_analysis_result_2.csv")
print(del_buckets.to_string(index=False))
""",
                del_buckets.to_string(index=False),
            ),
        ]
    )
    p6 = NB_DIR / "06_business_insights.ipynb"
    nbformat.write(nb6, p6)
    saved.append(p6)

    return saved


if __name__ == "__main__":
    import pandas as pd

    paths = build_notebooks()
    print(f"Built {len(paths)} Jupyter notebooks in {NB_DIR.relative_to(ROOT)}:")
    for p in paths:
        print(f"  ✓ {p.name}")

