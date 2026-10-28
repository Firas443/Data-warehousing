$ErrorActionPreference='Stop'
$file=Join-Path $PSScriptRoot 'HealthRetailers_Complete_Project_Guide_EN.docx'
$folder=Join-Path $PSScriptRoot 'qa\chunks'
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$w=New-Object -ComObject Word.Application
$w.Visible=$false;$w.DisplayAlerts=0;$w.AutomationSecurity=3
$d=$w.Documents.Open($file,$false,$true)
try {
 $d.Repaginate()
 Write-Output "Pages $($d.ComputeStatistics(2))"
 $d.ExportAsFixedFormat((Join-Path $folder 'probe-first-page.pdf'),17,$false,0,3,1,1,0,$true,$false,0,$false,$false,$false)
 Write-Output 'First page exported'
} finally {$d.Close(0);$w.Quit()}
