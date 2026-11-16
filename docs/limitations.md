# Analytical, Data & Technical Limitations

A core requirement of senior analytics engineering is distinguishing between **what the data proves** and **what the data cannot prove**. All reports, notebooks, dashboards, and AI agent outputs explicitly disclose the following limitations:

---

## 1. Data & Domain Limitations

1. **Historical Time Window (`Sept 2016 – Oct 2018`):**
   - The public Olist dataset covers orders placed between `2016-09-04` and `2018-10-17`, with complete monthly coverage from **January 2017 through August 2018** (`20` months, Rule D-2).
   - Boundary months (`Sept–Dec 2016` with `267` delivered orders, and `Sept–Oct 2018` with `0` delivered orders and `20` canceled/shipped rows) are excluded from time-series and cohort trends to prevent right-censoring distortion.
   - Structural Brazilian market shifts post-2018 (such as the introduction of **PIX** instant payments in late 2020 and post-2020 logistics consolidation) are outside this historical window.

2. **Delivered Order Value Proxy vs. Net Marketplace Revenue (Rule D-1):**
   - `payment_value` (`R$ 15,422,461.77` on delivered orders) represents the **total amount paid by the customer** (`item price + shipping freight + credit card installment interest`).
   - It is **not** Olist's net corporate commission/take-rate revenue, which is proprietary and undisclosed in the public dataset.

3. **Lack of Product Cost / Margin Data:**
   - The dataset provides item selling price (`price`) and shipping fee (`freight_value`), but does not include seller Cost of Goods Sold (COGS), marketing acquisition cost (CAC), or return/refund processing costs. Therefore, profitability and net margin cannot be calculated directly.

---

## 2. Customer Retention & Modeling Limitations

1. **Right-Censored Repeat Purchase Window:**
   - Customers acquired in mid-2018 (`2018-06` to `2018-08`) have only `0–2` months of follow-up observation before the dataset ends. Their long-term repeat rate (`M+6`, `M+12`) is unobserved.
2. **Non-Contractual Inactivity vs. Observed Churn (Rule D-6):**
   - Because an e-commerce marketplace has no subscription contract, a customer with `recency_days > 180` or `> 365` is **inactive**, not provably "churned." All recency thresholds (`90/180/270/365` days) and RFM segment names (`At Risk`, `Lost Customers`) are analytical heuristics.
3. **Historical CLV Proxy vs. Predictive CLV:**
   - Customer Lifetime Value in this project (`R$ 320.82` for repeat buyers vs. `R$ 160.76` for one-time buyers) is a **historical cumulative order value proxy** (`SUM(payment_value)`), not a probabilistic forward-looking BG/NBD + Gamma-Gamma projection.

---

## 3. Technical & BI Delivery Notes

1. **Power BI `.pbix` Binary & Dataset Licence Attribution:**
   - The compiled Power BI Desktop workbook (`powerbi/Ecommerce_Intelligence_OS.pbix`, `34.89 MB`, saved and reopened cleanly with populated VertiPaq `DataModel` and 5 PBIR report pages) alongside its `.pbip` source (`19` tables, `10` single-direction relationships, `39` weighted DAX measures, synced dropdown slicers) is included for recruiter evaluation alongside the live **8-page Streamlit web dashboard** (`app/streamlit_app.py`), **10-sheet Executive Excel Workbook**, and **3-page Executive PDF Report**.
   - Because the `.pbix` `DataModel` embeds cleaned Olist-derived tables (`data/processed/` & `powerbi/data_exports/`), those data artifacts and `.pbix` are shared strictly for non-commercial portfolio demonstration with attribution under **CC BY-NC-SA 4.0**, while authored source code, SQL, DAX, and documentation are licensed under **MIT**.
2. **Observational Analysis (Correlation ≠ Causation) & Portfolio Scope:**
   - Statistical tests (`Mann-Whitney U` and `Welch's t`, $p < 0.0001$) demonstrate strong association between late delivery and lower review scores (`-1.72 ★`), not controlled causal proof. This platform is an end-to-end portfolio demonstration, not a deployed multi-tenant production SaaS product.
