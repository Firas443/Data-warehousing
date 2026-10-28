USE [$(WarehouseDatabase)];
GO
IF OBJECT_ID('dbo.fait_stock_actuel','U') IS NULL
CREATE TABLE dbo.fait_stock_actuel(
 Product_Id int NOT NULL CONSTRAINT PK_fait_stock_actuel PRIMARY KEY,
 DateKey int NULL,
 QuantiteActuelle decimal(18,4) NOT NULL,
 QuantiteAlerte decimal(18,4) NULL,
 EstSousSeuil bit NULL,
 CONSTRAINT FK_stock_produit FOREIGN KEY(Product_Id) REFERENCES dbo.dim_produit(Product_Id),
 CONSTRAINT FK_stock_temps FOREIGN KEY(DateKey) REFERENCES dbo.dim_temps(DateKey)
);
IF OBJECT_ID('dbo.fait_achats','U') IS NULL
CREATE TABLE dbo.fait_achats(
 Id bigint NOT NULL CONSTRAINT PK_fait_achats PRIMARY KEY,
 Document_Id bigint NOT NULL,
 DateKey int NOT NULL,
 Product_Id int NOT NULL,
 Fournisseur_Id int NOT NULL,
 QuantiteAchetee decimal(18,4) NOT NULL,
 MontantAchat_HT decimal(18,4) NOT NULL,
 CONSTRAINT FK_achats_temps FOREIGN KEY(DateKey) REFERENCES dbo.dim_temps(DateKey),
 CONSTRAINT FK_achats_produit FOREIGN KEY(Product_Id) REFERENCES dbo.dim_produit(Product_Id),
 CONSTRAINT FK_achats_fournisseur FOREIGN KEY(Fournisseur_Id) REFERENCES dbo.dim_fournisseur(Fournisseur_Id)
);
GO
USE [$(StagingDatabase)];
GO
CREATE OR ALTER FUNCTION dbo.fn_nombre_fait(@s nvarchar(4000))
RETURNS decimal(18,4)
AS
BEGIN
 SET @s=REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(@s)),NCHAR(160),N''),NCHAR(8239),N''),N' ',N'');
 RETURN TRY_CONVERT(decimal(18,4),REPLACE(NULLIF(@s,N''),N',',N'.'));
END;
GO
IF OBJECT_ID('dbo.Rejets_Faits','U') IS NULL
CREATE TABLE dbo.Rejets_Faits(Fait nvarchar(40) NOT NULL,SourceId bigint NULL,Motif nvarchar(100) NOT NULL);
-- Compute catalogue text repairs once per load, before matching stock rows.
IF OBJECT_ID('dbo.CatalogueSeuils_Faits','U') IS NULL
BEGIN
 CREATE TABLE dbo.CatalogueSeuils_Faits(Code nvarchar(200) NULL,Libelle nvarchar(255) COLLATE Latin1_General_100_CI_AI NULL,Seuil decimal(18,4) NULL);
 CREATE INDEX IX_seuils_code ON dbo.CatalogueSeuils_Faits(Code);
 CREATE INDEX IX_seuils_libelle ON dbo.CatalogueSeuils_Faits(Libelle);
END;
IF OBJECT_ID('dbo.CodesProduits_Faits','U') IS NULL
CREATE TABLE dbo.CodesProduits_Faits(Product_Id int NOT NULL PRIMARY KEY,Code nvarchar(200) NULL);
GO
CREATE OR ALTER VIEW dbo.v_source_stock AS
WITH catalogue AS (
 SELECT Code,Libelle,Seuil FROM dbo.CatalogueSeuils_Faits
), seuils AS (
 SELECT Libelle,CASE WHEN COUNT(DISTINCT Seuil)=1 THEN MAX(Seuil) END AS QuantiteAlerte
 FROM catalogue GROUP BY Libelle
), codes AS (
 SELECT Code,CASE WHEN COUNT(DISTINCT Seuil)=1 THEN MAX(Seuil) END AS QuantiteAlerte
 FROM catalogue WHERE NULLIF(Code,N'') IS NOT NULL GROUP BY Code
), evenements AS (
 SELECT Product_Id,Code FROM dbo.CodesProduits_Faits
), stock AS (
 SELECT TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(Product_Id)),N'')) AS Product_Id,
 CAST(CASE WHEN COUNT(*)=COUNT(dbo.fn_nombre_fait(Quantity)) THEN SUM(dbo.fn_nombre_fait(Quantity)) END AS decimal(18,4)) AS QuantiteActuelle
 FROM dbo.ProductStocks_SA GROUP BY TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(Product_Id)),N''))
)
SELECT s.Product_Id,s.QuantiteActuelle,COALESCE(cc.QuantiteAlerte,c.QuantiteAlerte) AS QuantiteAlerte
FROM stock s LEFT JOIN [$(WarehouseDatabase)].dbo.dim_produit p ON p.Product_Id=s.Product_Id
LEFT JOIN seuils c ON c.Libelle=p.Libelle COLLATE Latin1_General_100_CI_AI
LEFT JOIN evenements e ON e.Product_Id=s.Product_Id
LEFT JOIN codes cc ON cc.Code=e.Code;
GO
CREATE OR ALTER VIEW dbo.v_source_achats AS
WITH lignes AS (
SELECT TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(i.Id)),N'')) AS Id,TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(d.Id)),N'')) AS Document_Id,
 TRY_CONVERT(datetime,NULLIF(LTRIM(RTRIM(d.DocumentDate)),N''),101) AS DocumentDate,
 CAST(CASE WHEN d.State=N'1' THEN 1 ELSE 0 END AS bit) AS IsValidated,
 TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(ps.Product_Id)),N'')) AS Product_Id,COALESCE(TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(t.Company_Id)),N'')),-1) AS Fournisseur_Id,
 dbo.fn_nombre_fait(i.Quantity) AS Quantity,dbo.fn_nombre_fait(i.PrixTotalHt) AS TotalHt,
 dbo.fn_nombre_fait(d.TotalNetHt) AS TotalDocument_HT
