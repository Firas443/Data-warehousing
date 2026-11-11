using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Microsoft.SqlServer.Dts.Runtime;
using Microsoft.SqlServer.Dts.Runtime.Wrapper;
using Microsoft.SqlServer.Dts.Pipeline.Wrapper;
using Package=Microsoft.SqlServer.Dts.Runtime.Package;
using TaskHost=Microsoft.SqlServer.Dts.Runtime.TaskHost;

public static class TeacherFacts {
 static Edge Key(VisualGraph g,Edge from,ConnectionManager cm,string table,string key) {
  var paths=g.Lookup(from,"Recherche "+table,cm,"SELECT ["+key+"] AS RefKey FROM dbo.["+table+"]",key,"RefKey");
  paths[0].Node.Instantiate().SetComponentProperty("NoMatchBehavior",0);
  return paths[0];
 }
 static Edge SurrogateKey(VisualGraph g,Edge from,ConnectionManager cm,string table,string businessKey,string surrogateKey) {
  var paths=g.Lookup(from,"Recherche "+table+" - "+surrogateKey,cm,
   "SELECT ["+businessKey+"] AS RefKey,["+surrogateKey+"] FROM dbo.["+table+"]",
   businessKey,"RefKey",surrogateKey);
  paths[0].Node.Instantiate().SetComponentProperty("NoMatchBehavior",0);
  return paths[0];
 }
 internal static void Upsert(VisualGraph g,Edge from,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater,string table,string key,params string[] attrs) {
  var sql="SELECT ["+key+"] AS OldKey";var copy=new List<string>();
  foreach(var c in attrs){sql+=",["+c+"] AS [Old_"+c+"]";copy.Add("Old_"+c);}
  var lookupName=table.StartsWith("dim_",StringComparison.Ordinal)?"Recherche dans la dimension":"Recherche du fait existant";
  var routes=g.Lookup(from,lookupName,reference,sql+" FROM dbo.["+table+"]",key,"OldKey",copy.ToArray());
  var maps=new List<string>{key};maps.AddRange(attrs);
  g.Destination(routes[1],"INSERT - "+table,writer,"dbo.["+table+"]",maps.ToArray());
  var comparisons=new List<string>();var parameters=new List<string>();var update="UPDATE dbo.["+table+"] SET ";
  foreach(var c in attrs){
   comparisons.Add("(ISNULL(["+c+"]) ? !ISNULL([Old_"+c+"]) : (ISNULL([Old_"+c+"]) ? TRUE : ["+c+"] != [Old_"+c+"]))");
   update+="["+c+"]=?,";parameters.Add(c);
  }
  update=update.TrimEnd(',')+" WHERE ["+key+"]=?";parameters.Add(key);
  var changes=g.Split(routes[0],"Fractionnement conditionnel - valeurs modifiees","UPDATE",String.Join(" || ",comparisons));
  changes[1].Output.Name="INCHANGE - aucune ecriture";
  g.Command(changes[0],"UPDATE - "+table,updater,update,parameters.ToArray());
 }
 public static TaskHost Stock(Package pkg,ConnectionManager source,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater) {
  var g=new VisualGraph(pkg,"alim_fait_stock_actuel");
  var e=g.Source("SA - quantites et seuils par produit","SELECT Product_Id,QuantiteActuelle,QuantiteAlerte FROM dbo.v_source_stock",source);
  e=g.Derived(e,"Colonne derivee - date inconnue et alerte","DateKey=NULL(DT_I4)","EstSousSeuil=ISNULL([QuantiteAlerte]) ? NULL(DT_BOOL) : [QuantiteActuelle] < [QuantiteAlerte]");
  e=SurrogateKey(g,e,reference,"dim_produit","Product_Id","Produit_SK");
  Upsert(g,e,reference,writer,updater,"fait_stock_actuel","Product_Id","Produit_SK","DateKey","QuantiteActuelle","QuantiteAlerte","EstSousSeuil");
  return g.Task;
 }
 public static TaskHost Purchases(Package pkg,ConnectionManager source,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater,ConnectionManager reject) {
  var g=new VisualGraph(pkg,"alim_fait_achats");
  var e=g.Source("SA - lignes factures et fournisseurs","SELECT * FROM dbo.v_source_achats",source);
  e=g.Derived(e,"Colonne derivee - motif de selection","Fait=(DT_WSTR,40)\"fait_achats\"","Motif=(DT_WSTR,100)(![IsValidated] ? \"BROUILLON\" : ISNULL([Product_Id]) ? \"SANS_PRODUIT\" : \"ACCEPTE\")");
  var routes=g.Split(e,"Fractionnement conditionnel - factures valides","FACTURES VALIDEES","[Motif] == \"ACCEPTE\"");
  routes[1].Output.Name="BROUILLONS OU COMMENTAIRES";
  g.Destination(routes[1],"SA - conserver les lignes exclues",reject,"dbo.Rejets_Faits","Fait","SourceId=Id","Motif");
  e=g.Derived(routes[0],"Colonnes derivees - date et montant HT net","DateKey=(DT_I4)(YEAR([DocumentDate])*10000+MONTH([DocumentDate])*100+DAY([DocumentDate]))","QuantiteAchetee=(DT_NUMERIC,18,4)[Quantity]","MontantAchat_HT=(DT_NUMERIC,18,4)([TotalHt]-[RemiseDocument_HT])");
  e=Key(g,e,reference,"dim_temps","DateKey");
  e=SurrogateKey(g,e,reference,"dim_produit","Product_Id","Produit_SK");
  e=SurrogateKey(g,e,reference,"dim_fournisseur","Fournisseur_Id","Fournisseur_SK");
  Upsert(g,e,reference,writer,updater,"fait_achats","Id","Document_Id","DateKey","Product_Id","Produit_SK","Fournisseur_Id","Fournisseur_SK","QuantiteAchetee","MontantAchat_HT");
  return g.Task;
 }
 public static TaskHost Sales(Package pkg,ConnectionManager source,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater,ConnectionManager reject) {
  var g=new VisualGraph(pkg,"alim_fait_ventes");
  var e=g.Source("SA - lignes de vente","SELECT * FROM dbo.v_source_ventes",source);
  e=g.Derived(e,"Colonne derivee - nom du fait","Fait=(DT_WSTR,40)\"fait_ventes\"");
  var routes=g.Split(e,"Fractionnement conditionnel - ventes retenues","VENTES RETENUES","[Motif] == \"ACCEPTE\"");
  routes[1].Output.Name="LIGNES EXCLUES";
  g.Destination(routes[1],"SA - conserver les lignes exclues",reject,"dbo.Rejets_Faits","Fait","SourceId=Id","Motif");
  e=DateKey(g,routes[0],"DocumentDate");
  e=Key(g,e,reference,"dim_temps","DateKey");
  e=SurrogateKey(g,e,reference,"dim_produit","Product_Id","Produit_SK");
  e=SurrogateKey(g,e,reference,"dim_client","Company_Id","Client_SK");
  Upsert(g,e,reference,writer,updater,"fait_ventes","Id","Document_Id","DateKey","Product_Id","Produit_SK","Company_Id","Client_SK","QuantiteVendue","Remise_HT","CA_HT","Cout_HT");
  return g.Task;
 }
 static Edge DateKey(VisualGraph g,Edge e,string column) {
  var date="["+column+"]";
  return g.Derived(e,"Colonne derivee - cle de date","DateKey=(DT_I4)(YEAR("+date+")*10000+MONTH("+date+")*100+DAY("+date+"))");
 }
 public static TaskHost Payments(Package pkg,ConnectionManager source,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater,bool supplier) {
  var table=supplier?"fait_decaissements":"fait_encaissements";
  var partnerKey=supplier?"Fournisseur_Id":"Company_Id";
  var partnerSk=supplier?"Fournisseur_SK":"Client_SK";
  var g=new VisualGraph(pkg,"alim_"+table);
  var e=g.Source("SA - reglements et affectations",
   "SELECT Id,Payment_Id,Document_Id,PaymentDate,PaymentMode_Id,"+partnerKey+",Amount FROM dbo.v_source_reglements WHERE IsSupplier="+(supplier?"1":"0"),source);
  e=DateKey(g,e,"PaymentDate");
  e=Key(g,e,reference,"dim_temps","DateKey");
  e=SurrogateKey(g,e,reference,"dim_paiement","PaymentMode_Id","Paiement_SK");
  e=SurrogateKey(g,e,reference,supplier?"dim_fournisseur":"dim_client",partnerKey,partnerSk);
  Upsert(g,e,reference,writer,updater,table,"Id","Payment_Id","Document_Id","DateKey","PaymentMode_Id","Paiement_SK",partnerKey,partnerSk,"Amount");
  return g.Task;
 }
}

