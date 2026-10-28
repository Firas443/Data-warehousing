$ErrorActionPreference='Stop'
$file=Join-Path $PSScriptRoot 'HealthRetailers_Complete_Project_Guide_EN.docx'
$pdf=Join-Path $PSScriptRoot 'HealthRetailers_Complete_Project_Guide_EN.pdf'
$localWork=Join-Path $env:TEMP ('HealthRetailersGuideRender_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $localWork | Out-Null
$localFile=Join-Path $localWork 'HealthRetailers_Complete_Project_Guide_EN.docx'
$localPdf=Join-Path $localWork 'HealthRetailers_Complete_Project_Guide_EN.pdf'
Copy-Item -LiteralPath $file -Destination $localFile
$word=$null;$document=$null
try {
 Write-Output 'Starting hidden Word instance for document rendering.'
 $word=New-Object -ComObject Word.Application
 $word.Visible=$false;$word.DisplayAlerts=0;$word.AutomationSecurity=3;$word.ScreenUpdating=$false
 $backgroundSave=$word.Options.BackgroundSave
 $word.Options.BackgroundSave=$false
 $document=$word.Documents.Open($localFile,$false,$false)
 Write-Output 'Updating contents and page fields.'
 foreach($toc in $document.TablesOfContents){$toc.Update()}
 $null=$document.Fields.Update();$document.Repaginate()
 foreach($toc in $document.TablesOfContents){$toc.UpdatePageNumbers()}
 Write-Output 'Saving paginated document.'
 $document.Save()
 Write-Output "Pagination complete: $($document.ComputeStatistics(2)) pages."
 $document.Fields.Unlink()
 Write-Output 'Exporting the document as PDF.'
 $document.ExportAsFixedFormat($localPdf,17,$false,0,0,1,63,0,$true,$false,0,$false,$false,$false)
 Write-Output 'PDF export complete.'
} finally {
 if($document){$document.Close(0);[void][Runtime.InteropServices.Marshal]::ReleaseComObject($document)}
 if($word){if($null -ne $backgroundSave){$word.Options.BackgroundSave=$backgroundSave};$word.Quit();[void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)}
 [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
Copy-Item -LiteralPath $localFile -Destination $file -Force
Copy-Item -LiteralPath $localPdf -Destination $pdf -Force
Write-Output "Final Word and PDF copies saved. Rendering workspace: $localWork"
