USE [$(WarehouseDatabase)];
GO
SET NOCOUNT ON;
IF (SELECT COUNT(*) FROM sys.tables WHERE is_ms_shipped=0) <> 10
 THROW 51001, 'Expected five dimension tables and five fact tables.', 1;
IF EXISTS (SELECT 1 FROM sys.tables WHERE name NOT IN ('dim_client','dim_fournisseur','dim_produit','dim_paiement','dim_temps','fait_stock_actuel','fait_achats','fait_ventes','fait_encaissements','fait_decaissements'))
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
IF (
 SELECT COUNT(*)
 FROM sys.foreign_key_columns k
 JOIN sys.columns p ON p.object_id=k.parent_object_id AND p.column_id=k.parent_column_id
 JOIN sys.columns r ON r.object_id=k.referenced_object_id AND r.column_id=k.referenced_column_id
 WHERE p.name=r.name AND p.name IN ('Produit_SK','Client_SK','Paiement_SK','Fournisseur_SK','DateKey')
)<>14
 THROW 51018,'Expected nine surrogate-key and five calendar relationships.',1;
IF EXISTS(SELECT 1 FROM dbo.fait_stock_actuel f JOIN dbo.dim_produit p ON p.Produit_SK=f.Produit_SK WHERE f.Product_Id<>p.Product_Id)
 OR EXISTS(SELECT 1 FROM dbo.fait_achats f
  JOIN dbo.dim_produit p ON p.Produit_SK=f.Produit_SK
  JOIN dbo.dim_fournisseur s ON s.Fournisseur_SK=f.Fournisseur_SK
  WHERE f.Product_Id<>p.Product_Id OR f.Fournisseur_Id<>s.Fournisseur_Id)
 OR EXISTS(SELECT 1 FROM dbo.fait_ventes f
  JOIN dbo.dim_produit p ON p.Produit_SK=f.Produit_SK
  JOIN dbo.dim_client c ON c.Client_SK=f.Client_SK
  WHERE f.Product_Id<>p.Product_Id OR f.Company_Id<>c.Company_Id)
 OR EXISTS(SELECT 1 FROM dbo.fait_encaissements f
  JOIN dbo.dim_client c ON c.Client_SK=f.Client_SK
  JOIN dbo.dim_paiement p ON p.Paiement_SK=f.Paiement_SK
  WHERE f.Company_Id<>c.Company_Id OR f.PaymentMode_Id<>p.PaymentMode_Id)
 OR EXISTS(SELECT 1 FROM dbo.fait_decaissements f
  JOIN dbo.dim_fournisseur s ON s.Fournisseur_SK=f.Fournisseur_SK
  JOIN dbo.dim_paiement p ON p.Paiement_SK=f.Paiement_SK
  WHERE f.Fournisseur_Id<>s.Fournisseur_Id OR f.PaymentMode_Id<>p.PaymentMode_Id)
 THROW 51019,'A fact surrogate key points to the wrong business member.',1;
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
DECLARE @FactDifferences bigint;
SELECT @FactDifferences=COUNT_BIG(*)
FROM (
 SELECT * FROM (
 SELECT Id,Document_Id,CONVERT(int,CONVERT(char(8),DocumentDate,112)) AS DateKey,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT
 FROM [$(StagingDatabase)].dbo.v_source_ventes WHERE Motif=N'ACCEPTE'
 EXCEPT SELECT Id,Document_Id,DateKey,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT FROM dbo.fait_ventes
 ) AS Missing
 UNION ALL
 SELECT * FROM (
 SELECT Id,Document_Id,DateKey,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT FROM dbo.fait_ventes
 EXCEPT SELECT Id,Document_Id,CONVERT(int,CONVERT(char(8),DocumentDate,112)) AS DateKey,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT
 FROM [$(StagingDatabase)].dbo.v_source_ventes WHERE Motif=N'ACCEPTE'
 ) AS Extra
) AS Differences
OPTION (HASH JOIN);
IF @FactDifferences<>0
 THROW 51014,'Warehouse fait_ventes differs from eligible staging rows.',1;
SELECT @FactDifferences=COUNT_BIG(*)
FROM (
 SELECT * FROM (
 SELECT Id,Payment_Id,Document_Id,CONVERT(int,CONVERT(char(8),PaymentDate,112)) AS DateKey,PaymentMode_Id,Company_Id,Amount
 FROM [$(StagingDatabase)].dbo.v_source_reglements WHERE IsSupplier=0
 EXCEPT SELECT Id,Payment_Id,Document_Id,DateKey,PaymentMode_Id,Company_Id,Amount FROM dbo.fait_encaissements
 ) AS Missing
 UNION ALL
 SELECT * FROM (
 SELECT Id,Payment_Id,Document_Id,DateKey,PaymentMode_Id,Company_Id,Amount FROM dbo.fait_encaissements
 EXCEPT SELECT Id,Payment_Id,Document_Id,CONVERT(int,CONVERT(char(8),PaymentDate,112)) AS DateKey,PaymentMode_Id,Company_Id,Amount
 FROM [$(StagingDatabase)].dbo.v_source_reglements WHERE IsSupplier=0
 ) AS Extra
) AS Differences
OPTION (HASH JOIN);
IF @FactDifferences<>0
 THROW 51015,'Warehouse fait_encaissements differs from eligible staging rows.',1;
SELECT @FactDifferences=COUNT_BIG(*)
FROM (
 SELECT * FROM (
 SELECT Id,Payment_Id,Document_Id,CONVERT(int,CONVERT(char(8),PaymentDate,112)) AS DateKey,PaymentMode_Id,Fournisseur_Id,Amount
 FROM [$(StagingDatabase)].dbo.v_source_reglements WHERE IsSupplier=1
 EXCEPT SELECT Id,Payment_Id,Document_Id,DateKey,PaymentMode_Id,Fournisseur_Id,Amount FROM dbo.fait_decaissements
 ) AS Missing
 UNION ALL
 SELECT * FROM (
 SELECT Id,Payment_Id,Document_Id,DateKey,PaymentMode_Id,Fournisseur_Id,Amount FROM dbo.fait_decaissements
 EXCEPT SELECT Id,Payment_Id,Document_Id,CONVERT(int,CONVERT(char(8),PaymentDate,112)) AS DateKey,PaymentMode_Id,Fournisseur_Id,Amount
 FROM [$(StagingDatabase)].dbo.v_source_reglements WHERE IsSupplier=1
 ) AS Extra
) AS Differences
OPTION (HASH JOIN);
IF @FactDifferences<>0
 THROW 51016,'Warehouse fait_decaissements differs from eligible staging rows.',1;

-- Each active payment must reconcile to its source amount on the correct side.
SELECT @FactDifferences=COUNT_BIG(*) FROM (
 SELECT p.Payment_Id,p.IsSupplier,p.Amount FROM [$(StagingDatabase)].dbo.v_paiements_actifs p
 EXCEPT
 SELECT Payment_Id,IsSupplier,SUM(Amount)
 FROM (
  SELECT Payment_Id,0 AS IsSupplier,Amount FROM dbo.fait_encaissements
  UNION ALL
  SELECT Payment_Id,1,Amount FROM dbo.fait_decaissements
 ) f GROUP BY Payment_Id,IsSupplier
) AS Differences OPTION (HASH JOIN);
IF @FactDifferences<>0
 THROW 51017,'Payment allocations do not reconcile with active payments.',1;
PRINT 'Five dimensions and five facts validated successfully.';
