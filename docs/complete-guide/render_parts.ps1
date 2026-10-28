$ErrorActionPreference='Stop'
$parts=Get-Content (Join-Path $PSScriptRoot 'qa\parts.json') -Raw|ConvertFrom-Json
$app=New-Object -ComObject Word.Application
$app.Visible=$false;$app.DisplayAlerts=0;$app.AutomationSecurity=3
$pageNumber=1;$records=@()
try {
 foreach($part in $parts){
  Write-Output "Opening part $($part.part)"
  $doc=$app.Documents.Open($part.docx,$false,$true)
  try {
   $section=$doc.Sections.Item(1)
   foreach($footer in $section.Footers){if($footer.Exists){$footer.PageNumbers.RestartNumberingAtSection=$true;$footer.PageNumbers.StartingNumber=$pageNumber;$null=$footer.Range.Fields.Update()}}
   $doc.Repaginate();$pages=$doc.ComputeStatistics(2)
   $pdf=[IO.Path]::ChangeExtension($part.docx,'pdf')
   $doc.ExportAsFixedFormat($pdf,17,$false,0,0,1,999,0,$true,$false,0,$false,$false,$false)
   $records += [pscustomobject]@{Part=$part.part;Start=$pageNumber;Pages=$pages;Pdf=$pdf;Title=$part.title}
   $pageNumber += $pages
   $records|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 (Join-Path $PSScriptRoot 'qa\rendered-parts.json')
   Write-Output "Rendered part $($part.part) pages $pages"
  } finally {$doc.Close(0)}
 }
} finally {$app.Quit()}
Write-Output "Rendered $($pageNumber-1) pages."
