USE [$(WarehouseDatabase)];
GO
SET XACT_ABORT ON;
SET NOCOUNT ON;

-- A completed migration keeps its existing key assignments on subsequent setup runs.
IF COL_LENGTH(N'dbo.dim_produit',N'Produit_SK') IS NOT NULL RETURN;

DECLARE @dimensions TABLE (TableName sysname, BusinessKey sysname, SurrogateKey sysname);
INSERT @dimensions VALUES
 (N'dim_produit',N'Product_Id',N'Produit_SK'),
 (N'dim_client',N'Company_Id',N'Client_SK'),
 (N'dim_paiement',N'PaymentMode_Id',N'Paiement_SK'),
 (N'dim_fournisseur',N'Fournisseur_Id',N'Fournisseur_SK');

DECLARE @links TABLE (FactName sysname, DimensionName sysname, ConstraintName sysname);
INSERT @links VALUES
 (N'fait_stock_actuel',N'dim_produit',N'FK_stock_produit'),
 (N'fait_achats',N'dim_produit',N'FK_achats_produit'),
 (N'fait_achats',N'dim_fournisseur',N'FK_achats_fournisseur'),
 (N'fait_ventes',N'dim_produit',N'FK_ventes_produit'),
 (N'fait_ventes',N'dim_client',N'FK_ventes_client'),
 (N'fait_encaissements',N'dim_client',N'FK_encaissements_client'),
 (N'fait_encaissements',N'dim_paiement',N'FK_encaissements_paiement'),
 (N'fait_decaissements',N'dim_fournisseur',N'FK_decaissements_fournisseur'),
 (N'fait_decaissements',N'dim_paiement',N'FK_decaissements_paiement');

DECLARE @fact sysname,@dim sysname,@constraint sysname,@business sysname,@sk sysname,@pk sysname,@sql nvarchar(max);
BEGIN TRY
 BEGIN TRANSACTION;

 -- Remove the old business-key foreign keys before moving the dimension primary keys.
 DECLARE old_links CURSOR LOCAL FAST_FORWARD FOR SELECT FactName,ConstraintName FROM @links;
 OPEN old_links;
 FETCH NEXT FROM old_links INTO @fact,@constraint;
 WHILE @@FETCH_STATUS=0
 BEGIN
  SET @sql=N'ALTER TABLE dbo.'+QUOTENAME(@fact)+N' DROP CONSTRAINT '+QUOTENAME(@constraint)+N';';
  EXEC sys.sp_executesql @sql;
  FETCH NEXT FROM old_links INTO @fact,@constraint;
 END;
 CLOSE old_links;
 DEALLOCATE old_links;

 DECLARE dims CURSOR LOCAL FAST_FORWARD FOR SELECT TableName,BusinessKey,SurrogateKey FROM @dimensions;
 OPEN dims;
 FETCH NEXT FROM dims INTO @dim,@business,@sk;
 WHILE @@FETCH_STATUS=0
 BEGIN
  SELECT @pk=name FROM sys.key_constraints WHERE parent_object_id=OBJECT_ID(N'dbo.'+@dim) AND type=N'PK';
  SET @sql=N'ALTER TABLE dbo.'+QUOTENAME(@dim)+N' ADD '+QUOTENAME(@sk)+N' int IDENTITY(1,1) NOT NULL;'
   +N'ALTER TABLE dbo.'+QUOTENAME(@dim)+N' DROP CONSTRAINT '+QUOTENAME(@pk)+N';'
   +N'ALTER TABLE dbo.'+QUOTENAME(@dim)+N' ADD CONSTRAINT '+QUOTENAME(N'PK_'+@dim)+N' PRIMARY KEY ('+QUOTENAME(@sk)+N');'
   +N'ALTER TABLE dbo.'+QUOTENAME(@dim)+N' ADD CONSTRAINT '+QUOTENAME(N'UQ_'+@dim+N'_business')+N' UNIQUE ('+QUOTENAME(@business)+N');';
  EXEC sys.sp_executesql @sql;
  FETCH NEXT FROM dims INTO @dim,@business,@sk;
 END;
 CLOSE dims;
 DEALLOCATE dims;

 -- Keep source IDs for reconciliation, while the foreign keys point to the warehouse identities.
 DECLARE new_links CURSOR LOCAL FAST_FORWARD FOR
  SELECT l.FactName,l.DimensionName,l.ConstraintName,d.BusinessKey,d.SurrogateKey
  FROM @links l JOIN @dimensions d ON d.TableName=l.DimensionName;
 OPEN new_links;
 FETCH NEXT FROM new_links INTO @fact,@dim,@constraint,@business,@sk;
 WHILE @@FETCH_STATUS=0
 BEGIN
  SET @sql=N'ALTER TABLE dbo.'+QUOTENAME(@fact)+N' ADD '+QUOTENAME(@sk)+N' int NULL;';
  EXEC sys.sp_executesql @sql;
  SET @sql=N'UPDATE f SET '+QUOTENAME(@sk)+N'=d.'+QUOTENAME(@sk)+N' FROM dbo.'+QUOTENAME(@fact)+N' f'
   +N' JOIN dbo.'+QUOTENAME(@dim)+N' d ON d.'+QUOTENAME(@business)+N'=f.'+QUOTENAME(@business)+N';'
   +N'ALTER TABLE dbo.'+QUOTENAME(@fact)+N' ALTER COLUMN '+QUOTENAME(@sk)+N' int NOT NULL;'
   +N'ALTER TABLE dbo.'+QUOTENAME(@fact)+N' WITH CHECK ADD CONSTRAINT '+QUOTENAME(@constraint)
   +N' FOREIGN KEY ('+QUOTENAME(@sk)+N') REFERENCES dbo.'+QUOTENAME(@dim)+N' ('+QUOTENAME(@sk)+N');';
  EXEC sys.sp_executesql @sql;
  FETCH NEXT FROM new_links INTO @fact,@dim,@constraint,@business,@sk;
 END;
 CLOSE new_links;
 DEALLOCATE new_links;

 ALTER TABLE dbo.fait_stock_actuel DROP CONSTRAINT PK_fait_stock_actuel;
 EXEC sys.sp_executesql N'ALTER TABLE dbo.fait_stock_actuel ADD CONSTRAINT PK_fait_stock_actuel PRIMARY KEY (Produit_SK);';
 ALTER TABLE dbo.fait_stock_actuel ADD CONSTRAINT UQ_fait_stock_actuel_product UNIQUE(Product_Id);
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
GO