FROM dbo.DocumentItem_SA i
JOIN dbo.Documents_SA d ON TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(d.Id)),N''))=TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(i.Document_Id)),N''))
LEFT JOIN dbo.ProductStocks_SA ps ON TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(ps.Id)),N''))=TRY_CONVERT(int,NULLIF(LTRIM(RTRIM(i.ProductStock_Id)),N''))
LEFT JOIN dbo.Transactions_SA t ON TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(t.Id)),N''))=TRY_CONVERT(bigint,NULLIF(LTRIM(RTRIM(d.Transaction_Id)),N''))
WHERE d.DocumentType_Id=N'20'
), totaux AS (
 SELECT *,SUM(CASE WHEN Product_Id IS NOT NULL THEN TotalHt ELSE 0 END) OVER(PARTITION BY Document_Id) AS SommeLignes,
 ROW_NUMBER() OVER(PARTITION BY Document_Id ORDER BY CASE WHEN Product_Id IS NULL THEN 1 ELSE 0 END,Id DESC) AS DerniereLigne
 FROM lignes
), arrondis AS (
 SELECT *,CAST(CASE WHEN Product_Id IS NULL THEN NULL
 WHEN SommeLignes=0 AND TotalDocument_HT=0 THEN TotalHt
 ELSE ROUND(TotalHt*CONVERT(decimal(18,8),TotalDocument_HT/NULLIF(SommeLignes,0)),4) END AS decimal(18,4)) AS MontantArrondi
 FROM totaux
), nets AS (
 SELECT *,CAST(MontantArrondi+CASE WHEN DerniereLigne=1
 THEN TotalDocument_HT-SUM(MontantArrondi) OVER(PARTITION BY Document_Id) ELSE 0 END AS decimal(18,4)) AS MontantNet_HT
 FROM arrondis
)
SELECT Id,Document_Id,DocumentDate,IsValidated,Product_Id,Fournisseur_Id,Quantity,TotalHt,
 CAST(TotalHt-MontantNet_HT AS decimal(18,4)) AS RemiseDocument_HT,MontantNet_HT
FROM nets;
GO
CREATE OR ALTER PROCEDURE dbo.usp_preparer_faits
AS
BEGIN
 SET NOCOUNT ON;
 TRUNCATE TABLE dbo.CatalogueSeuils_Faits;
 INSERT dbo.CatalogueSeuils_Faits(Code,Libelle,Seuil)
 SELECT CAST(LTRIM(RTRIM(Code)) AS nvarchar(200)),
 CAST(dbo.fn_reparer_accents(LTRIM(RTRIM([Libellé]))) AS nvarchar(255)),dbo.fn_nombre_fait([Quantité d'Alerte])
 FROM dbo.Produits_SA;
 TRUNCATE TABLE dbo.CodesProduits_Faits;
 ;WITH e AS (
 SELECT TRY_CONVERT(int,JSON_VALUE(CASE WHEN ISJSON(Data)=1 THEN Data ELSE N'{}' END,'$.id')) AS Product_Id,
 CAST(JSON_VALUE(CASE WHEN ISJSON(Data)=1 THEN Data ELSE N'{}' END,'$.cde') AS nvarchar(200)) AS Code,TRY_CONVERT(bigint,Id) AS EventId
 FROM dbo.Events_SA WHERE EntityType=N'1' AND ISJSON(Data)=1
 ), classes AS (
 SELECT *,ROW_NUMBER() OVER(PARTITION BY Product_Id ORDER BY EventId DESC) AS rn FROM e WHERE Product_Id IS NOT NULL
 )
 INSERT dbo.CodesProduits_Faits(Product_Id,Code) SELECT Product_Id,Code FROM classes WHERE rn=1;
 -- Invalid core lines must fail explicitly, rather than lose business amounts.
 IF EXISTS(SELECT 1 FROM dbo.v_source_stock WHERE Product_Id IS NULL OR QuantiteActuelle IS NULL)
 THROW 51101,'Invalid stock identifier or quantity.',1;
 IF EXISTS(SELECT 1 FROM dbo.v_source_achats WHERE IsValidated=1 AND
 (Id IS NULL OR Document_Id IS NULL OR DocumentDate IS NULL
 OR (Product_Id IS NOT NULL AND (Quantity IS NULL OR TotalHt IS NULL OR MontantNet_HT IS NULL))
 OR (Product_Id IS NULL AND COALESCE(TotalHt,0)<>0)))
 THROW 51102,'Invalid validated purchase line; inspect staging data.',1;
 TRUNCATE TABLE dbo.Rejets_Faits;
 -- Reconcile removed/reclassified source keys while preserving rerunnable upserts.
 DELETE f FROM [$(WarehouseDatabase)].dbo.fait_stock_actuel f
 WHERE NOT EXISTS(SELECT 1 FROM dbo.v_source_stock s WHERE s.Product_Id=f.Product_Id);
 DELETE f FROM [$(WarehouseDatabase)].dbo.fait_achats f
 WHERE NOT EXISTS(SELECT 1 FROM dbo.v_source_achats s WHERE s.Id=f.Id AND s.IsValidated=1 AND s.Product_Id IS NOT NULL);
END;
GO
