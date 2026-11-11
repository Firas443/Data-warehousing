using System;
using Microsoft.SqlServer.Dts.Runtime;
using Microsoft.SqlServer.Dts.Runtime.Wrapper;
using Package=Microsoft.SqlServer.Dts.Runtime.Package;
using TaskHost=Microsoft.SqlServer.Dts.Runtime.TaskHost;

public static class DimensionGraphs {
 static string Empty(string col) {
  return "(ISNULL(["+col+"]) ? TRUE : TRIM(["+col+"]) == \"\")";
 }
 static string Repair(string value) {
  string[] broken={"\u00c2\u00b0","\u00c3\u00a9","\u00c3\u00a8","\u00c3\u2030","\u00c3\u00af","\u00c3\u00b4","\u00c3\u00a0","\u00e2\u20ac\u201d"};
  string[] correct={"\u00b0","\u00e9","\u00e8","\u00c9","\u00ef","\u00f4","\u00e0","\u2014"};
  for(int i=0;i<broken.Length;i++)value="REPLACE("+value+",\""+broken[i]+"\",\""+correct[i]+"\")";
  return value;
 }
 static Edge Seeds(VisualGraph g,ConnectionManager sa,string dimension) {
  var seed=g.Table("SA - membres speciaux","DimMembresSpeciaux_SA",sa,"Dimension","MemberId");
  return g.Split(seed,"Fractionnement - membres de la dimension","MEMBRES DE "+dimension,"[Dimension] == \""+dimension+"\"")[0];
 }
 static Edge Candidate(VisualGraph g,Edge e,string name,string text) {
  e=g.Derived(e,"Colonne derivee - "+name,"IdTexte="+text);
  e=g.Conversion(e,"Conversion de donnees - "+name,"IdTexte","CandidateId",DataType.DT_I4,0,0);
  return g.Sort(e,"Trier - "+name,"CandidateId",true);
 }
 static Edge PartnerId(VisualGraph g,Edge e,ConnectionManager sa,bool client) {
  if(client) {
   e=g.ExistsLookup(e,"Recherche - exclure les factures regroupees",sa,
    "SELECT Document1_Id FROM dbo.RelatedDocuments_SA","Document_Id","Document1_Id")[1];
  }
  const string sql="SELECT Id AS TransactionKey,Company_Id AS SourceCompany FROM dbo.Transactions_SA";
  if(client) {
   e=g.OptionalLookup(e,"Recherche - societe de la transaction",sa,sql,"SourceTransaction","TransactionKey","SourceCompany");
   return Candidate(g,e,"clients des ventes",Empty("SourceCompany")+" ? (DT_WSTR,4000)\"-1\" : TRIM([SourceCompany])");
  }
  e=g.Lookup(e,"Recherche - societe de la transaction",sa,sql,"Transaction_Id","TransactionKey","SourceCompany")[0];
  e=g.Split(e,"Fractionnement - societe renseignee","AVEC FOURNISSEUR","!"+Empty("SourceCompany"))[0];
  return Candidate(g,e,"fournisseurs des achats","TRIM([SourceCompany])");
 }
 static Edge PartnerDetails(VisualGraph g,Edge e,ConnectionManager sa,string catalogue) {
  e=g.Derived(e,"Colonne derivee - cle texte pour la recherche","CompanyKey=(DT_WSTR,4000)[CandidateId]");
  e=g.OptionalLookup(e,"Recherche - fiche societe",sa,
   "SELECT Id AS CompanyRef,Code AS CompanyCode,Name AS CompanyName FROM dbo.CompaniesList_SA",
   "CompanyKey","CompanyRef","CompanyCode","CompanyName");
  return g.OptionalLookup(e,"Recherche - libelle dans le catalogue",sa,
   "SELECT Code AS CatalogCode,Nom AS CatalogName FROM dbo."+catalogue,"CompanyCode","CatalogCode","CatalogName");
 }
 public static TaskHost Client(Package pkg,ConnectionManager sa,ConnectionManager dw,ConnectionManager writer,ConnectionManager updater) {
  var g=new VisualGraph(pkg,"alim_dim_client");
  var sales=g.Table("SA - lignes de documents","DocumentItem_SA",sa,"Document_Id","ProductStock_Id");
  sales=g.Split(sales,"Fractionnement - lignes avec produit","LIGNES PRODUIT","!"+Empty("ProductStock_Id"))[0];
  sales=g.Sort(sales,"Trier - un identifiant par document","Document_Id",true);
  sales=g.Lookup(sales,"Recherche - document de la ligne",sa,
   "SELECT Id AS DocumentKey,Transaction_Id AS SourceTransaction,DocumentType_Id AS DocType,State AS DocState FROM dbo.Documents_SA",
   "Document_Id","DocumentKey","SourceTransaction","DocType","DocState")[0];
  sales=g.Split(sales,"Fractionnement - ventes validees","VENTES VALIDEES",
   "[DocState] == \"1\" && ([DocType] == \"1\" || [DocType] == \"4\" || [DocType] == \"5\" || [DocType] == \"6\" || [DocType] == \"7\")")[0];
  sales=PartnerId(g,sales,sa,true);

  var catalogue=g.Table("SA - societes du catalogue","CompaniesList_SA",sa,"Id","Code");
  catalogue=g.Lookup(catalogue,"Recherche - code du catalogue client",sa,
   "SELECT Code FROM dbo.Clients_SA","Code","Code")[0];
  catalogue=Candidate(g,catalogue,"clients du catalogue","TRIM([Id])");
  var seeds=Seeds(g,sa,"CLIENT");
  seeds=g.Derived(seeds,"Colonne derivee - identifiants speciaux","CandidateId=[MemberId]");
  seeds=g.Sort(seeds,"Trier - identifiants speciaux","CandidateId",true);
  var e=g.Union("Union All - ventes catalogue et membres speciaux",new[]{"CandidateId"},sales,catalogue,seeds);
  e=g.Sort(e,"Trier - un client par identifiant","CandidateId",true);
  e=PartnerDetails(g,e,sa,"Clients_SA");
  e=g.Derived(e,"Colonne derivee - nettoyer les libelles",
   "NomRepare="+Repair("TRIM([CatalogName])"),"NomSociete=TRIM(REPLACE([CompanyName],\"|\",\"\"))");
  e=g.Derived(e,"Colonne derivee - retirer le prefixe du catalogue",
   "NomCatalogue=TRIM(SUBSTRING([NomRepare],FINDSTRING([NomRepare],\"\u2014\",1)+1,200))");
  e=g.Derived(e,"Colonnes derivees - nom type et identification",
   "Company_Id=[CandidateId]",
   "Nom=(DT_WSTR,200)([CandidateId] == -1 ? \"NON RENSEIGNE\" : [CandidateId] == 2 ? \"Client comptoir (anonyme)\" : !"+Empty("NomCatalogue")+" ? [NomCatalogue] : !"+Empty("NomSociete")+" ? [NomSociete] : \"NON RENSEIGNE\")",
   "TypeClient=(DT_WSTR,30)([CandidateId] == -1 ? \"NON RENSEIGNE\" : [CandidateId] == 2 ? \"COMPTOIR_ANONYME\" : ISNULL([NomRepare]) ? \"NON RENSEIGNE\" : FINDSTRING(UPPER([NomRepare]),\"CLIENT PARTICULIER\",1)>0 ? \"PARTICULIER\" : FINDSTRING(UPPER([NomRepare]),\"LABORATOIRE\",1)>0 ? \"B2B - LABORATOIRE\" : \"NON RENSEIGNE\")",
   "EstClientIdentifie=(DT_BOOL)([CandidateId] != -1 && [CandidateId] != 2)");
  var attrs=new[]{"Nom","TypeClient","EstClientIdentifie"};
  var cols=new[]{"Company_Id","Nom","TypeClient","EstClientIdentifie"};
  e=g.Sort(e,"Trier - clients prepares","Company_Id",false,attrs);
  var old=g.Table("DW - dimension client","dim_client",dw,cols);
  old=g.Sort(old,"Trier - clients du DW","Company_Id",false,attrs);
  e=g.LeftJoin(e,old,"Jointure de fusion - gauche","Company_Id",cols,cols);
  var routes=g.Split(e,"Fractionnement - client nouveau ou modifie","INSERT","ISNULL([Old_Company_Id])");
  g.Destination(routes[0],"INSERT - dim_client",writer,"dbo.dim_client",cols);
  var changes=g.Split(routes[1],"Fractionnement - attributs modifies","UPDATE",
   "ISNULL([Old_Nom]) || [Nom] != [Old_Nom] || [TypeClient] != [Old_TypeClient] || [EstClientIdentifie] != [Old_EstClientIdentifie]");
  g.Command(changes[0],"UPDATE - dim_client",updater,"UPDATE dbo.dim_client SET Nom=?,TypeClient=?,EstClientIdentifie=? WHERE Company_Id=?",
   "Nom","TypeClient","EstClientIdentifie","Company_Id");
  return g.Task;
 }
 public static TaskHost Supplier(Package pkg,ConnectionManager sa,ConnectionManager dw,ConnectionManager writer,ConnectionManager updater) {
  var g=new VisualGraph(pkg,"alim_dim_fournisseur");
  var companies=g.Table("SA - liste des societes","CompaniesList_SA",sa,"Id","CompanyType_Id");
  companies=g.Split(companies,"Fractionnement - societes fournisseurs","FOURNISSEURS","TRIM([CompanyType_Id]) == \"2\"")[0];
  companies=Candidate(g,companies,"societes fournisseurs","TRIM([Id])");
  var purchases=g.Table("SA - documents","Documents_SA",sa,"Transaction_Id","DocumentType_Id","State");
  purchases=g.Split(purchases,"Fractionnement - achats valides","ACHATS VALIDES",
   "[State] == \"1\" && ([DocumentType_Id] == \"20\" || [DocumentType_Id] == \"23\")")[0];
  purchases=PartnerId(g,purchases,sa,false);
  var seeds=Seeds(g,sa,"FOURNISSEUR");
  seeds=g.Derived(seeds,"Colonne derivee - fournisseur inconnu","CandidateId=[MemberId]");
  seeds=g.Sort(seeds,"Trier - fournisseur inconnu","CandidateId",true);
  var e=g.Union("Union All - societes achats et membre inconnu",new[]{"CandidateId"},companies,purchases,seeds);
  e=g.Sort(e,"Trier - un fournisseur par identifiant","CandidateId",true);
  e=PartnerDetails(g,e,sa,"Fournisseurs_SA");
  e=g.Derived(e,"Colonnes derivees - retirer le numero et nettoyer la societe",
   "NomSansNumero=ISNULL([CatalogName]) ? NULL(DT_WSTR,4000) : FINDSTRING(\"0123456789\",SUBSTRING([CatalogName],1,1),1)>0 && FINDSTRING([CatalogName],\". \",1)>0 ? TRIM(SUBSTRING([CatalogName],FINDSTRING([CatalogName],\". \",1)+2,200)) : TRIM([CatalogName])",
   "NomSociete=TRIM(REPLACE([CompanyName],\"|\",\"\"))");
  e=g.Derived(e,"Colonne derivee - reparer les accents","NomRepare="+Repair("[NomSansNumero]"));
  e=g.Derived(e,"Colonnes derivees - identifiant et nom fournisseur",
   "Fournisseur_Id=[CandidateId]",
   "Nom=(DT_WSTR,200)([CandidateId] == -1 ? \"NON RENSEIGNE\" : !ISNULL([NomRepare]) ? [NomRepare] : !ISNULL([NomSociete]) ? [NomSociete] : \"FOURNISSEUR INCONNU \" + (DT_WSTR,10)[CandidateId])");
  TeacherFacts.Upsert(g,e,dw,writer,updater,"dim_fournisseur","Fournisseur_Id","Nom");
  return g.Task;
 }
 public static TaskHost Payment(Package pkg,ConnectionManager sa,ConnectionManager dw,ConnectionManager writer,ConnectionManager updater) {
  var g=new VisualGraph(pkg,"alim_dim_paiement");
  var e=g.Table("SA - modes des paiements","PaymentsList_SA",sa,"PaymentMode_Id","PaymentMethodName");
  e=g.Split(e,"Fractionnement - modes renseignes","MODES RENSEIGNES","!"+Empty("PaymentMode_Id"))[0];
  e=g.Derived(e,"Colonnes derivees - texte et libelle lisible","IdTexte=TRIM([PaymentMode_Id])",
   "PaymentModeName=(DT_WSTR,50)(TRIM([PaymentMethodName]) == \"Core.PaymentMode.Cheque\" ? \"Ch\u00e8que\" : TRIM([PaymentMethodName]) == \"Core.PaymentMode.Cash.Tunisia\" ? \"Esp\u00e8ces\" : TRIM([PaymentMethodName]) == \"Core.PaymentMode.BankCard\" ? \"Carte bancaire\" : TRIM([PaymentMethodName]) == \"Core.PaymentMode.Credit\" ? \"Cr\u00e9dit (paiement diff\u00e9r\u00e9)\" : TRIM([PaymentMethodName]) == \"Core.PaymentMode.Jetons\" ? \"Jetons\" : TRIM([PaymentMethodName]))");
  e=g.Conversion(e,"Conversion de donnees - code du mode","IdTexte","ModeIdConverti",DataType.DT_I4,0,0);
  e=g.Sort(e,"Trier - un libelle par mode","ModeIdConverti",true,"PaymentModeName");
  e=g.Derived(e,"Colonne derivee - cle du mode","PaymentMode_Id=[ModeIdConverti]");
  e=g.Sort(e,"Trier - projeter le mode et son libelle","PaymentMode_Id",false,"PaymentModeName");
  var seed=Seeds(g,sa,"PAIEMENT");
  seed=g.Derived(seed,"Colonnes derivees - mode inconnu","PaymentMode_Id=[MemberId]","PaymentModeName=(DT_WSTR,50)\"Non renseign\u00e9\"");
  seed=g.Sort(seed,"Trier - mode inconnu","PaymentMode_Id",false,"PaymentModeName");
  e=g.Union("Union All - modes connus et inconnu",new[]{"PaymentMode_Id","PaymentModeName"},e,seed);
  TeacherFacts.Upsert(g,e,dw,writer,updater,"dim_paiement","PaymentMode_Id","PaymentModeName");
  return g.Task;
 }
}
