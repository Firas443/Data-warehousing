# HealthRetailers — cinq dimensions et cinq faits avec SSIS

Base : travail d'Amal (`amal-mh/HealthRetailers_DW`, commit `3d52d4f`). Corrections locales sur la branche `codex/fix-five-dimensions`. Le travail complet précédent reste dans le dépôt voisin `DataWarehouseProject_3AI4`.

Dépôt du projet final : https://github.com/Firas443/Data-warehousing, branche `main`. Les scripts utilisent le commit de base conservé dans l'historique et ne dépendent pas du nom du remote. Les sources métier, bases locales et fichiers temporaires de vérification documentaire restent exclus de Git.

Guide en anglais de la version initiale à deux faits : [PDF](docs/complete-guide/HealthRetailers_Complete_Project_Guide_EN.pdf) et [Word modifiable](docs/complete-guide/HealthRetailers_Complete_Project_Guide_EN.docx).

## Périmètre livré

**Cinq dimensions et cinq tables de faits dans `DW_Health_Dimensions`** :

| Dimension | Clé primaire du DW | Identifiant métier | Attributs d'analyse |
|---|---|---|---|
| dim_produit | Produit_SK | Product_Id | Libelle, Famille, Marque |
| dim_client | Client_SK | Company_Id | Nom, TypeClient, EstClientIdentifie |
| dim_fournisseur | Fournisseur_SK | Fournisseur_Id | Nom |
| dim_paiement | Paiement_SK | PaymentMode_Id | PaymentModeName |
| dim_temps | DateKey (AAAAMMJJ) | Date | Date, Annee, Trimestre, Mois, SemaineISO, EstFerie |

SQL Server génère les quatre clés de substitution avec `IDENTITY`. Les identifiants métier restent uniques dans les dimensions et servent à retrouver le membre lors du chargement SSIS. Les recherches des faits récupèrent la clé `_SK`, qui porte la relation dans le DW. Les faits conservent les identifiants métier pour le rapprochement avec le staging. Le stock utilise `Produit_SK` comme clé primaire. Le calendrier conserve `DateKey` pour les relations de date.

Les modifications remplacent les attributs précédents (SCD type 1), sans historique des changements de famille ou de libellé. Calendrier : 730 jours du 30/09/2024 au 29/09/2026. Les jours fériés suivent la règle française d'origine ; à confirmer si l'entreprise utilise un autre calendrier.

## Exécution

