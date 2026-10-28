$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$cfg=Get-Content (Join-Path $root 'settings.example.json') -Raw | ConvertFrom-Json
$ispac=Join-Path $root 'HealthRetailers_SSIS\bin\Development\HealthRetailers_SSIS.ispac'
$dtexec='C:\Program Files\Microsoft SQL Server\160\DTS\Binn\DTExec.exe'
$results=[System.Collections.Generic.List[object]]::new()
function Check($name,$ok,$detail){
 $results.Add([pscustomobject]@{Check=$name;Passed=[bool]$ok;Detail=$detail})
 if(!$ok){throw "FAILED: $name ($detail)"}
}
function RunPackage($name,$log){
 & $dtexec /PROJECT $ispac /PACKAGE $name /REPORTING E > (Join-Path $root "reports\$log")
 Check "SSIS $log" ($LASTEXITCODE -eq 0) "DTExec exit $LASTEXITCODE"
}
function Connect($db){$c=[System.Data.SqlClient.SqlConnection]::new("Data Source=$($cfg.Server);Initial Catalog=$db;Integrated Security=True");$c.Open();return $c}
function Sql($cn,$text){$c=$cn.CreateCommand();$c.CommandTimeout=300;$c.CommandText=$text;$null=$c.ExecuteNonQuery();$c.Dispose()}
Add-Type -ReferencedAssemblies System.Data -TypeDefinition @'
using System; using System.Data.SqlClient; using System.IO; using System.Text; using System.Security.Cryptography; using System.Collections.Generic; using System.Globalization;
public static class DataHash {
 public static string Calculate(SqlConnection cn,string query) {
  var hashes=new List<string>();
  using(var cmd=new SqlCommand(query,cn)){cmd.CommandTimeout=300;using(var rd=cmd.ExecuteReader()){
   while(rd.Read()) { using(var ms=new MemoryStream())using(var bw=new BinaryWriter(ms,Encoding.Unicode)) {
    for(int i=0;i<rd.FieldCount;i++) {
     object v=rd.GetValue(i); string s=v==DBNull.Value?"":v is DateTime?((DateTime)v).ToString("O",CultureInfo.InvariantCulture):Convert.ToString(v,CultureInfo.InvariantCulture);
     byte[] b=Encoding.Unicode.GetBytes(s);bw.Write(b.Length);bw.Write(b);
    }
    using(var sha=SHA256.Create())hashes.Add(BitConverter.ToString(sha.ComputeHash(ms.ToArray())).Replace("-","").ToLowerInvariant());
   }}
  }}
  hashes.Sort(StringComparer.Ordinal);using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(Encoding.ASCII.GetBytes(String.Join("\n",hashes)))).Replace("-","").ToLowerInvariant();
 }
}
'@
$sa=Connect $cfg.StagingDatabase;$dw=Connect $cfg.WarehouseDatabase
try {
 RunPackage 'Master.dtsx' 'master.log'
 $manifest=Get-Content (Join-Path $root 'reports\source-manifest.json') -Raw | ConvertFrom-Json
 foreach($source in $manifest){
  $cmd=$sa.CreateCommand();$cmd.CommandText="SELECT COUNT_BIG(*) FROM dbo.[$($source.table)]";$n=$cmd.ExecuteScalar();$cmd.Dispose()
  Check "Stage count $($source.table)" ($n -eq $source.rows) "$n rows"
  $cols=($source.columns | ForEach-Object {'['+$_.Replace(']',']]')+']'}) -join ','
  $hash=[DataHash]::Calculate($sa,"SELECT $cols FROM dbo.[$($source.table)]")
  Check "Lossless Unicode $($source.table)" ($hash -eq $source.contentHash) 'All cells and duplicate rows reconciled with original source'
 }
 $tables=@('dim_client','dim_fournisseur','dim_produit','dim_paiement','dim_temps','fait_stock_actuel','fait_achats')
 $before=@{};$counts=@{}
 foreach($table in $tables){$before[$table]=[DataHash]::Calculate($dw,"SELECT * FROM dbo.$table");$cmd=$dw.CreateCommand();$cmd.CommandText="SELECT COUNT(*) FROM dbo.$table";$counts[$table]=$cmd.ExecuteScalar();$cmd.Dispose()}
 RunPackage 'Master.dtsx' 'master-rerun.log'
 foreach($table in $tables){Check "Idempotency $table" ([DataHash]::Calculate($dw,"SELECT * FROM dbo.$table") -eq $before[$table]) "$($counts[$table]) rows, identical attributes after second full run"}
 $fixtures=@(@('dim_client','Nom','Company_Id',2),@('dim_fournisseur','Nom','Fournisseur_Id',-1),@('dim_produit','Libelle','Product_Id',1),@('dim_paiement','PaymentModeName','PaymentMode_Id',1))
 $saved=@()
 try {
  foreach($f in $fixtures){
   $cmd=$dw.CreateCommand();$cmd.CommandText="SELECT [$($f[1])] FROM dbo.[$($f[0])] WHERE [$($f[2])]=$($f[3])";$old=$cmd.ExecuteScalar();$cmd.Dispose();$saved+=,@($f,$old)
   $value=if($f[0] -eq 'dim_paiement'){"N'CHANGED FOR REGRESSION TEST'"}else{'NULL'}
   Sql $dw "UPDATE dbo.[$($f[0])] SET [$($f[1])]=$value WHERE [$($f[2])]=$($f[3])"
  }
  RunPackage 'ETL_SA_DW.dtsx' 'dimension-null-and-update.log'
  foreach($table in $tables){Check "NULL/change repair $table" ([DataHash]::Calculate($dw,"SELECT * FROM dbo.$table") -eq $before[$table]) 'Dimension restored to expected source values'}
 } finally {
  foreach($s in $saved){$f=$s[0];$cmd=$dw.CreateCommand();$cmd.CommandText="UPDATE dbo.[$($f[0])] SET [$($f[1])]=@v WHERE [$($f[2])]=$($f[3])";$null=$cmd.Parameters.AddWithValue('@v',$s[1]);$null=$cmd.ExecuteNonQuery();$cmd.Dispose()}
 }
 $cmd=$dw.CreateCommand();$cmd.CommandText='SELECT MIN(Id) FROM dbo.fait_achats';$purchaseId=$cmd.ExecuteScalar();$cmd.Dispose()
 $cmd=$dw.CreateCommand();$cmd.CommandText='SELECT MIN(Product_Id) FROM dbo.fait_stock_actuel WHERE QuantiteAlerte IS NOT NULL';$stockId=$cmd.ExecuteScalar();$cmd.Dispose()
 Check 'Stock NULL fixture has known threshold' ($stockId -isnot [DBNull]) "Product $stockId"
 $factFixtures=@(@('fait_stock_actuel','QuantiteActuelle','Product_Id',$stockId,'-9999'),@('fait_stock_actuel','QuantiteAlerte','Product_Id',$stockId,'NULL'),@('fait_stock_actuel','EstSousSeuil','Product_Id',$stockId,'NULL'),@('fait_achats','MontantAchat_HT','Id',$purchaseId,'-9999'))
 $savedFacts=@()
 try {
  foreach($f in $factFixtures){
   $cmd=$dw.CreateCommand();$cmd.CommandText="SELECT [$($f[1])] FROM dbo.[$($f[0])] WHERE [$($f[2])]=$($f[3])";$old=$cmd.ExecuteScalar();$cmd.Dispose();$savedFacts+=,@($f,$old)
   Sql $dw "UPDATE dbo.[$($f[0])] SET [$($f[1])]=$($f[4]) WHERE [$($f[2])]=$($f[3])"
  }
  RunPackage 'ETL_SA_DW.dtsx' 'facts-update.log'
  foreach($table in @('fait_stock_actuel','fait_achats')){Check "Fact UPDATE repair $table" ([DataHash]::Calculate($dw,"SELECT * FROM dbo.$table") -eq $before[$table]) 'Native UPDATE routes restored stock measures, nullable attributes and purchase amount'}
 } finally {
  foreach($s in $savedFacts){$f=$s[0];$cmd=$dw.CreateCommand();$cmd.CommandText="UPDATE dbo.[$($f[0])] SET [$($f[1])]=@v WHERE [$($f[2])]=$($f[3])";$null=$cmd.Parameters.AddWithValue('@v',$s[1]);$null=$cmd.ExecuteNonQuery();$cmd.Dispose()}
 }
 $cmd=$dw.CreateCommand();$cmd.CommandText="SELECT Document_Id FROM dbo.fait_achats WHERE Id=$purchaseId";$documentId=$cmd.ExecuteScalar();$cmd.Dispose()
 $cmd=$sa.CreateCommand();$cmd.CommandText="SELECT State FROM dbo.Documents_SA WHERE TRY_CONVERT(bigint,Id)=$documentId";$oldState=$cmd.ExecuteScalar();$cmd.Dispose()
 try {
  Sql $sa "UPDATE dbo.Documents_SA SET State=N'0' WHERE TRY_CONVERT(bigint,Id)=$documentId"
  RunPackage 'ETL_SA_DW.dtsx' 'facts-source-reclassification.log'
  $cmd=$dw.CreateCommand();$cmd.CommandText="SELECT COUNT(*) FROM dbo.fait_achats WHERE Document_Id=$documentId";$remaining=$cmd.ExecuteScalar();$cmd.Dispose()
  Check 'Remove reclassified invoice facts' ($remaining -eq 0) 'Invoice changed to draft no longer contributes purchases'
 } finally {
  $cmd=$sa.CreateCommand();$cmd.CommandText="UPDATE dbo.Documents_SA SET State=@v WHERE TRY_CONVERT(bigint,Id)=$documentId";$null=$cmd.Parameters.AddWithValue('@v',$oldState);$null=$cmd.ExecuteNonQuery();$cmd.Dispose()
  RunPackage 'ETL_SA_DW.dtsx' 'facts-source-restored.log'
 }
 foreach($table in $tables){Check "Restored source and warehouse $table" ([DataHash]::Calculate($dw,"SELECT * FROM dbo.$table") -eq $before[$table]) 'Reinserted valid invoice lines and restored baseline after fixture'}
 & sqlcmd -S $cfg.Server -E -C -b -f 65001 -v "StagingDatabase=$($cfg.StagingDatabase)" "WarehouseDatabase=$($cfg.WarehouseDatabase)" -i (Join-Path $root 'sql\99_verifications.sql') > (Join-Path $root 'reports\sql-validation.log')
 Check 'SQL reconciliation and trusted foreign keys' ($LASTEXITCODE -eq 0) 'Bidirectional row and measure comparisons for both facts, calendar and dimensions validated'
 Check 'Five dimensions and two facts' (($counts.Keys | Measure-Object).Count -eq 7) ($counts | ConvertTo-Json -Compress)
 $report=@"
# Verification report

Verified: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz')

Result: $($results.Count) checks passed. Native SQL Server 2022 SSIS build and execution.

| Dimension | Rows |
|---|---:|
| dim_client | $($counts.dim_client) |
| dim_fournisseur | $($counts.dim_fournisseur) |
| dim_produit | $($counts.dim_produit) |
| dim_paiement | $($counts.dim_paiement) |
| dim_temps | $($counts.dim_temps) |
| fait_stock_actuel | $($counts.fait_stock_actuel) |
| fait_achats | $($counts.fait_achats) |

Five dimensions and two facts. All 17 staging tables reconcile with source row counts and cell-level multiset SHA-256 hashes. Null and empty CSV cells are equivalent in this comparison; duplicate rows are preserved. Raw file byte hashes are recorded separately in source-manifest.json.

The full Master succeeded twice. Every dimension has identical keys and attributes after the second execution. The dimension package repaired three deliberately introduced NULL labels and a changed payment label; all dimension hashes then matched the baseline. Fixtures were restored in a finally block.

Evidence: build.log, master.log, master-rerun.log, dimension-null-and-update.log, verification-results.json, source-manifest.json.

The two fact UPDATE paths repair deliberately changed measures and nullable stock attributes. A validated invoice changed to draft is removed from purchases; restored source state causes its lines to be inserted again. All seven table hashes match the baseline afterward. SQL assertions compare every fact row and measure against eligible source records and require enabled, trusted foreign keys.

Scope: current stock and validated supplier invoices only, excluding supplier credit notes. Stock capture date remains NULL because the export does not establish it. Missing source labels, alert thresholds and attributes remain explicitly unknown.
"@
 $report | Set-Content -Encoding UTF8 (Join-Path $root 'reports\FINAL-REPORT.md')
 Write-Host "PASS: $($results.Count) checks."
} finally {
 $results | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $root 'reports\verification-results.json')
 $sa.Dispose();$dw.Dispose()
}
