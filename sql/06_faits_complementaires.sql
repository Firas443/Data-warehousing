USE [$(WarehouseDatabase)];
GO
IF OBJECT_ID('dbo.fait_ventes','U') IS NULL
CREATE TABLE dbo.fait_ventes(
 Id bigint NOT NULL CONSTRAINT PK_fait_ventes PRIMARY KEY,
 Document_Id bigint NOT NULL,
 DateKey int NOT NULL CONSTRAINT FK_ventes_temps REFERENCES dbo.dim_temps(DateKey),
 Product_Id int NOT NULL CONSTRAINT FK_ventes_produit REFERENCES dbo.dim_produit(Product_Id),
 Company_Id int NOT NULL CONSTRAINT FK_ventes_client REFERENCES dbo.dim_client(Company_Id),
 QuantiteVendue decimal(18,4) NOT NULL,
 Remise_HT decimal(18,4) NOT NULL,
 CA_HT decimal(18,4) NOT NULL,
 Cout_HT decimal(18,4) NULL
);
IF OBJECT_ID('dbo.fait_encaissements','U') IS NULL
CREATE TABLE dbo.fait_encaissements(
 Id bigint NOT NULL CONSTRAINT PK_fait_encaissements PRIMARY KEY,
 Payment_Id bigint NOT NULL,
 Document_Id bigint NULL,
 DateKey int NOT NULL CONSTRAINT FK_encaissements_temps REFERENCES dbo.dim_temps(DateKey),
 PaymentMode_Id int NOT NULL CONSTRAINT FK_encaissements_paiement REFERENCES dbo.dim_paiement(PaymentMode_Id),
 Company_Id int NOT NULL CONSTRAINT FK_encaissements_client REFERENCES dbo.dim_client(Company_Id),
 Amount decimal(18,4) NOT NULL
);
IF OBJECT_ID('dbo.fait_decaissements','U') IS NULL
CREATE TABLE dbo.fait_decaissements(
 Id bigint NOT NULL CONSTRAINT PK_fait_decaissements PRIMARY KEY,
 Payment_Id bigint NOT NULL,
 Document_Id bigint NULL,
 DateKey int NOT NULL CONSTRAINT FK_decaissements_temps REFERENCES dbo.dim_temps(DateKey),
 PaymentMode_Id int NOT NULL CONSTRAINT FK_decaissements_paiement REFERENCES dbo.dim_paiement(PaymentMode_Id),
 Fournisseur_Id int NOT NULL CONSTRAINT FK_decaissements_fournisseur REFERENCES dbo.dim_fournisseur(Fournisseur_Id),
 Amount decimal(18,4) NOT NULL
);
GO
USE [$(StagingDatabase)];
GO
IF OBJECT_ID('dbo.CoutsVentes_Faits','U') IS NULL
CREATE TABLE dbo.CoutsVentes_Faits(
 Document_Id bigint NOT NULL,StockId int NOT NULL,UnitCost decimal(18,4) NOT NULL,
 CONSTRAINT PK_CoutsVentes_Faits PRIMARY KEY(Document_Id,StockId)
);
IF OBJECT_ID('dbo.VentesPreparees_Faits','U') IS NULL
CREATE TABLE dbo.VentesPreparees_Faits(
 Id bigint NULL,Document_Id bigint NULL,DocumentDate datetime NULL,Product_Id int NULL,Company_Id int NOT NULL,
 QuantiteVendue decimal(18,4) NULL,Remise_HT decimal(18,4) NULL,CA_HT decimal(18,4) NULL,
 Cout_HT decimal(18,4) NULL,Motif nvarchar(100) NOT NULL
);
IF OBJECT_ID('dbo.PaiementsActifs_Faits','U') IS NULL
CREATE TABLE dbo.PaiementsActifs_Faits(
 Payment_Id bigint NULL,PaymentDate datetime NULL,Amount decimal(18,4) NULL,
 PaymentMode_Id int NOT NULL,Company_Id int NOT NULL,Fournisseur_Id int NOT NULL,IsSupplier int NULL
);
IF OBJECT_ID('dbo.ReglementsPrepares_Faits','U') IS NULL
CREATE TABLE dbo.ReglementsPrepares_Faits(
 Id bigint NULL,Payment_Id bigint NULL,Document_Id bigint NULL,PaymentDate datetime NULL,
 PaymentMode_Id int NOT NULL,Company_Id int NOT NULL,Fournisseur_Id int NOT NULL,IsSupplier int NULL,
 Amount decimal(18,4) NULL
);
GO
CREATE OR ALTER VIEW dbo.v_calcul_ventes AS
WITH grouped AS (
 SELECT DISTINCT TRY_CONVERT(bigint,Document1_Id) AS Document_Id
 FROM dbo.RelatedDocuments_SA
)
SELECT TRY_CONVERT(bigint,NULLIF(TRIM(i.Id),N'')) AS Id,TRY_CONVERT(bigint,d.Id) AS Document_Id,
 TRY_CONVERT(datetime,NULLIF(TRIM(d.DocumentDate),N''),101) AS DocumentDate,
 TRY_CONVERT(int,NULLIF(TRIM(ps.Product_Id),N'')) AS Product_Id,
 COALESCE(c.Company_Id,-1) AS Company_Id,
 CAST(CASE WHEN s.IsReturn=1 THEN -ABS(n.Quantity) ELSE n.Quantity END AS decimal(18,4)) AS QuantiteVendue,
 CAST(CASE WHEN s.IsReturn=1 THEN -ABS(n.Discount) ELSE n.Discount END AS decimal(18,4)) AS Remise_HT,
 CAST(CASE WHEN s.IsReturn=1 THEN -ABS(n.LineTotal) ELSE n.LineTotal END AS decimal(18,4)) AS CA_HT,
 CAST(CASE WHEN s.IsReturn=1 THEN -ABS(n.Quantity) ELSE n.Quantity END*r.UnitCost AS decimal(18,4)) AS Cout_HT,
 CAST(CASE WHEN d.State<>N'1' OR d.State IS NULL THEN N'BROUILLON'
      WHEN d.DocumentType_Id=N'1' AND g.Document_Id IS NOT NULL THEN N'FACTURE_REGROUPEE'
      WHEN NULLIF(TRIM(i.ProductStock_Id),N'') IS NULL
        AND (NULLIF(TRIM(i.PrixTotalHt),N'') IS NULL OR dbo.fn_nombre_fait(i.PrixTotalHt)=0)
        THEN N'SANS_PRODUIT'
      ELSE N'ACCEPTE' END AS nvarchar(100)) AS Motif
