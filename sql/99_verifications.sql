USE [$(WarehouseDatabase)];
GO
SET NOCOUNT ON;
IF (SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0) <> 7
 THROW 51001, 'Expected five dimension tables and two fact tables.', 1;
IF EXISTS (SELECT 1 FROM sys.tables WHERE name NOT IN ('dim_client','dim_fournisseur','dim_produit','dim_paiement','dim_temps','fait_stock_actuel','fait_achats'))
 THROW 51002, 'Unexpected warehouse table.', 1;
IF (SELECT COUNT(*) FROM dbo.dim_temps)<>730
 THROW 51003, 'Calendar must contain 730 days.', 1;
IF EXISTS(SELECT 1 FROM dbo.dim_temps WHERE DateKey<>CONVERT(int,CONVERT(char(8),[Date],112)) OR Annee<>YEAR([Date]) OR Mois<>MONTH([Date]) OR Trimestre<>DATEPART(QUARTER,[Date]) OR SemaineISO<>DATEPART(ISO_WEEK,[Date]))
 THROW 51004, 'Invalid calendar attributes.', 1;
IF NOT EXISTS(SELECT 1 FROM dbo.dim_client WHERE Company_Id=-1)
 OR NOT EXISTS(SELECT 1 FROM dbo.dim_fournisseur WHERE Fournisseur_Id=-1)
 THROW 51005, 'Unknown partner member missing.', 1;
IF NOT EXISTS(SELECT 1 FROM dbo.dim_client WHERE Company_Id=2 AND EstClientIdentifie=0)
 THROW 51006, 'Anonymous customer must not count as identified.', 1;
IF EXISTS(SELECT 1 FROM dbo.dim_produit WHERE NULLIF(LTRIM(RTRIM(Libelle)),N'') IS NULL)
 OR EXISTS(SELECT 1 FROM dbo.dim_client WHERE NULLIF(LTRIM(RTRIM(Nom)),N'') IS NULL)
 OR EXISTS(SELECT 1 FROM dbo.dim_fournisseur WHERE NULLIF(LTRIM(RTRIM(Nom)),N'') IS NULL)
 THROW 51007, 'A dimension label is missing.', 1;
IF (SELECT COUNT(*) FROM dbo.dim_paiement)<>6
 THROW 51008, 'Expected six payment modes for this dataset.', 1;
IF EXISTS(SELECT 1 FROM sys.foreign_keys WHERE is_disabled=1 OR is_not_trusted=1)
 THROW 51009,'All warehouse foreign keys must be enabled and trusted.',1;
IF EXISTS(
 SELECT Product_Id,QuantiteActuelle,QuantiteAlerte,CAST(CASE WHEN QuantiteAlerte IS NULL THEN NULL WHEN QuantiteActuelle<QuantiteAlerte THEN 1 ELSE 0 END AS bit)
 FROM [$(StagingDatabase)].dbo.v_source_stock
 EXCEPT SELECT Product_Id,QuantiteActuelle,QuantiteAlerte,EstSousSeuil FROM dbo.fait_stock_actuel)
 OR EXISTS(
 SELECT Product_Id,QuantiteActuelle,QuantiteAlerte,EstSousSeuil FROM dbo.fait_stock_actuel
 EXCEPT SELECT Product_Id,QuantiteActuelle,QuantiteAlerte,CAST(CASE WHEN QuantiteAlerte IS NULL THEN NULL WHEN QuantiteActuelle<QuantiteAlerte THEN 1 ELSE 0 END AS bit) FROM [$(StagingDatabase)].dbo.v_source_stock)
 THROW 51010,'Stock rows or measures differ from staging.',1;
IF EXISTS(SELECT 1 FROM dbo.fait_stock_actuel WHERE DateKey IS NOT NULL)
 THROW 51011,'Source snapshot date is unknown; do not invent a date.',1;
IF EXISTS(
 SELECT Id,Document_Id,CONVERT(int,CONVERT(char(8),DocumentDate,112)),Product_Id,Fournisseur_Id,Quantity,MontantNet_HT
 FROM [$(StagingDatabase)].dbo.v_source_achats WHERE IsValidated=1 AND Product_Id IS NOT NULL
 EXCEPT SELECT Id,Document_Id,DateKey,Product_Id,Fournisseur_Id,QuantiteAchetee,MontantAchat_HT FROM dbo.fait_achats)
 OR EXISTS(
 SELECT Id,Document_Id,DateKey,Product_Id,Fournisseur_Id,QuantiteAchetee,MontantAchat_HT FROM dbo.fait_achats
 EXCEPT SELECT Id,Document_Id,CONVERT(int,CONVERT(char(8),DocumentDate,112)),Product_Id,Fournisseur_Id,Quantity,MontantNet_HT
 FROM [$(StagingDatabase)].dbo.v_source_achats WHERE IsValidated=1 AND Product_Id IS NOT NULL)
 THROW 51012,'Purchase rows or measures differ from validated invoice lines.',1;
IF EXISTS(
 SELECT f.Document_Id FROM dbo.fait_achats f
 JOIN [$(StagingDatabase)].dbo.Documents_SA d ON TRY_CONVERT(bigint,d.Id)=f.Document_Id
 GROUP BY f.Document_Id,d.TotalNetHt
 HAVING SUM(f.MontantAchat_HT)<>[$(StagingDatabase)].dbo.fn_nombre_fait(d.TotalNetHt))
 THROW 51013,'Net purchase totals do not reconcile with supplier invoice headers.',1;
PRINT 'Five dimensions and two facts validated successfully.';
