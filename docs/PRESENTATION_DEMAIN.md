# Présentation courte

« Nous avons repris la structure SSIS d'Amal et corrigé les problèmes de chargement. Nous partons des CSV bruts. Un premier package charge 17 sources dans une zone de staging SQL Server. Un deuxième transforme ces données et alimente les dimensions. Le Master orchestre l'ensemble et exécute les contrôles. »

## Démonstration

1. Master.dtsx : staging → calendrier → dimensions → vérification.
2. EL_SI_SA.dtsx : ouvrir un flux CSV → destination staging.
3. ETL_SA_DW.dtsx : ouvrir alim_dim_produit ou alim_dim_client pour montrer source, tri, jointure de fusion, fractionnement INSERT/UPDATE et destinations.
4. SSMS : montrer les cinq tables, les nombres de lignes et les résultats de vérification.

## Transformations à expliquer

- Conversion des identifiants texte vers des nombres.
- Nettoyage HTML et réparation de certaines séquences d'accents.
- Rapprochement des produits entre catalogue, événements et documents.
- Valeurs inconnues explicites si une information manque.
- Insertion d'une clé absente ; mise à jour des attributs modifiés, même si l'ancienne valeur était NULL.
- Clés métier conservées ; attributs remplacés sans historique : SCD type 1.

## Les deux faits implémentés

« Nous avons cinq dimensions et deux faits. Le stock actuel mesure la quantité disponible par produit et signale les produits sous leur seuil. Les achats mesurent quantité et montant HT par ligne de facture fournisseur validée, hors avoirs. »

Ouvrir aussi alim_fait_stock_actuel et alim_fait_achats : montrer les Lookup, les fractionnements INSERT/UPDATE et les colonnes dérivées. Les recherches vérifient les clés des dimensions. Le stock est un état actuel sans date de capture prouvée : sa DateKey reste NULL. Les achats s’analysent par mois et fournisseur. Les dimensions client et paiement serviront à d’autres faits ; tous les faits n’utilisent pas toutes les dimensions.

## Preuves

scripts/verify.ps1 exécute les packages natifs, contrôle toutes les cellules du staging, rejoue le Master et compare les dimensions. Il introduit trois NULL et un libellé modifié pour démontrer que les chemins UPDATE réparent les valeurs. Les résultats sont dans reports/verification-results.json.

Les tests vérifient également les mesures et les clés étrangères des faits, leur stabilité à la réexécution, la réparation de mesures modifiées et le retrait d’une facture devenue brouillon.

Pour les remises : « Le montant HT net correspond au montant de ligne moins sa part de remise globale. On contrôle que la somme des lignes égale le montant net de la facture. »