FROM dbo.DocumentItem_SA i
JOIN dbo.Documents_SA d ON TRY_CONVERT(bigint,d.Id)=TRY_CONVERT(bigint,i.Document_Id)
LEFT JOIN dbo.ProductStocks_SA ps ON TRY_CONVERT(int,ps.Id)=TRY_CONVERT(int,i.ProductStock_Id)
LEFT JOIN dbo.Transactions_SA t ON TRY_CONVERT(bigint,t.Id)=TRY_CONVERT(bigint,d.Transaction_Id)
LEFT JOIN [$(WarehouseDatabase)].dbo.dim_client c ON c.Company_Id=TRY_CONVERT(int,NULLIF(TRIM(t.Company_Id),N''))
LEFT JOIN dbo.CoutsVentes_Faits r ON r.Document_Id=TRY_CONVERT(bigint,d.Id) AND r.StockId=TRY_CONVERT(int,i.ProductStock_Id)
LEFT JOIN grouped g ON g.Document_Id=TRY_CONVERT(bigint,d.Id)
CROSS APPLY (VALUES(CASE WHEN d.DocumentType_Id IN (N'4',N'7') THEN 1 ELSE 0 END)) s(IsReturn)
CROSS APPLY (VALUES(
 dbo.fn_nombre_fait(i.Quantity),
 CASE WHEN NULLIF(TRIM(i.SumDiscountTotal),N'') IS NULL THEN 0 ELSE dbo.fn_nombre_fait(i.SumDiscountTotal) END,
 CASE WHEN NULLIF(TRIM(i.PrixTotalHt),N'') IS NULL THEN dbo.fn_nombre_fait(i.SumPrixNetHt)
      ELSE dbo.fn_nombre_fait(i.PrixTotalHt) END
)) n(Quantity,Discount,LineTotal)
WHERE d.DocumentType_Id IN (N'1',N'4',N'5',N'6',N'7');
GO
CREATE OR ALTER VIEW dbo.v_source_ventes AS
SELECT Id,Document_Id,DocumentDate,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT,Motif
FROM dbo.VentesPreparees_Faits;
GO
CREATE OR ALTER VIEW dbo.v_calcul_paiements AS
WITH candidates AS (
 SELECT Id,Company_Id,Amount,PaymentDate,PaymentMode_Id,IsRemoved FROM dbo.PaymentsList_SA
 UNION ALL
 SELECT p.Id,p.Company_Id,p.Amount,p.PaymentDate,p.PaymentMode_Id,N'FAUX'
 FROM dbo.Payment_SA p WHERE NOT EXISTS(SELECT 1 FROM dbo.PaymentsList_SA l WHERE TRY_CONVERT(bigint,l.Id)=TRY_CONVERT(bigint,p.Id))
), directions AS (
 SELECT TRY_CONVERT(bigint,a.Payment_Id) AS Payment_Id,MIN(CASE WHEN d.DocumentType_Id IN (N'20',N'23') THEN 1 ELSE 0 END) AS MinSide,
 MAX(CASE WHEN d.DocumentType_Id IN (N'20',N'23') THEN 1 ELSE 0 END) AS MaxSide
 FROM dbo.TransactionPayments_SA a JOIN dbo.Documents_SA d ON TRY_CONVERT(bigint,d.Transaction_Id)=TRY_CONVERT(bigint,a.Transaction_Id)
 WHERE d.State=N'1' AND d.DocumentType_Id IN (N'1',N'4',N'5',N'6',N'7',N'20',N'23')
 GROUP BY TRY_CONVERT(bigint,a.Payment_Id)
)
SELECT TRY_CONVERT(bigint,NULLIF(TRIM(p.Id),N'')) AS Payment_Id,
 TRY_CONVERT(datetime,NULLIF(TRIM(p.PaymentDate),N''),103) AS PaymentDate,
 dbo.fn_nombre_fait(p.Amount) AS Amount,
 COALESCE(m.PaymentMode_Id,-1) AS PaymentMode_Id,
 COALESCE(dc.Company_Id,-1) AS Company_Id,COALESCE(df.Fournisseur_Id,-1) AS Fournisseur_Id,
 CASE c.CompanyType_Id WHEN N'1' THEN 0 WHEN N'2' THEN 1
      ELSE CASE WHEN s.MinSide=s.MaxSide THEN s.MinSide END END AS IsSupplier
