USE [$(WarehouseDatabase)];
GO
-- Quels produits ont besoin de réapprovisionnement ?
SELECT p.Product_Id,p.Libelle,p.Famille,p.Marque,
 f.QuantiteActuelle,f.QuantiteAlerte
FROM dbo.fait_stock_actuel f JOIN dbo.dim_produit p ON p.Produit_SK=f.Produit_SK
WHERE f.EstSousSeuil=1 ORDER BY f.QuantiteActuelle,p.Libelle;

-- Combien avons-nous acheté par mois et fournisseur (hors avoirs) ?
SELECT t.Annee,t.Mois,s.Nom AS Fournisseur,
 COUNT(DISTINCT f.Document_Id) AS NombreFactures,
 SUM(f.MontantAchat_HT) AS MontantAchat_HT
FROM dbo.fait_achats f
JOIN dbo.dim_temps t ON t.DateKey=f.DateKey
JOIN dbo.dim_fournisseur s ON s.Fournisseur_SK=f.Fournisseur_SK
GROUP BY t.Annee,t.Mois,s.Nom ORDER BY t.Annee,t.Mois,MontantAchat_HT DESC;

-- Quantités achetées : grouper par produit pour conserver le sens des unités.
SELECT p.Product_Id,p.Libelle,SUM(f.QuantiteAchetee) AS QuantiteAchetee,
 SUM(f.MontantAchat_HT) AS MontantAchat_HT
FROM dbo.fait_achats f JOIN dbo.dim_produit p ON p.Produit_SK=f.Produit_SK
GROUP BY p.Product_Id,p.Libelle ORDER BY MontantAchat_HT DESC;

-- Chiffre d'affaires HT et remises par mois, retours compris.
SELECT t.Annee,t.Mois,SUM(v.CA_HT) AS CA_HT,SUM(v.Remise_HT) AS Remise_HT
FROM dbo.fait_ventes v JOIN dbo.dim_temps t ON t.DateKey=v.DateKey
GROUP BY t.Annee,t.Mois ORDER BY t.Annee,t.Mois;

-- Encaissements et decaissements par mois et mode de paiement.
WITH Flux AS (
 SELECT DateKey,Paiement_SK,Amount,N'Encaissement' AS Sens FROM dbo.fait_encaissements
 UNION ALL
 SELECT DateKey,Paiement_SK,Amount,N'Decaissement' FROM dbo.fait_decaissements
)
SELECT t.Annee,t.Mois,f.Sens,p.PaymentModeName,SUM(f.Amount) AS Montant
FROM Flux f JOIN dbo.dim_temps t ON t.DateKey=f.DateKey
JOIN dbo.dim_paiement p ON p.Paiement_SK=f.Paiement_SK
GROUP BY t.Annee,t.Mois,f.Sens,p.PaymentModeName
ORDER BY t.Annee,t.Mois,f.Sens,p.PaymentModeName;
