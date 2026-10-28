$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$cfg=Get-Content (Join-Path $root 'settings.example.json') -Raw|ConvertFrom-Json
$g='C:\Windows\Microsoft.NET\assembly'
$m="$g\GAC_MSIL\Microsoft.SqlServer.ManagedDTS\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SqlServer.ManagedDTS.dll"
$w="$g\GAC_64\Microsoft.SqlServer.DTSRuntimeWrap\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SqlServer.DTSRuntimeWrap.dll"
$p="$g\GAC_MSIL\Microsoft.SqlServer.DTSPipelineWrap\v4.0_16.0.0.0__89845dcd8080cc91\Microsoft.SQLServer.DTSPipelineWrap.dll"
Add-Type -Path $m;Add-Type -Path $w;Add-Type -Path $p
Add-Type -Path 'C:\Program Files\Microsoft SQL Server\160\DTS\Tasks\Microsoft.SqlServer.SQLTask.dll'
Add-Type -Path (Join-Path $PSScriptRoot 'FactGraphs.cs') -ReferencedAssemblies @($m,$w,$p)
$app=New-Object Microsoft.SqlServer.Dts.Runtime.Application
$file=Join-Path $root 'HealthRetailers_SSIS\ETL_SA_DW.dtsx'
$pkg=$app.LoadPackage($file,$null)
$pkg.MaxConcurrentExecutables=1
function Conn($name,$database){
 $c=$pkg.Connections.Add('OLEDB');$c.Name=$name
 $c.ConnectionString="Provider=MSOLEDBSQL;Data Source=$($cfg.Server);Initial Catalog=$database;Integrated Security=SSPI;Use Encryption for Data=False;"
 return $c
}
$source=Conn 'SA - sources des faits' $cfg.StagingDatabase
$reference=Conn 'DW - recherches des faits' $cfg.WarehouseDatabase
$writer=Conn 'DW - insertion des faits' $cfg.WarehouseDatabase
$updater=Conn 'DW - mise a jour des faits' $cfg.WarehouseDatabase
$reject=Conn 'SA - lignes exclues' $cfg.StagingDatabase
$dimensions=@($pkg.Executables)
$prepare=$pkg.Executables.Add('Microsoft.SqlServer.Dts.Tasks.ExecuteSQLTask.ExecuteSQLTask, Microsoft.SqlServer.SQLTask, Version=16.0.0.0, Culture=neutral, PublicKeyToken=89845dcd8080cc91')
$prepare.Name='Preparation des deux faits';$prepare.DelayValidation=$true
$prepare.InnerObject.Connection=$source.ID;$prepare.InnerObject.SqlStatementSource='EXEC dbo.usp_preparer_faits;'
foreach($dimension in $dimensions){$pkg.PrecedenceConstraints.Add($dimension,$prepare).Value='Success'}
$stock=[TeacherFacts]::Stock($pkg,$source,$reference,$writer,$updater)
$achats=[TeacherFacts]::Purchases($pkg,$source,$reference,$writer,$updater,$reject)
$pkg.PrecedenceConstraints.Add($prepare,$stock).Value='Success'
$pkg.PrecedenceConstraints.Add($stock,$achats).Value='Success'
$app.SaveToXml($file,$pkg,$null)
Write-Host 'Two native fact Data Flows added to ETL_SA_DW.dtsx.'
