param(
  [Parameter(Mandatory=$true)][string]$Docx,
  [Parameter(Mandatory=$true)][string]$Pdf
)
$ErrorActionPreference = 'Stop'
$docxPath = (Resolve-Path -LiteralPath $Docx).Path
$pdfPath  = [System.IO.Path]::GetFullPath($Pdf)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($docxPath, $false, $true)
  $doc.ExportAsFixedFormat($pdfPath, 17)
  $doc.Close(0)
  Write-Host "pdf written: $pdfPath"
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}