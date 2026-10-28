# HealthRetailers_DW

## Description
Projet académique de Business Intelligence portant sur la création d'un Data Warehouse à partir de données HealthRetailers, avec SQL Server Integration Services (SSIS).

Le projet comprend des scripts SQL, des packages ETL et un package maître permettant d'automatiser l'exécution.

## Prérequis
- SQL Server
- SQL Server Management Studio (SSMS)
- Visual Studio avec l'extension SQL Server Integration Services Projects

## Installation et exécution

1. Cloner ou télécharger le dépôt GitHub.
2. Ouvrir `HealthRetailers_SSIS.sln` dans Visual Studio.
3. Exécuter les scripts SQL du dossier `sql/` dans l'ordre prévu.
4. Placer les fichiers CSV nécessaires dans un dossier local.
5. Dans Visual Studio, ouvrir chaque package SSIS et accéder à ses gestionnaires de connexions (*Connection Managers*).
6. Pour chaque fichier CSV, modifier la propriété **ConnectionString** afin qu'elle pointe vers le chemin local correspondant au fichier.
7. Vérifier les connexions aux bases de données et les paramètres du projet.
8. Exécuter `Master.dtsx` pour lancer les packages ETL dans l'ordre prévu.
9. Exécuter les scripts de vérification SQL pour contrôler les résultats du chargement.
    
## Organisation du projet

- `HealthRetailers_SSIS.sln` : solution Visual Studio.
- `HealthRetailers_SSIS/` : projet SSIS et packages ETL.
- `sql/` : scripts SQL de création et de vérification.
- `ETL_SI_SA.dtsx` : chargement de la zone de staging.
- `ETL_SA_DW.dtsx` : chargement du Data Warehouse.
- `Master.dtsx` : orchestration des packages ETL.

## Données

Les fichiers CSV sont utilisés comme sources de données. Le paramètre `DossierDonnees` doit pointer vers leur emplacement local.

## Auteur
Projet réalisé dans un cadre académique.
