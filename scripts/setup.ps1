$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Set-Location $root
$python='C:\Users\firas\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if(!(Test-Path $python)){$python='python'}
& $python (Join-Path $PSScriptRoot 'configure.py')
if($LASTEXITCODE){throw 'Configuration failed'}
$settings=Get-Content settings.example.json -Raw | ConvertFrom-Json
foreach($name in @('01_SA_Health.sql','02_DW_Health.sql','04_dimension_sources.sql','05_faits.sql')){
 & sqlcmd -S $settings.Server -E -C -b -f 65001 -v "StagingDatabase=$($settings.StagingDatabase)" "WarehouseDatabase=$($settings.WarehouseDatabase)" -i (Join-Path $root "sql\$name")
 if($LASTEXITCODE){throw "SQL setup failed: $name"}
}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'build-facts.ps1')
if($LASTEXITCODE){throw 'Fact diagram authoring failed'}
& $python (Join-Path $PSScriptRoot 'layout-facts.py')
if($LASTEXITCODE){throw 'Fact diagram layout failed'}
$vs='C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\devenv.com'
& $vs (Join-Path $root 'HealthRetailers_SSIS.sln') /Build Development /Out (Join-Path $root 'reports\build.log')
if($LASTEXITCODE){throw 'Visual Studio build failed'}
Write-Host 'Setup complete. Run scripts\verify.ps1 or execute Master.dtsx in Visual Studio.'
