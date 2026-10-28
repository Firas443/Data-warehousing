-- =====================================================================
-- Alimentation de dim_temps : du 30/09/2024 au 29/09/2026 (730 jours)
-- Rejouable : n'ajoute que les dates absentes, ne supprime rien.
-- A executer APRES 02_DW_Health.sql
-- =====================================================================
USE [$(WarehouseDatabase)];
GO

DECLARE @debut date = '2024-09-30', @fin date = '2026-09-29';

;WITH jours AS (
    SELECT @debut AS d
    UNION ALL
    SELECT DATEADD(DAY, 1, d) FROM jours WHERE d < @fin
),
annees AS (SELECT DISTINCT YEAR(d) AS Y FROM jours),
-- Calcul de Paques (algorithme gregorien)
s1 AS (SELECT Y, Y%19 AS a, Y/100 AS b, Y%100 AS c FROM annees),
s2 AS (SELECT Y, a, b, c, b/4 AS d, b%4 AS e, (b+8)/25 AS f FROM s1),
s3 AS (SELECT Y, a, b, c, d, e, f, (b-f+1)/3 AS g FROM s2),
s4 AS (SELECT Y, a, c, e, (19*a + b - d - g + 15)%30 AS h, c/4 AS i, c%4 AS k FROM s3),
s5 AS (SELECT Y, a, h, (32 + 2*e + 2*i - h - k)%7 AS l FROM s4),
s6 AS (SELECT Y, h, l, (a + 11*h + 22*l)/451 AS m FROM s5),
paques AS (
    SELECT Y, DATEFROMPARTS(Y, (h+l-7*m+114)/31, ((h+l-7*m+114)%31)+1) AS P
    FROM s6
)
INSERT INTO dbo.dim_temps (DateKey, [Date], Annee, Trimestre, Mois, SemaineISO, EstFerie)
SELECT CONVERT(int, CONVERT(char(8), j.d, 112)),
       j.d,
       YEAR(j.d),
       DATEPART(QUARTER, j.d),
       MONTH(j.d),
       DATEPART(ISO_WEEK, j.d),
       CASE WHEN MONTH(j.d)*100 + DAY(j.d) IN (101, 501, 508, 714, 815, 1101, 1111, 1225)
              OR j.d IN (DATEADD(DAY, 1,  p.P),   -- lundi de Paques
                         DATEADD(DAY, 39, p.P),   -- Ascension
                         DATEADD(DAY, 50, p.P))   -- lundi de Pentecote
            THEN 1 ELSE 0 END
FROM jours j
JOIN paques p ON p.Y = YEAR(j.d)
WHERE NOT EXISTS (SELECT 1 FROM dbo.dim_temps t
                  WHERE t.DateKey = CONVERT(int, CONVERT(char(8), j.d, 112)))
OPTION (MAXRECURSION 1000);
GO
