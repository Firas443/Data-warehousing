USE [$(StagingDatabase)];
GO
SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON;
GO
CREATE OR ALTER FUNCTION [dbo].[fn_reparer_accents] (@s NVARCHAR(MAX))
RETURNS NVARCHAR(MAX)
AS
BEGIN
  RETURN
  REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(
    @s COLLATE Latin1_General_100_BIN2,
    NCHAR(194)+NCHAR(176),                N'°'),
    NCHAR(195)+NCHAR(169),                N'é'),
    NCHAR(195)+NCHAR(168),                N'è'),
    NCHAR(195)+NCHAR(8240),               N'É'),
    NCHAR(195)+NCHAR(175),                N'ï'),
    NCHAR(195)+NCHAR(180),                N'ô'),
    NCHAR(195)+NCHAR(160),                N'à'),
    NCHAR(226)+NCHAR(8364)+NCHAR(8221),   N'—');
END;
GO
CREATE OR ALTER FUNCTION [dbo].[fn_texte_html] (@s NVARCHAR(MAX))
RETURNS NVARCHAR(MAX)
AS
BEGIN
  DECLARE @a INT, @b INT;
  SET @a = CHARINDEX(N'<', @s COLLATE Latin1_General_100_BIN2);
  WHILE @a > 0
  BEGIN
    SET @b = CHARINDEX(N'>', @s COLLATE Latin1_General_100_BIN2, @a);
    IF @b = 0 BREAK;
    SET @s = STUFF(@s, @a, @b - @a + 1, N' ');
    SET @a = CHARINDEX(N'<', @s COLLATE Latin1_General_100_BIN2);
  END;
  SET @s = REPLACE(REPLACE(REPLACE(REPLACE(@s, N'&#39;', N''''), N'&amp;', N'&'),
                   N'&quot;', N'"'), N'&nbsp;', N' ');
  SET @s = REPLACE(REPLACE(REPLACE(@s, N'  ', N' '), N'  ', N' '), N'  ', N' ');
  RETURN LTRIM(RTRIM(@s));
END;
GO
CREATE OR ALTER PROCEDURE [dbo].[usp_source_dim_produit]
AS
BEGIN
  SET NOCOUNT ON;

  -- 1. Produits décrits dans les événements (dernier événement par produit)
  SELECT pid, cde, lbl, lbl COLLATE Latin1_General_100_CI_AI AS k
  INTO #ev
  FROM (
    SELECT TRY_CAST(JSON_VALUE(Data,'$.id') AS INT) AS pid,
           JSON_VALUE(Data,'$.cde') AS cde,
           CAST(dbo.fn_reparer_accents(JSON_VALUE(Data,'$.lbl')) AS NVARCHAR(400)) AS lbl,
           ROW_NUMBER() OVER (PARTITION BY JSON_VALUE(Data,'$.id')
                              ORDER BY TRY_CAST(Id AS INT) DESC) AS rn
    FROM Events_SA
    WHERE EntityType = '1' AND ISJSON(Data) = 1) e
  WHERE rn = 1 AND pid IS NOT NULL;

  -- 2. Libellés des lignes de vente (HTML nettoyé une seule fois)
  SELECT DISTINCT TRY_CAST(ps.Product_Id AS INT) AS Product_Id, i.Description
  INTO #desc
  FROM DocumentItem_SA i
  JOIN ProductStocks_SA ps ON ps.Id = i.ProductStock_Id;

  SELECT Product_Id,
         CAST(dbo.fn_texte_html(Description) AS NVARCHAR(400)) AS lbl
  INTO #lg0
  FROM #desc WHERE Product_Id IS NOT NULL;

  SELECT Product_Id, lbl, lbl COLLATE Latin1_General_100_CI_AI AS k
  INTO #lg
  FROM #lg0 WHERE lbl <> N'';

  -- 3. Export Produits : conserver les lignes distinctes, même si le code a été endommagé.
  SELECT ROW_NUMBER() OVER (ORDER BY Code, Libelle, Famille, Marque) AS ExportId, Code, Libelle, Famille, Marque, Libelle COLLATE Latin1_General_100_CI_AI AS k
  INTO #exp
  FROM (
    SELECT CAST(LTRIM(RTRIM(p.Code)) AS nvarchar(200)) AS Code,
           CAST(dbo.fn_reparer_accents(LTRIM(RTRIM(p.[Libellé]))) AS NVARCHAR(400)) AS Libelle,
           CAST(NULLIF(dbo.fn_reparer_accents(LTRIM(RTRIM(p.Famille))), N'') AS NVARCHAR(200)) AS Famille,
           CAST(NULLIF(dbo.fn_reparer_accents(LTRIM(RTRIM(p.Marque))),  N'') AS NVARCHAR(200)) AS Marque,
           ROW_NUMBER() OVER (PARTITION BY LTRIM(RTRIM(p.Code)), p.[Libellé], p.Famille, p.Marque ORDER BY (SELECT 1)) AS rn
    FROM Produits_SA p) x
  WHERE rn = 1;
  CREATE INDEX ix_exp_code ON #exp(Code);
  CREATE INDEX ix_exp_k    ON #exp(k);

  -- 4. Liens possibles produit -> export (le code GUID est prioritaire)
  SELECT Product_Id, ExportId, Code, prio, sans_famille
  INTO #cand
  FROM (
    SELECT ev.pid AS Product_Id, e.ExportId, e.Code, 1 AS prio,
           CASE WHEN e.Famille IS NULL THEN 1 ELSE 0 END AS sans_famille
    FROM #ev ev JOIN #exp e ON e.Code = ev.cde AND ((SELECT COUNT(*) FROM #exp z WHERE z.Code=e.Code)=1 OR e.k=ev.k)
    UNION ALL
    SELECT lg.Product_Id, e.ExportId, e.Code, 2, CASE WHEN e.Famille IS NULL THEN 1 ELSE 0 END
    FROM #lg lg JOIN #exp e ON e.k = lg.k
    UNION ALL
    SELECT ev.pid, e.ExportId, e.Code, 3, CASE WHEN e.Famille IS NULL THEN 1 ELSE 0 END
    FROM #ev ev JOIN #exp e ON e.k = ev.k) c;

  SELECT Product_Id, ExportId, Code
  INTO #best
  FROM (SELECT Product_Id, ExportId, Code,
               ROW_NUMBER() OVER (PARTITION BY Product_Id ORDER BY prio, sans_famille, Code, ExportId) AS rn
        FROM #cand) c
  WHERE rn = 1;

  SELECT Product_Id, MAX(lbl) AS lbl INTO #l1 FROM #lg GROUP BY Product_Id;

  -- 5. Marques connues
  SELECT UPPER(BrandName) AS Marque,
         BrandName COLLATE Latin1_General_100_CI_AI AS kb,
         LEN(BrandName) AS n
  INTO #br
  FROM ProductBrands_SA
  WHERE LTRIM(RTRIM(BrandName)) <> '';

  -- 6. Résultat : un produit par ligne
  SELECT p.Product_Id,
         CAST(x.Lib AS NVARCHAR(255)) AS Libelle,
         CAST(COALESCE(e.Famille, N'NON RENSEIGNE') AS NVARCHAR(100)) AS Famille,
         CAST(COALESCE(e.Marque, br.Marque, N'NON RENSEIGNE') AS NVARCHAR(100)) AS Marque
  FROM (SELECT DISTINCT TRY_CAST(Product_Id AS INT) AS Product_Id
        FROM ProductStocks_SA WHERE TRY_CAST(Product_Id AS INT) IS NOT NULL) p
  LEFT JOIN #best b ON b.Product_Id = p.Product_Id
  LEFT JOIN #exp  e ON e.ExportId = b.ExportId
  LEFT JOIN #l1  l1 ON l1.Product_Id = p.Product_Id
  LEFT JOIN #ev  ev ON ev.pid = p.Product_Id
  CROSS APPLY (SELECT COALESCE(
        CASE WHEN e.Libelle COLLATE Latin1_General_100_BIN2 LIKE N'%' + NCHAR(65533) + N'%'
               OR e.Libelle COLLATE Latin1_General_100_BIN2 LIKE N'%' + NCHAR(239) + NCHAR(191) + NCHAR(189) + N'%'
             THEN NULL ELSE e.Libelle END,
        l1.lbl, ev.lbl,
        N'PRODUIT INCONNU ' + CAST(p.Product_Id AS NVARCHAR(10))) AS Lib) x
  OUTER APPLY (SELECT TOP 1 bb.Marque FROM #br bb
               WHERE LEFT(x.Lib, bb.n + 1) COLLATE Latin1_General_100_CI_AI = bb.kb + N' '
               ORDER BY bb.n DESC) br
  ORDER BY p.Product_Id;
END;
GO
