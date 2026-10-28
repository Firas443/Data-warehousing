# Verification report

Verified: 2026-10-28 20:54:02 +01:00

Result: 67 checks passed. Native SQL Server 2022 SSIS build and execution.

| Dimension | Rows |
|---|---:|
| dim_client | 82 |
| dim_fournisseur | 116 |
| dim_produit | 6842 |
| dim_paiement | 6 |
| dim_temps | 730 |
| fait_stock_actuel | 6842 |
| fait_achats | 6964 |

Five dimensions and two facts. All 17 staging tables reconcile with source row counts and cell-level multiset SHA-256 hashes. Null and empty CSV cells are equivalent in this comparison; duplicate rows are preserved. Raw file byte hashes are recorded separately in source-manifest.json.

The full Master succeeded twice. Every dimension has identical keys and attributes after the second execution. The dimension package repaired three deliberately introduced NULL labels and a changed payment label; all dimension hashes then matched the baseline. Fixtures were restored in a finally block.

Evidence: build.log, master.log, master-rerun.log, dimension-null-and-update.log, verification-results.json, source-manifest.json.

The two fact UPDATE paths repair deliberately changed measures and nullable stock attributes. A validated invoice changed to draft is removed from purchases; restored source state causes its lines to be inserted again. All seven table hashes match the baseline afterward. SQL assertions compare every fact row and measure against eligible source records and require enabled, trusted foreign keys.

Scope: current stock and validated supplier invoices only, excluding supplier credit notes. Stock capture date remains NULL because the export does not establish it. Missing source labels, alert thresholds and attributes remain explicitly unknown.

## Business results

Stock: 6,842 products, total source quantity 18,800; 4,449 known alert thresholds and 2,195 products below threshold. The remaining 2,393 thresholds are unknown. Snapshot DateKey remains NULL.

Purchases: 6,964 lines from 880 validated supplier invoices, net HT total 958,947.7230 after document discounts. All invoice net totals reconcile exactly. Credit notes are excluded. 49 draft lines and 14 comment lines are recorded in staging exclusions. All five foreign keys are enabled and trusted.

Original four dimension component sets and designer layouts retained; two fact diagrams added. Six native Data Flows in ETL_SA_DW.dtsx.
