-- =====================================================================
-- Verifications apres execution des packages SSIS
-- Comparer chaque resultat avec la valeur "attendu".
-- =====================================================================
USE DW_Health;
GO

-- 1. dim_temps : attendu 730 | 2024-09-30 | 2026-09-29
SELECT COUNT(*) AS nb, MIN([Date]) AS debut, MAX([Date]) AS fin FROM dbo.dim_temps;

-- 2. dim_temps par annee : attendu 2024 -> 93 jours / 3 feries
--                                 2025 -> 365 jours / 11 feries
--                                 2026 -> 272 jours / 8 feries
SELECT Annee, COUNT(*) AS nb_jours, SUM(CAST(EstFerie AS int)) AS nb_feries
FROM dbo.dim_temps GROUP BY Annee ORDER BY Annee;

-- 3. dim_paiement : attendu 6 lignes
--    -1 Non renseigne | 1 Cheque | 5 Carte bancaire | 7 Credit | 11 Especes | 21 Jetons
SELECT * FROM dbo.dim_paiement ORDER BY 1;

-- 4. Autres dimensions (volumes du schema, a titre indicatif :
--    dim_client 82, dim_fournisseur 116, dim_produit 6842)
SELECT 'dim_client'      AS table_name, COUNT(*) AS nb FROM dbo.dim_client
UNION ALL SELECT 'dim_fournisseur', COUNT(*) FROM dbo.dim_fournisseur
UNION ALL SELECT 'dim_produit',     COUNT(*) FROM dbo.dim_produit;
GO
