# Cross-Platform KPI Reconciliation Report

**Generated At:** `2026-11-16T17:23:33.327921`  
**Overall Status:** **PASS (100% Reconciled)** (`18/18` KPIs Verified Across 5 Layers)  
**Layers Audited:** `SQL / Database` | `Python (kpi_engine)` | `Excel (10-Sheet Workbook)` | `Streamlit UI` | `Power BI Exports`

| KPI ID | Metric Name | Canonical Value | SQL Layer | Python Layer | Excel Layer | Streamlit Layer | Power BI Layer | Max Diff | Status |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `KPI-001` | **Total Orders (All Statuses)** | `99,441` | `99441` | `99441` | `99441` | `99441` | `99441` | `0.0` | **PASS** |
| `KPI-002` | **Delivered Orders** | `96,478` | `96478` | `96478` | `96478` | `96478` | `96478` | `0.0` | **PASS** |
| `KPI-003` | **Delivery Completion Rate** | `97.02%` | `97.02` | `97.02` | `97.02` | `97.02` | `97.02` | `0.0` | **PASS** |
| `KPI-004` | **Delivered Order Value (Revenue Proxy)** | `R$ 15,422,461.77` | `15422461.77` | `15422461.77` | `15422461.77` | `15422461.77` | `15422461.77` | `0.0` | **PASS** |
| `KPI-005` | **Delivered Item Merchandise Revenue** | `R$ 13,221,498.11` | `13221498.11` | `13221498.11` | `13221498.11` | `13221498.11` | `13221498.11` | `0.0` | **PASS** |
| `KPI-006` | **Delivered Freight Value** | `R$ 2,198,275.64` | `2198275.64` | `2198275.64` | `2198275.64` | `2198275.64` | `2198275.64` | `0.0` | **PASS** |
| `KPI-007` | **Gross Payment Value (All Statuses)** | `R$ 16,008,872.12` | `16008872.12` | `16008872.12` | `16008872.12` | `16008872.12` | `16008872.12` | `0.0` | **PASS** |
| `KPI-008` | **Mean Order Value (AOV Proxy)** | `R$ 159.86` | `159.86` | `159.86` | `159.86` | `159.86` | `159.85` | `0.01` | **PASS** |
| `KPI-009` | **Median Order Value & IQR** | `R$ 105.28 (IQR: R$ 114.45)` | `105.28` | `105.28` | `105.28` | `105.28` | `105.28` | `0.0` | **PASS** |
| `KPI-010` | **Unique Customers (Delivered vs All Statuses)** | `93,358` | `93358` | `93358` | `93358` | `93358` | `93358` | `0.0` | **PASS** |
| `KPI-011` | **True Repeat Customer Rate (Governance Rule D-5)** | `2.16% (2,015 customers)` | `2.16` | `2.16` | `2.16` | `2.16` | `2.16` | `0.0` | **PASS** |
| `KPI-012` | **Repeat Customer Revenue Share (D-5)** | `4.19% (R$ 646,454.25)` | `4.19` | `4.19` | `4.19` | `4.19` | `4.19` | `0.0` | **PASS** |
| `KPI-013` | **Average & Median Delivery Days** | `12.56 days (Median: 10.22d)` | `12.56` | `12.56` | `12.56` | `12.56` | `12.56` | `0.0` | **PASS** |
| `KPI-014` | **Late Delivery Rate (Timestamp vs Calendar Date)** | `8.11% (Calendar: 6.77%)` | `8.11` | `8.11` | `8.11` | `8.11` | `8.11` | `0.0` | **PASS** |
| `KPI-015` | **Average Customer Review Score (Delivered)** | `4.16 / 5.00` | `4.16` | `4.16` | `4.16` | `4.16` | `4.16` | `0.0` | **PASS** |
| `KPI-016` | **Late Delivery Review Score Drop** | `-1.73 stars (4.29 vs 2.57)` | `1.72` | `1.73` | `1.73` | `1.73` | `1.73` | `0.01` | **PASS** |
| `KPI-017` | **Top Product Category Item Revenue (health_beauty)** | `R$ 1,233,131.72 (9.33% share)` | `1233131.72` | `1233131.72` | `1233131.72` | `1233131.72` | `1233131.72` | `0.0` | **PASS** |
| `KPI-018` | **Top 10% Seller Revenue Concentration (Decile 1)** | `67.11% (R$ 8,873,076.37)` | `67.11` | `67.11` | `67.11` | `67.11` | `67.11` | `0.0` | **PASS** |
