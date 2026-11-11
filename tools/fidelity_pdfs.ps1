# The fidelity fixtures' PDFs, made by Word (4.13.0; claude/stationkeeper-pdf-fidelity-plan-4.13.html, step 1).
# For each test_samples\fidelity\F*.docx: Save as PDF with tags (pdf_word_tagged) and without (pdf_word_untagged);
# then Word's own conversion of each tagged PDF back to Word (word_reflow\F*.docx), the baseline the copy must beat.
# One hidden Word; it changes no Word or Windows settings. Usage:
#   powershell -ExecutionPolicy Bypass -File tools\fidelity_pdfs.ps1 [-Root <repo>] [-NoReflow]
param([string]$Root = (Split-Path $PSScriptRoot -Parent), [switch]$NoReflow)
$ErrorActionPreference = 'Stop'
$fx = Join-Path $Root 'test_samples\fidelity'
$tagged = Join-Path $fx 'pdf_word_tagged'; $plain = Join-Path $fx 'pdf_word_untagged'; $reflow = Join-Path $fx 'word_reflow'
foreach ($d in $tagged, $plain, $reflow) { New-Item -ItemType Directory -Force $d | Out-Null }
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    foreach ($f in Get-ChildItem $fx -Filter 'F*.docx') {
        $stem = [IO.Path]::GetFileNameWithoutExtension($f.Name)
        $doc = $word.Documents.Open($f.FullName, $false, $true)
        foreach ($pair in @(@($tagged, $true), @($plain, $false))) {
            $out = Join-Path $pair[0] "$stem.pdf"
            # ExportAsFixedFormat(path, PDF, open after, optimize for print, whole document, from, to, content,
            #   doc props, keep IRM, no bookmarks, structure tags, bitmap missing fonts, not PDF/A)
            $doc.ExportAsFixedFormat($out, 17, $false, 0, 0, 1, 1, 0, $true, $true, 0, $pair[1], $true, $false)
        }
        $doc.Close($false)
        Write-Output "PDF $stem"
    }
    if (-not $NoReflow) {
        foreach ($p in Get-ChildItem $tagged -Filter 'F*.pdf') {
            $stem = [IO.Path]::GetFileNameWithoutExtension($p.Name)
            try {
                $doc = $word.Documents.Open($p.FullName, $false, $true)    # ConfirmConversions off, read-only
                $doc.SaveAs2((Join-Path $reflow "$stem.docx"), 16)
                $doc.Close($false)
                Write-Output "REFLOW $stem"
            } catch {
                Write-Output "REFLOW_FAILED $stem $($_.Exception.Message)"
            }
        }
    }
} finally {
    $word.Quit($false)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
Write-Output 'FIDELITY_PDFS_DONE'