public class Edge {
 public IDTSComponentMetaData100 Node;
 public IDTSOutput100 Output;
 public Edge(IDTSComponentMetaData100 n,IDTSOutput100 o){Node=n;Output=o;}
}
public class VisualGraph {
 public TaskHost Task;
 public MainPipe Pipe;
 public VisualGraph(Package pkg,string name) {
  Task=(TaskHost)pkg.Executables.Add("STOCK:PipelineTask");Task.Name=name;Task.DelayValidation=true;
  Pipe=(MainPipe)Task.InnerObject;
 }
 IDTSComponentMetaData100 New(string id,string name) {
  var n=Pipe.ComponentMetaDataCollection.New();n.ComponentClassID=id;n.Instantiate().ProvideComponentProperties();n.Name=name;return n;
 }
 void Connection(IDTSComponentMetaData100 n,ConnectionManager cm) {
  n.RuntimeConnectionCollection[0].ConnectionManagerID=cm.ID;
  n.RuntimeConnectionCollection[0].ConnectionManager=DtsConvert.GetExtendedInterface(cm);
 }
 void Link(Edge e,IDTSComponentMetaData100 target) {
  Pipe.PathCollection.New().AttachPathAndPropagateNotifications(e.Output,target.InputCollection[0]);
 }
 Dictionary<string,IDTSInputColumn100> Inputs(IDTSComponentMetaData100 n) {
  var result=new Dictionary<string,IDTSInputColumn100>();var i=n.InputCollection[0];var v=i.GetVirtualInput();var w=n.Instantiate();
  foreach(IDTSVirtualInputColumn100 c in v.VirtualInputColumnCollection)
   result[c.Name]=w.SetUsageType(i.ID,v,c.LineageID,DTSUsageType.UT_READONLY);
  return result;
 }
 string Expression(IDTSComponentMetaData100 n,string friendly) {
  var input=n.InputCollection[0];var vi=input.GetVirtualInput();
  return Regex.Replace(friendly,@"\[([^\]]+)\]",m=> {
   string key=m.Groups[1].Value;
   var col=vi.VirtualInputColumnCollection[key];
   n.Instantiate().SetUsageType(input.ID,vi,col.LineageID,DTSUsageType.UT_READONLY);
   return "#"+col.LineageID;
  });
 }
 public Edge Source(string name,string sql,ConnectionManager cm) {
  var n=New("DTSAdapter.OLEDBSource.8",name);Connection(n,cm);var w=n.Instantiate();
  w.SetComponentProperty("AccessMode",2);w.SetComponentProperty("SqlCommand",sql);
  w.AcquireConnections(null);w.ReinitializeMetaData();w.ReleaseConnections();return new Edge(n,n.OutputCollection[0]);
 }
 public Edge Table(string name,string table,ConnectionManager cm,params string[] columns) {
  var n=New("DTSAdapter.OLEDBSource.8",name);Connection(n,cm);var w=n.Instantiate();
  w.SetComponentProperty("AccessMode",0);w.SetComponentProperty("OpenRowset","dbo.["+table+"]");
  w.AcquireConnections(null);w.ReinitializeMetaData();w.ReleaseConnections();
  var output=n.OutputCollection[0];
  var keep=new HashSet<string>(columns);
  var unused=new List<int>();
  foreach(IDTSOutputColumn100 col in output.OutputColumnCollection)
   if(!keep.Contains(col.Name))unused.Add(col.ID);
  foreach(int id in unused)output.OutputColumnCollection.RemoveObjectByID(id);
  var errors=n.OutputCollection[1].OutputColumnCollection;
  unused.Clear();
  foreach(IDTSOutputColumn100 col in errors)
   if(!keep.Contains(col.Name) && col.Name!="ErrorCode" && col.Name!="ErrorColumn")unused.Add(col.ID);
  foreach(int id in unused)errors.RemoveObjectByID(id);
  return new Edge(n,output);
 }
 public Edge Derived(Edge from,string name,params string[] definitions) {
  var n=New("DTSTransform.DerivedColumn.8",name);Link(from,n);var w=n.Instantiate();
  foreach(string def in definitions) {
   int at=def.IndexOf('=');string col=def.Substring(0,at),friendly=def.Substring(at+1);
   var output=n.OutputCollection[0];var c=w.InsertOutputColumnAt(output.ID,output.OutputColumnCollection.Count,col,"");
   w.SetOutputColumnProperty(output.ID,c.ID,"Expression",Expression(n,friendly));
   w.SetOutputColumnProperty(output.ID,c.ID,"FriendlyExpression",friendly);
  }
  return new Edge(n,n.OutputCollection[0]);
 }
 public Edge[] Split(Edge from,string name,string outputName,string predicate) {
  var n=New("DTSTransform.ConditionalSplit.8",name);Link(from,n);var w=n.Instantiate();
  var fallback=n.OutputCollection[0];fallback.Name="Other rows";
  var yes=w.InsertOutput(DTSInsertPlacement.IP_BEFORE,fallback.ID);yes.Name=outputName;
  w.SetOutputProperty(yes.ID,"Expression",Expression(n,predicate));
  w.SetOutputProperty(yes.ID,"FriendlyExpression",predicate);w.SetOutputProperty(yes.ID,"EvaluationOrder",0);
  return new[]{new Edge(n,yes),new Edge(n,fallback)};
 }
 public Edge[] Lookup(Edge from,string name,ConnectionManager cm,string sql,string inputKey,string refKey,params string[] copy) {
  return LookupCore(from,name,cm,sql,inputKey,refKey,false,true,copy);
 }
 public Edge OptionalLookup(Edge from,string name,ConnectionManager cm,string sql,string inputKey,string refKey,params string[] copy) {
  return LookupCore(from,name,cm,sql,inputKey,refKey,true,true,copy)[0];
 }
 Edge[] LookupCore(Edge from,string name,ConnectionManager cm,string sql,string inputKey,string refKey,bool optional,bool unique,params string[] copy) {
  var n=New("DTSTransform.Lookup.8",name);Connection(n,cm);Link(from,n);var w=n.Instantiate();
  try{w.SetComponentProperty("SqlCommand",sql);}catch(Exception ex){throw new Exception("Lookup SQL command",ex);}
  try{w.SetComponentProperty("NoMatchBehavior",optional?0:1);}catch(Exception ex){throw new Exception("Lookup no-match setting",ex);}
  try{w.SetComponentProperty("TreatDuplicateKeysAsError",unique);}catch(Exception ex){throw new Exception("Lookup duplicate-key setting",ex);}
  w.AcquireConnections(null);w.ReinitializeMetaData();
  var lookupInput=n.InputCollection[0];var lookupVirtual=lookupInput.GetVirtualInput();
  var join=w.SetUsageType(lookupInput.ID,lookupVirtual,lookupVirtual.VirtualInputColumnCollection[inputKey].LineageID,DTSUsageType.UT_READONLY);
  w.SetInputColumnProperty(lookupInput.ID,join.ID,"JoinToReferenceColumn",refKey);
  var output=n.OutputCollection[0];
  if(optional)output.ErrorRowDisposition=DTSRowDisposition.RD_IgnoreFailure;
  foreach(string col in copy) {
   var c=w.InsertOutputColumnAt(output.ID,output.OutputColumnCollection.Count,col,"");
   w.SetOutputColumnProperty(output.ID,c.ID,"CopyFromReferenceColumn",col);
  }
  w.ReleaseConnections();return new[]{new Edge(n,n.OutputCollection[0]),new Edge(n,n.OutputCollection[1])};
 }
 public Edge[] ExistsLookup(Edge from,string name,ConnectionManager cm,string sql,string inputKey,string refKey) {
  return LookupCore(from,name,cm,sql,inputKey,refKey,false,false,new string[0]);
 }
 public Edge Sort(Edge from,string name,string key,bool distinct,params string[] extra) {
  var n=New("Microsoft.Sort",name);var w=n.Instantiate();Link(from,n);
  w.SetComponentProperty("EliminateDuplicates",distinct);
  var input=n.InputCollection[0];var vi=input.GetVirtualInput();
  var cols=new List<string>{key};cols.AddRange(extra);
  foreach(var col in cols) {
   var selected=w.SetUsageType(input.ID,vi,vi.VirtualInputColumnCollection[col].LineageID,DTSUsageType.UT_READONLY);
   w.SetInputColumnProperty(input.ID,selected.ID,"NewSortKeyPosition",col==key?1:0);
  }
  return new Edge(n,n.OutputCollection[0]);
 }
 public Edge Union(string name,string[] columns,params Edge[] branches) {
  var n=New("Microsoft.UnionAll",name);var w=n.Instantiate();
  for(int i=0;i<branches.Length;i++) {
   var input=n.InputCollection[n.InputCollection.Count-1];
   Pipe.PathCollection.New().AttachPathAndPropagateNotifications(branches[i].Output,input);
   var vi=input.GetVirtualInput();
   foreach(var col in columns) {
    var selected=w.SetUsageType(input.ID,vi,vi.VirtualInputColumnCollection[col].LineageID,DTSUsageType.UT_READONLY);
    var output=n.OutputCollection[0].OutputColumnCollection[col];
    w.SetInputColumnProperty(input.ID,selected.ID,"OutputColumnLineageID",output.LineageID);
   }
  }
  return new Edge(n,n.OutputCollection[0]);
 }
 public Edge LeftJoin(Edge left,Edge right,string name,string key,string[] incoming,string[] existing) {
  var n=New("Microsoft.MergeJoin",name);var w=n.Instantiate();
  n.CustomPropertyCollection["JoinType"].Value=1;n.CustomPropertyCollection["NumKeyColumns"].Value=1;
  Pipe.PathCollection.New().AttachPathAndPropagateNotifications(left.Output,n.InputCollection[0]);
  Pipe.PathCollection.New().AttachPathAndPropagateNotifications(right.Output,n.InputCollection[1]);
  var output=n.OutputCollection[0];
  for(int i=0;i<2;i++) {
   var input=n.InputCollection[i];var vi=input.GetVirtualInput();
   foreach(var col in i==0?incoming:existing) {
    var virtualColumn=vi.VirtualInputColumnCollection[col];
    if(virtualColumn==null) {
     var available=new List<string>();
     foreach(IDTSVirtualInputColumn100 c in vi.VirtualInputColumnCollection)available.Add(c.Name);
     throw new InvalidOperationException(name+" input "+i+" is missing "+col+"; found "+String.Join(", ",available));
    }
    w.SetUsageType(input.ID,vi,virtualColumn.LineageID,DTSUsageType.UT_READONLY);
    var selected=input.InputColumnCollection.GetInputColumnByLineageID(virtualColumn.LineageID);
    foreach(IDTSOutputColumn100 projected in output.OutputColumnCollection) {
     var mapping=projected.CustomPropertyCollection["InputColumnID"];
     if(mapping!=null && Convert.ToInt32(mapping.Value)==selected.ID) {
      projected.Name=(i==0?"":"Old_")+col;
      break;
     }
    }
   }
  }
  output.IsSorted=true;
  return new Edge(n,output);
 }
 public Edge Conversion(Edge from,string name,string input,string output,DataType type,int precision,int scale) {
  var n=New("DTSTransform.DataConvert.8",name);Link(from,n);var w=n.Instantiate();var i=n.InputCollection[0];var vi=i.GetVirtualInput();
  var source=w.SetUsageType(i.ID,vi,vi.VirtualInputColumnCollection[input].LineageID,DTSUsageType.UT_READONLY);
  var o=n.OutputCollection[0];var c=w.InsertOutputColumnAt(o.ID,0,output,"");
  w.SetOutputColumnProperty(o.ID,c.ID,"SourceInputColumnLineageID",source.LineageID);
  w.SetOutputColumnDataTypeProperties(o.ID,c.ID,type,0,precision,scale,0);
  return new Edge(n,o);
 }
 public void Destination(Edge from,string name,ConnectionManager cm,string table,params string[] mapping) {
  var n=New("DTSAdapter.OLEDBDestination.8",name);Connection(n,cm);var w=n.Instantiate();
  w.SetComponentProperty("AccessMode",3);w.SetComponentProperty("OpenRowset",table);
  w.SetComponentProperty("FastLoadOptions","TABLOCK,CHECK_CONSTRAINTS");
  w.AcquireConnections(null);w.ReinitializeMetaData();Link(from,n);
  var input=n.InputCollection[0];var vi=input.GetVirtualInput();
  foreach(string m in mapping) {
   string[] pair=m.Split('=');string target=pair[0],source=pair.Length>1?pair[1]:target;
   var c=w.SetUsageType(input.ID,vi,vi.VirtualInputColumnCollection[source].LineageID,DTSUsageType.UT_READONLY);
   w.MapInputColumn(input.ID,c.ID,input.ExternalMetadataColumnCollection[target].ID);
  }
  w.ReleaseConnections();
 }
 public void Command(Edge from,string name,ConnectionManager cm,string sql,params string[] parameters) {
  var n=New("DTSTransform.OLEDBCommand.8",name);Connection(n,cm);Link(from,n);var w=n.Instantiate();
  w.SetComponentProperty("SqlCommand",sql);w.AcquireConnections(null);w.ReinitializeMetaData();
  var input=n.InputCollection[0];var vi=input.GetVirtualInput();
  for(int i=0;i<parameters.Length;i++) {
   var c=w.SetUsageType(input.ID,vi,vi.VirtualInputColumnCollection[parameters[i]].LineageID,DTSUsageType.UT_READONLY);
   w.MapInputColumn(input.ID,c.ID,input.ExternalMetadataColumnCollection[i].ID);
  }
  w.ReleaseConnections();
 }
 public void Reject(Edge from,ConnectionManager cm,string reason) {
  var e=Derived(from,"Describe rejection - "+reason,"_RejectReason=(DT_WSTR,200)\""+reason+"\"");
  Destination(e,"Rejected rows - "+reason,cm,"[visual].[RejectedRows]","SourceTable=_SourceTable","SourceId=Id","Reason=_RejectReason");
 }
 public Edge CheckKey(Edge from,ConnectionManager reference,ConnectionManager rejects,string key,string table,string reason) {
  var paths=Lookup(from,"Lookup "+table+" - "+reason,reference,"SELECT ["+key+"] AS RefKey FROM dbo.["+table+"]",key,"RefKey");
  Reject(paths[1],rejects,reason);return paths[0];
 }
 public static TaskHost Dimension(Package pkg,ConnectionManager source,ConnectionManager reference,ConnectionManager writer,ConnectionManager updater,string table,string key,string[] attrs,string[] stringAttrs) {
  var g=new VisualGraph(pkg,"Dimension - "+table);var e=g.Source("Staging candidates - "+table,"SELECT * FROM visual.["+table+"]",source);
  var strings=new HashSet<string>(stringAttrs);var derived=new List<string>();
  foreach(string c in attrs)if(strings.Contains(c))derived.Add("Clean_"+c+"=TRIM(["+c+"])");
  if(derived.Count>0)e=g.Derived(e,"Trim dimension text",derived.ToArray());
  var referenceSql="SELECT ["+key+"] AS OldKey";var copies=new List<string>();
  foreach(string c in attrs){referenceSql+=",["+c+"] AS [Old_"+c+"]";copies.Add("Old_"+c);}
  referenceSql+=" FROM dbo.["+table+"]";
  var routes=g.Lookup(e,"Lookup existing member",reference,referenceSql,key,"OldKey",copies.ToArray());
  var mapping=new List<string>{key};var comparisons=new List<string>();var parameters=new List<string>();var update="UPDATE dbo.["+table+"] SET ";
  foreach(string c in attrs) {
   string current=strings.Contains(c)?"Clean_"+c:c;mapping.Add(c+"="+current);parameters.Add(current);
   comparisons.Add("(ISNULL(["+current+"]) != ISNULL([Old_"+c+"])) || (!ISNULL(["+current+"]) && !ISNULL([Old_"+c+"]) && ["+current+"] != [Old_"+c+"]) ");
   update+="["+c+"]=?,";
  }
  update=update.TrimEnd(',')+" WHERE ["+key+"]=?";parameters.Add(key);
  g.Destination(routes[1],"Insert new dimension member",writer,"dbo.["+table+"]",mapping.ToArray());
  var changes=g.Split(routes[0],"Separate changed and unchanged members","Changed attributes",String.Join(" || ",comparisons));
  changes[1].Output.Name="Unchanged - no write required";
  g.Command(changes[0],"Update existing member",updater,update,parameters.ToArray());
  return g.Task;
 }
}
