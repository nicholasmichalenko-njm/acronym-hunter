# The copies Redline made of the fidelity fixtures, saved as PDF by Word, to compare page pictures (4.13.0 to 4.15.0).
# Usage: powershell -ExecutionPolicy Bypass -File tools\fidelity_copies.ps1 -Copies <folder of "<stem> - copy.docx">
param([Parameter(Mandatory = $true)][string]$Copies)
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
Start-Sleep -Milliseconds 400
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    foreach ($f in Get-ChildItem $Copies -Filter '* - copy.docx') {
        [string]$src = $f.FullName; $no = $false; $ro = $true
        $doc = $word.Documents.Open([ref]$src, [ref]$no, [ref]$ro)
        [string]$out = [IO.Path]::ChangeExtension($f.FullName, '.pdf')
        $doc.ExportAsFixedFormat($out, 17)
        $doc.Close([ref]0)
        Write-Output "COPY_PDF $($f.BaseName)"
    }
} finally {
    $word.Quit([ref]0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
Write-Output 'FIDELITY_COPIES_DONE'
