USE [$(WarehouseDatabase)];
GO
-- Quels produits ont besoin de réapprovisionnement ?
SELECT p.Product_Id,p.Libelle,p.Famille,p.Marque,
 f.QuantiteActuelle,f.QuantiteAlerte
FROM dbo.fait_stock_actuel f JOIN dbo.dim_produit p ON p.Product_Id=f.Product_Id
WHERE f.EstSousSeuil=1 ORDER BY f.QuantiteActuelle,p.Libelle;

-- Combien avons-nous acheté par mois et fournisseur (hors avoirs) ?
SELECT t.Annee,t.Mois,s.Nom AS Fournisseur,
 COUNT(DISTINCT f.Document_Id) AS NombreFactures,
 SUM(f.MontantAchat_HT) AS MontantAchat_HT
FROM dbo.fait_achats f
JOIN dbo.dim_temps t ON t.DateKey=f.DateKey
JOIN dbo.dim_fournisseur s ON s.Fournisseur_Id=f.Fournisseur_Id
GROUP BY t.Annee,t.Mois,s.Nom ORDER BY t.Annee,t.Mois,MontantAchat_HT DESC;

-- Quantités achetées : grouper par produit pour conserver le sens des unités.
SELECT p.Product_Id,p.Libelle,SUM(f.QuantiteAchetee) AS QuantiteAchetee,
 SUM(f.MontantAchat_HT) AS MontantAchat_HT
FROM dbo.fait_achats f JOIN dbo.dim_produit p ON p.Product_Id=f.Product_Id
GROUP BY p.Product_Id,p.Libelle ORDER BY MontantAchat_HT DESC;