FROM candidates p
LEFT JOIN directions s ON s.Payment_Id=TRY_CONVERT(bigint,p.Id)
LEFT JOIN dbo.CompaniesList_SA c ON TRY_CONVERT(int,c.Id)=TRY_CONVERT(int,p.Company_Id)
LEFT JOIN [$(WarehouseDatabase)].dbo.dim_client dc ON dc.Company_Id=TRY_CONVERT(int,NULLIF(TRIM(p.Company_Id),N''))
LEFT JOIN [$(WarehouseDatabase)].dbo.dim_fournisseur df ON df.Fournisseur_Id=TRY_CONVERT(int,NULLIF(TRIM(p.Company_Id),N''))
LEFT JOIN [$(WarehouseDatabase)].dbo.dim_paiement m ON m.PaymentMode_Id=TRY_CONVERT(int,NULLIF(TRIM(p.PaymentMode_Id),N''))
WHERE UPPER(TRIM(COALESCE(p.IsRemoved,N''))) NOT IN (N'VRAI',N'TRUE',N'1');
GO
CREATE OR ALTER VIEW dbo.v_paiements_actifs AS
SELECT Payment_Id,PaymentDate,Amount,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier
FROM dbo.PaiementsActifs_Faits;
GO
CREATE OR ALTER VIEW dbo.v_calcul_reglements AS
WITH targets AS (
 SELECT TRY_CONVERT(bigint,d.Transaction_Id) AS Transaction_Id,CASE WHEN d.DocumentType_Id IN (N'20',N'23') THEN 1 ELSE 0 END AS IsSupplier,
 CASE WHEN COUNT(*)=1 THEN MAX(TRY_CONVERT(bigint,d.Id)) END AS Document_Id
 FROM dbo.Documents_SA d
 WHERE d.State=N'1' AND d.DocumentType_Id IN (N'1',N'4',N'5',N'6',N'7',N'20',N'23')
 GROUP BY TRY_CONVERT(bigint,d.Transaction_Id),CASE WHEN d.DocumentType_Id IN (N'20',N'23') THEN 1 ELSE 0 END
), allocations AS (
 SELECT TRY_CONVERT(bigint,NULLIF(TRIM(a.Id),N'')) AS Id,
 TRY_CONVERT(bigint,NULLIF(TRIM(a.Payment_Id),N'')) AS Payment_Id,
 TRY_CONVERT(bigint,a.Transaction_Id) AS Transaction_Id,dbo.fn_nombre_fait(a.Amount) AS Amount
 FROM dbo.TransactionPayments_SA a
), totals AS (
 SELECT Payment_Id,CAST(SUM(Amount) AS decimal(28,4)) AS Amount,COUNT(*) AS Allocations
 FROM allocations GROUP BY Payment_Id
)
-- Positive IDs come from TransactionPayments. Negative IDs identify unapplied payment balances.
SELECT a.Id,p.Payment_Id,t.Document_Id,p.PaymentDate,p.PaymentMode_Id,p.Company_Id,p.Fournisseur_Id,p.IsSupplier,a.Amount
FROM dbo.v_paiements_actifs p JOIN allocations a ON a.Payment_Id=p.Payment_Id
LEFT JOIN targets t ON t.Transaction_Id=a.Transaction_Id AND t.IsSupplier=p.IsSupplier
UNION ALL
SELECT -p.Payment_Id,p.Payment_Id,CAST(NULL AS bigint),p.PaymentDate,p.PaymentMode_Id,p.Company_Id,p.Fournisseur_Id,p.IsSupplier,
 CAST(p.Amount-COALESCE(t.Amount,0) AS decimal(18,4))
