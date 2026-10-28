# HealthRetailers — cinq dimensions et deux faits avec SSIS

Base : travail d'Amal (`amal-mh/HealthRetailers_DW`, commit `3d52d4f`). Corrections locales sur la branche `codex/fix-five-dimensions`. Le travail complet précédent reste dans le dépôt voisin `DataWarehouseProject_3AI4`.

Dépôt du projet final : https://github.com/Firas443/Data-warehousing, branche `main`. Les scripts utilisent le commit de base conservé dans l'historique et ne dépendent pas du nom du remote. Les sources métier, bases locales et fichiers temporaires de vérification documentaire restent exclus de Git.

Guide complet en anglais : [PDF](docs/complete-guide/HealthRetailers_Complete_Project_Guide_EN.pdf) et [Word modifiable](docs/complete-guide/HealthRetailers_Complete_Project_Guide_EN.docx).

## Périmètre livré

**Cinq dimensions et deux tables de faits dans `DW_Health_Dimensions`** :

| Dimension | Clé métier (clé primaire) | Attributs d'analyse |
|---|---|---|
| dim_produit | Product_Id | Libelle, Famille, Marque |
| dim_client | Company_Id | Nom, TypeClient, EstClientIdentifie |
| dim_fournisseur | Fournisseur_Id | Nom |
| dim_paiement | PaymentMode_Id | PaymentModeName |
| dim_temps | DateKey (AAAAMMJJ) | Date, Annee, Trimestre, Mois, SemaineISO, EstFerie |

Les identifiants métier sont conservés. Les modifications remplacent les attributs précédents (SCD type 1), sans historique des changements de famille ou de libellé. Calendrier : 730 jours du 30/09/2024 au 29/09/2026. Les jours fériés suivent la règle française d'origine ; à confirmer si l'entreprise utilise un autre calendrier.

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
3. **ETL_SA_DW** : quatre Data Flows, avec tris, jointures de fusion, recherches, fractionnements INSERT/UPDATE et commandes de mise à jour.
4. **Verification** : assertions SQL automatiques ; une anomalie fait échouer le package.

Le package ETL_SA_DW conserve les quatre flux de dimensions d’Amal. Après eux, une tâche de préparation précède deux nouveaux Data Flows : **alim_fait_stock_actuel** et **alim_fait_achats**. Ils utilisent colonnes dérivées, recherches Lookup, fractionnements conditionnels, destinations INSERT et commandes OLE DB UPDATE, comme les flux fournisseur/paiement existants. Les tris et Merge Joins des dimensions produit/client sont conservés.

Double-cliquer sur les tâches alim_dim_client, alim_dim_produit, alim_dim_fournisseur ou alim_dim_paiement dans ETL_SA_DW pour voir leurs diagrammes. Le calendrier est généré en SQL.

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

## Présentation et suite

- docs/DEUX_FAITS_RECOMMANDES.md : définition des deux faits maintenant implémentés.
- docs/MODELE_FAITS.md : schéma et mesures.
- sql/07_analyses.sql : requêtes de démonstration pour SSMS.
- docs/PRESENTATION_DEMAIN.md : explication courte pour l'enseignant.

Les faits sont chargés par des Data Flows natifs : stock actuel par produit, et lignes des factures fournisseur validées (type 20), hors avoirs. DateKey du stock reste NULL tant que la date de capture n’est pas confirmée. Un seuil absent ou ambigu reste NULL. La quantité provient de Quantity. Le montant HT part de PrixTotalHt, puis déduit la part de remise globale de facture. Cette remise est répartie au prorata des montants HT ; le dernier montant absorbe le résidu d’arrondi pour que la somme égale exactement TotalNetHt de la facture. La soustraction est visible dans la transformation Colonne dérivée. Aucune jointure aux paiements ne multiplie les montants.

Les contrôles SQL comparent toutes les clés et mesures des deux faits aux sources dans les deux sens, et vérifient les clés étrangères. Les tests couvrent les chemins UPDATE des faits et la suppression/réinsertion des lignes lorsqu’une facture passe de validée à brouillon puis redevient valide. La préparation retire les faits dont la source a disparu ou est devenue inéligible ; les dimensions restent en SCD type 1.

Les seuils utilisent le code produit des événements quand il est disponible, puis le libellé nettoyé comme solution de repli. CatalogueSeuils_Faits met en cache les réparations de texte en staging ; la préparation le reconstruit à chaque exécution. Les insertions et mises à jour du DW restent dans les Data Flows natifs.
