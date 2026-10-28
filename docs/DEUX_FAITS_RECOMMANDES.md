# Deux faits simples à proposer

**Recommandation : fait_stock_actuel et fait_achats.** Ces deux tables sont maintenant créées et chargées dans ETL_SA_DW.dtsx, après les cinq dimensions.

## 1. fait_stock_actuel

**Question : quels produits faut-il réapprovisionner ?**

**Grain : une ligne par produit pour l'état actuel du stock**, après agrégation des lignes ProductStocks du même produit. Pour un historique de captures, le grain deviendra produit × date de capture et la clé devra inclure cette date.

| Élément | Proposition |
|---|---|
| Clé | Product_Id pour la version état actuel |
| Dimension | dim_produit ; dim_temps seulement si la date de capture est fiable |
| QuantiteActuelle | Somme des quantités courantes du produit dans ProductStocks |
| QuantiteAlerte | Seuil du catalogue Produits, lorsqu'il est renseigné |
| EstSousSeuil | 1 si quantité < seuil ; inconnu si seuil absent |
| Sources | ProductStocks et catalogue Produits, avec les correspondances de la dimension produit |

Le seuil est non additif : on ne somme pas les seuils pour mesurer le stock. La quantité s'additionne entre produits compatibles, **pas entre plusieurs captures temporelles**. La date de dernière vente ne prouve pas la date du stock : ne pas inventer une date de capture. Un seuil absent ne vaut pas automatiquement zéro.

Exemple fictif : produit A, quantité 8, seuil 10 → réapprovisionnement à prévoir.

**Phrase pour l'enseignant :** « Cette table donne une photographie des quantités disponibles par produit. On compare le stock au seuil d'alerte et on analyse les produits par famille ou marque. »

## 2. fait_achats

**Question : combien avons-nous acheté, à quel fournisseur et pendant quelle période ?**

**Grain : une ligne de facture fournisseur validée, pour un produit.** La clé est l'identifiant de ligne DocumentItem ; Document_Id reste une référence de document. Deux lignes du même produit sur une facture restent deux lignes distinctes.

| Élément | Proposition |
|---|---|
| Clé | Identifiant unique de ligne DocumentItem |
| Dimensions | dim_temps (date de facture), dim_produit, dim_fournisseur |
| QuantiteAchetee | Quantité de la ligne |
| MontantAchat_HT | Montant HT net de ligne, remise comprise |
| PrixUnitaire_HT | Facultatif ; ne pas sommer les prix unitaires |
| Sources | Documents + DocumentItem + ProductStocks ; Transactions/Companies pour le fournisseur selon les liens source |
| Périmètre simple | Factures fournisseur validées uniquement, type 20 dans ce jeu de données, à contrôler contre DocumentTypes |

Calculer le montant depuis les champs de ligne et leurs règles de remise, puis réconcilier avec les factures. Ne pas joindre les paiements aux lignes d'achat : plusieurs paiements multiplieraient les montants. Ne pas compter les commandes/bons de réception une seconde fois comme factures.

Pour l'oral, annoncer « factures fournisseur validées, remises déduites, hors avoirs ». Si les avoirs fournisseur (type 23) sont ajoutés ensuite, inverser les signes une seule fois et parler d'achats nets.

Exemple fictif : 10 unités à 5 HT, remise de 10 % → quantité 10, montant HT net 45. Analyse : somme des montants par mois et fournisseur.

**Phrase pour l'enseignant :** « Chaque ligne représente un produit acheté sur une facture fournisseur validée. Les mesures sont la quantité et le montant HT. On les analyse par date, produit et fournisseur. »

## Pourquoi ce choix

Le stock est facile à visualiser ; les achats montrent une étoile classique et l'intégration de plusieurs sources. Ils évitent d'introduire immédiatement le coût de revient des ventes et la répartition des paiements entre factures. Les dimensions client et paiement restent disponibles pour de futurs faits de ventes et d'encaissements : chaque fait n'utilise pas obligatoirement toutes les dimensions.

## Implémentation SSIS livrée

- alim_fait_stock_actuel : source staging → colonne dérivée (date NULL et alerte) → Lookup produit → Lookup fait existant → INSERT ou fractionnement des changements → UPDATE.
- alim_fait_achats : source staging → colonne dérivée du motif → fractionnement factures validées / lignes exclues → colonnes dérivées date et mesures → Lookups date, produit, fournisseur → Lookup fait existant → INSERT ou fractionnement des changements → UPDATE.
- Les exclusions sont visibles dans SA_Health_Dimensions.dbo.Rejets_Faits. Une clé de dimension inconnue provoque un échec explicite.
- Les seuils sont rapprochés d’abord par code produit issu des événements, puis par libellé nettoyé avec le catalogue ; un seuil absent ou contradictoire entre variantes reste NULL. Aucun seuil par défaut n’est inventé.
- La préparation supprime les anciennes lignes de faits qui ne sont plus éligibles avant les upserts. Elle ne tronque pas les faits à chaque exécution.

### Remise globale : règle effectivement appliquée

Le montant HT de ligne PrixTotalHt inclut les remises de ligne. S’il existe une remise globale de facture, sa part est répartie au prorata entre les lignes commerciales. La colonne dérivée SSIS soustrait cette part. Un ajustement d’arrondi à quatre décimales sur la ligne commerciale de plus grand identifiant permet une égalité exacte avec TotalNetHt du document. Le contrôle final vérifie chaque facture séparément, et pas seulement le total général.

La table technique CatalogueSeuils_Faits, en staging, met en cache les codes, libellés réparés et seuils pour éviter de recalculer les réparations de texte à chaque recherche. Elle est reconstruite par la préparation avant chaque chargement des faits.

CodesProduits_Faits met également en cache le dernier code de chaque produit issu des événements JSON, avec une clé primaire Product_Id. Les deux caches sont rafraîchis avant les Data Flows ; cela évite de reparcourir les événements et de recalculer les réparations à chaque Lookup.