Prérequis : SQL Server 2022 Developer, runtime SSIS 2022 complet, Visual Studio 2022 avec SSIS Projects, Python 3 et sqlcmd. Connexion Windows intégrée.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\setup.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\verify.ps1
```

Copier `settings.example.json` vers `settings.json` pour changer serveur et bases, puis relancer `setup.ps1`. Le script configure tous les chemins SSIS ; aucun paramètre fictif DossierDonnees n'est requis. Les scripts SQL utilisent les variables SQLCMD StagingDatabase et WarehouseDatabase ; le script d'installation les fournit. Dans SSMS, activer SQLCMD Mode pour les exécuter manuellement. Aucune base existante n'est supprimée par l'installation.

Ouvrir `HealthRetailers_SSIS.sln`, puis `Master.dtsx` :

1. **EL_SI_SA** : 17 Data Flows CSV → staging `SA_Health_Dimensions`.
2. **Calendrier** : alimentation SQL rejouable de dim_temps.
3. **ETL_SA_DW** : quatre flux de dimensions et cinq flux de faits, avec tris, jointures de fusion, recherches, fractionnements INSERT/UPDATE et commandes de mise à jour.
4. **Verification** : assertions SQL automatiques ; une anomalie fait échouer le package.

Le package ETL_SA_DW charge les quatre dimensions, prépare les sources de faits, puis exécute les cinq flux ci-dessous. Ouvrir chaque tâche `alim_fait_…` dans Visual Studio pour voir les colonnes dérivées, les recherches, le fractionnement des lignes modifiées et les branches INSERT/UPDATE.

| Fait | Une ligne représente | Mesures |
|---|---|---|
| `fait_stock_actuel` | Le stock actuel d’un produit | Quantité, seuil et indicateur d’alerte |
| `fait_achats` | Une ligne de facture fournisseur validée | Quantité achetée et montant net HT |
| `fait_ventes` | Une ligne de vente ou retour validée | Quantité, remise HT, CA HT et coût HT si connu |
| `fait_encaissements` | Une affectation d’un règlement client ou son solde non affecté | Montant encaissé |
| `fait_decaissements` | Une affectation d’un règlement fournisseur ou son solde non affecté | Montant décaissé |

Les retours réduisent les ventes. Les factures regroupées sont exclues pour éviter de recompter leurs livraisons. Le coût de vente provient du mouvement de validation quand il est disponible.

Pour les règlements, `PaymentsList_SA` prévaut sur `Payment_SA` quand le même identifiant existe dans les deux exports. Les règlements supprimés sont écartés. Les affectations de `TransactionPayments_SA` sont conservées à leur montant source. Le solde entre le paiement et ses affectations est conservé séparément. Un document est référencé lorsqu’un document validé du bon côté peut être identifié de façon unique pour la transaction. La somme des affectations et du solde doit correspondre au montant de chaque règlement actif.

Double-cliquer sur une tâche `alim_dim_…` dans `ETL_SA_DW` pour voir son diagramme. Les sources OLE DB des flux client, fournisseur et paiement lisent directement les tables de staging en mode **Table ou vue**. Les recherches lisent leurs colonnes de référence. Les règles de préparation se trouvent dans les composants SSIS.

| Dimension | Préparation et chargement |
|---|---|
| Client | Fractionnement conditionnel, recherches, conversion, Union All et tri pour sélectionner les clients. Les colonnes dérivées préparent le nom et le type. Le tri des deux entrées précède la jointure de fusion gauche vers le DW. |
| Fournisseur | Fractionnement des sociétés et des documents d'achat, conversion, Union All et tri. Les colonnes dérivées nettoient les noms. Une recherche dans le DW sépare les nouveaux fournisseurs des fournisseurs existants. |
| Paiement | Fractionnement pour écarter les modes vides, colonne dérivée pour traduire les libellés, conversion de l'identifiant, tri pour dédupliquer et recherche dans le DW. |
| Produit | La source appelle la procédure SQL de préparation. Le flux SSIS conserve le tri et la jointure de fusion gauche. |
| Temps | La tâche SQL `Calendrier` dans `Master.dtsx` génère les dates. |

La petite table de référence `DimMembresSpeciaux_SA` fournit les identifiants fixes des membres inconnus et du client comptoir. Les colonnes dérivées leur attribuent leurs libellés.

## Corrections et données

- Comparaisons NULL corrigées dans les quatre chemins de mise à jour.
- Détection exacte du caractère Unicode de remplacement sous collation binaire.
- Conservation des variantes du catalogue portant le même code ; un code ambigu exige également un libellé concordant.
- Choix déterministe d'une seule ligne de catalogue par produit.
- Connexions locales configurables, cible SQL Server 2022, création SQL portable.
- Calendrier et vérifications intégrés au Master.

Les 17 CSV utilisés sont conservés sans modification dans data/original. Une copie UTF-16 de transport est générée dans data/transport ; les valeurs restent identiques. Le staging utilise NVARCHAR. Les données métier sont exclues de Git. Pour une nouvelle machine, fournir les fichiers recensés dans scripts/sources.json ; sur cette machine ils sont déjà présents.

Le staging conserve les caractères déjà abîmés à la source. Les réparations connues se font à la transformation ; les informations impossibles à retrouver restent explicitement inconnues. Aucune orthographe n'est inventée. Les suppressions de source ne purgent pas automatiquement les dimensions.

reports/verification-results.json contient les résultats réels : exécution native, rapprochement des comptes et de toutes les cellules de staging (doublons inclus), deuxième exécution identique, réparation de NULL et modification d'un paiement. Les journaux DTExec et build.log fournissent les détails.

Le [classeur de rapprochement CSV / SQL Server](reports/HealthRetailers_CSV_vs_SQL.xlsx) présente les résultats des cinq faits, le détail filtrable par mois et les règles pour reproduire les calculs dans Excel ou Power Query. Les 17 fichiers CSV totalisent 244 300 lignes dans le staging. Les champs comparés concordent pour les 50 518 lignes de faits.

## Présentation et suite

- docs/DEUX_FAITS_RECOMMANDES.md : définition des deux premiers faits.
- docs/MODELE_FAITS.md : schéma et mesures des deux premiers faits.
- sql/07_analyses.sql : requêtes de démonstration pour SSMS.
- docs/PRESENTATION_DEMAIN.md : explication courte pour l'enseignant.

Les achats couvrent les lignes des factures fournisseur validées (type 20), hors avoirs. DateKey du stock reste NULL tant que la date de capture n’est pas confirmée. Un seuil absent ou ambigu reste NULL. La quantité provient de Quantity. Le montant HT part de PrixTotalHt, puis déduit la part de remise globale de facture. Cette remise est répartie au prorata des montants HT ; le dernier montant absorbe le résidu d’arrondi pour que la somme égale exactement TotalNetHt de la facture. La soustraction est visible dans la transformation Colonne dérivée. Aucune jointure aux paiements ne multiplie les montants.

Les contrôles SQL comparent toutes les clés et mesures des cinq faits aux sources dans les deux sens, et vérifient les clés étrangères. Les tests couvrent les chemins UPDATE des faits et la suppression/réinsertion des lignes lorsqu’une facture passe de validée à brouillon puis redevient valide. La préparation retire les faits dont la source a disparu ou est devenue inéligible ; les dimensions restent en SCD type 1.

Les seuils utilisent le code produit des événements quand il est disponible, puis le libellé nettoyé comme solution de repli. CatalogueSeuils_Faits met en cache les réparations de texte en staging ; la préparation le reconstruit à chaque exécution. Les insertions et mises à jour du DW restent dans les Data Flows natifs.
