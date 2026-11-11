$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$cfg=Get-Content (Join-Path $root 'settings.example.json') -Raw|ConvertFrom-Json
$g='C:\Windows\Microsoft.NET\assembly'
$m="$g\GAC_MSIL\Microsoft.SqlServer.ManagedDTS\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SqlServer.ManagedDTS.dll"
$w="$g\GAC_64\Microsoft.SqlServer.DTSRuntimeWrap\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SqlServer.DTSRuntimeWrap.dll"
$p="$g\GAC_MSIL\Microsoft.SqlServer.DTSPipelineWrap\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SQLServer.DTSPipelineWrap.dll"
Add-Type -Path $m;Add-Type -Path $w;Add-Type -Path $p
Add-Type -Path 'C:\Program Files\Microsoft SQL Server\160\DTS\Tasks\Microsoft.SqlServer.SQLTask.dll'
Add-Type -Path @((Join-Path $PSScriptRoot 'FactGraphs.cs'),(Join-Path $PSScriptRoot 'DimensionGraphs.cs')) -ReferencedAssemblies @($m,$w,$p)
$app=New-Object Microsoft.SqlServer.Dts.Runtime.Application
$file=Join-Path $root 'HealthRetailers_SSIS\ETL_SA_DW.dtsx'
$pkg=$app.LoadPackage($file,$null)
$pkg.MaxConcurrentExecutables=1
function Conn($name,$database){
 $c=$pkg.Connections.Add('OLEDB');$c.Name=$name
 $c.ConnectionString="Provider=MSOLEDBSQL;Data Source=$($cfg.Server);Initial Catalog=$database;Integrated Security=SSPI;Use Encryption for Data=False;"
 return $c
}
$source=Conn 'SA - sources ETL' $cfg.StagingDatabase
$reference=Conn 'DW - recherches ETL' $cfg.WarehouseDatabase
$writer=Conn 'DW - insertion ETL' $cfg.WarehouseDatabase
$updater=Conn 'DW - mise a jour ETL' $cfg.WarehouseDatabase
$reject=Conn 'SA - lignes exclues' $cfg.StagingDatabase
foreach($name in @('alim_dim_client','alim_dim_fournisseur','alim_dim_paiement')){
 $pkg.Executables.Remove($name)
}
$null=[DimensionGraphs]::Client($pkg,$source,$reference,$writer,$updater)
$null=[DimensionGraphs]::Supplier($pkg,$source,$reference,$writer,$updater)
$null=[DimensionGraphs]::Payment($pkg,$source,$reference,$writer,$updater)
$dimensions=@($pkg.Executables)
$prepare=$pkg.Executables.Add('Microsoft.SqlServer.Dts.Tasks.ExecuteSQLTask.ExecuteSQLTask, Microsoft.SqlServer.SQLTask, Version=16.0.0.0, Culture=neutral, PublicKeyToken=89845dcd8080cc91')
$prepare.Name='Preparation des faits';$prepare.DelayValidation=$true
$prepare.InnerObject.Connection=$source.ID
$prepare.InnerObject.SqlStatementSource='EXEC dbo.usp_preparer_faits; EXEC dbo.usp_preparer_faits_complementaires;'
foreach($dimension in $dimensions){$pkg.PrecedenceConstraints.Add($dimension,$prepare).Value='Success'}
$stock=[TeacherFacts]::Stock($pkg,$source,$reference,$writer,$updater)
$achats=[TeacherFacts]::Purchases($pkg,$source,$reference,$writer,$updater,$reject)
$ventes=[TeacherFacts]::Sales($pkg,$source,$reference,$writer,$updater,$reject)
$encaissements=[TeacherFacts]::Payments($pkg,$source,$reference,$writer,$updater,$false)
$decaissements=[TeacherFacts]::Payments($pkg,$source,$reference,$writer,$updater,$true)
$chain=@($prepare,$stock,$achats,$ventes,$encaissements,$decaissements)
for($i=1;$i -lt $chain.Count;$i++){
 $pkg.PrecedenceConstraints.Add($chain[$i-1],$chain[$i]).Value='Success'
}
$app.SaveToXml($file,$pkg,$null)
Write-Host 'Three native dimension preparations and five fact Data Flows added to ETL_SA_DW.dtsx.'
