USE [$(StagingDatabase)];
GO
-- Fixed identifiers used by the SSIS flows for unknown and anonymous members.
IF OBJECT_ID('dbo.DimMembresSpeciaux_SA','U') IS NULL
CREATE TABLE dbo.DimMembresSpeciaux_SA(
 Dimension nvarchar(20) NOT NULL,
 MemberId int NOT NULL,
 CONSTRAINT PK_DimMembresSpeciaux_SA PRIMARY KEY(Dimension,MemberId)
);
INSERT dbo.DimMembresSpeciaux_SA(Dimension,MemberId)
SELECT s.Dimension,s.MemberId
FROM (VALUES(N'CLIENT',-1),(N'CLIENT',2),(N'FOURNISSEUR',-1),(N'PAIEMENT',-1)) s(Dimension,MemberId)
WHERE NOT EXISTS(SELECT 1 FROM dbo.DimMembresSpeciaux_SA t WHERE t.Dimension=s.Dimension AND t.MemberId=s.MemberId);
GO