FROM dbo.v_paiements_actifs p LEFT JOIN totals t ON t.Payment_Id=p.Payment_Id
WHERE t.Allocations IS NULL OR p.Amount<>t.Amount;
GO
CREATE OR ALTER VIEW dbo.v_source_reglements AS
SELECT Id,Payment_Id,Document_Id,PaymentDate,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier,Amount
FROM dbo.ReglementsPrepares_Faits;
GO
CREATE OR ALTER PROCEDURE dbo.usp_preparer_faits_complementaires
AS
BEGIN
 SET NOCOUNT ON;
 TRUNCATE TABLE dbo.CoutsVentes_Faits;
 ;WITH costs AS (
  SELECT TRY_CONVERT(bigint,DocumentId) AS Document_Id,TRY_CONVERT(int,ProductStock_Id) AS StockId,
  dbo.fn_nombre_fait(JSON_VALUE(CASE WHEN ISJSON(Extra)=1 THEN Extra END,'$.cump')) AS UnitCost,
  TRY_CONVERT(bigint,Id) AS MovementId
  FROM dbo.StockMovements_SA WHERE UPPER(Description) LIKE N'VALIDATION%'
 ), ranked AS (
  SELECT *,ROW_NUMBER() OVER(PARTITION BY Document_Id,StockId ORDER BY MovementId,UnitCost) AS rn
  FROM costs WHERE Document_Id IS NOT NULL AND StockId IS NOT NULL AND UnitCost IS NOT NULL
 )
 INSERT dbo.CoutsVentes_Faits(Document_Id,StockId,UnitCost)
 SELECT Document_Id,StockId,UnitCost FROM ranked WHERE rn=1;

 TRUNCATE TABLE dbo.VentesPreparees_Faits;
 INSERT dbo.VentesPreparees_Faits(Id,Document_Id,DocumentDate,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT,Motif)
 SELECT Id,Document_Id,DocumentDate,Product_Id,Company_Id,QuantiteVendue,Remise_HT,CA_HT,Cout_HT,Motif
 FROM dbo.v_calcul_ventes OPTION(HASH JOIN);

 IF EXISTS(SELECT 1 FROM dbo.v_source_ventes WHERE Motif=N'ACCEPTE'
  AND (Id IS NULL OR Document_Id IS NULL OR DocumentDate IS NULL OR Product_Id IS NULL
       OR QuantiteVendue IS NULL OR Remise_HT IS NULL OR CA_HT IS NULL))
 THROW 51103,'Invalid validated sale line; inspect staging.',1;

 TRUNCATE TABLE dbo.PaiementsActifs_Faits;
 INSERT dbo.PaiementsActifs_Faits(Payment_Id,PaymentDate,Amount,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier)
 SELECT Payment_Id,PaymentDate,Amount,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier
 FROM dbo.v_calcul_paiements OPTION(HASH JOIN);
 IF EXISTS(SELECT 1 FROM dbo.v_paiements_actifs WHERE Payment_Id IS NULL OR Payment_Id<=0
  OR PaymentDate IS NULL OR Amount IS NULL OR IsSupplier IS NULL)
 OR EXISTS(SELECT Payment_Id FROM dbo.v_paiements_actifs GROUP BY Payment_Id HAVING COUNT(*)>1)
 THROW 51104,'Invalid active payment; inspect staging.',1;

 TRUNCATE TABLE dbo.ReglementsPrepares_Faits;
 INSERT dbo.ReglementsPrepares_Faits(Id,Payment_Id,Document_Id,PaymentDate,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier,Amount)
 SELECT Id,Payment_Id,Document_Id,PaymentDate,PaymentMode_Id,Company_Id,Fournisseur_Id,IsSupplier,Amount
 FROM dbo.v_calcul_reglements OPTION(HASH JOIN);
 IF EXISTS(SELECT 1 FROM dbo.v_source_reglements WHERE Id IS NULL OR Id=0 OR Amount IS NULL)
 OR EXISTS(SELECT Id FROM dbo.v_source_reglements GROUP BY Id HAVING COUNT(*)>1)
 THROW 51105,'Invalid payment allocation; inspect staging.',1;

 DELETE f FROM [$(WarehouseDatabase)].dbo.fait_ventes f
 WHERE NOT EXISTS(SELECT 1 FROM dbo.v_source_ventes s WHERE s.Id=f.Id AND s.Motif=N'ACCEPTE');
 DELETE f FROM [$(WarehouseDatabase)].dbo.fait_encaissements f
 WHERE NOT EXISTS(SELECT 1 FROM dbo.v_source_reglements s WHERE s.Id=f.Id AND s.IsSupplier=0);
 DELETE f FROM [$(WarehouseDatabase)].dbo.fait_decaissements f
 WHERE NOT EXISTS(SELECT 1 FROM dbo.v_source_reglements s WHERE s.Id=f.Id AND s.IsSupplier=1);
END;
GO
