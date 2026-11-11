# Verification report

Verified: 2026-11-11 19:55:56 +01:00

Result: 83 checks passed. Native SQL Server 2022 SSIS build and execution.

| Table | Rows |
|---|---:|
| dim_client | 82 |
| dim_fournisseur | 116 |
| dim_produit | 6842 |
| dim_paiement | 6 |
| dim_temps | 730 |
| fait_stock_actuel | 6842 |
| fait_achats | 6964 |
| fait_ventes | 25743 |
| fait_encaissements | 10467 |
| fait_decaissements | 502 |

Five dimensions and five facts. All 17 staging tables reconcile with source row counts and cell-level multiset SHA-256 hashes. Null and empty CSV cells are equivalent in this comparison; duplicate rows are preserved. Raw file byte hashes are recorded separately in source-manifest.json.

The full Master succeeded twice. Every dimension has identical keys and attributes after the second execution. The dimension package repaired three deliberately introduced NULL labels and a changed payment label; all dimension hashes then matched the baseline. Fixtures were restored in a finally block.

Evidence: build.log, master.log, master-rerun.log, dimension-null-and-update.log, verification-results.json, source-manifest.json.

The five fact UPDATE paths repair deliberately changed measures, nullable stock attributes and a sale's incorrect product surrogate key. A validated invoice changed to draft is removed from purchases. Restoring the source state causes its lines to be inserted again. All ten table hashes match the baseline afterward. SQL assertions compare every fact row and measure against eligible source records, reconcile each payment, and verify all 14 trusted foreign keys and their business-member mappings.

The warehouse covers current stock, validated supplier invoices, sales and sales returns, customer receipts, and supplier disbursements. Stock capture date remains NULL because the export does not establish it. Missing cost, alert threshold and document links stay NULL.
