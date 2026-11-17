# Render a .pptx to PDF (and optionally PNGs of every slide) with PowerPoint, for visual checks.
# Usage: powershell -File render_pptx.ps1 <in.pptx> <out.pdf> [<png_dir>]
param([string]$InPptx, [string]$OutPdf, [string]$PngDir = "")
$OutPdf = [System.IO.Path]::GetFullPath($OutPdf.Replace('/', '\'))
if ($PngDir -ne "") { $PngDir = [System.IO.Path]::GetFullPath($PngDir.Replace('/', '\')) }
$ppt = New-Object -ComObject PowerPoint.Application
try {
    $pres = $ppt.Presentations.Open((Resolve-Path $InPptx).Path, $true, $false, $false)
    $pres.SaveAs($OutPdf, 32)   # ppSaveAsPDF
    if ($PngDir -ne "") {
        New-Item -ItemType Directory -Force $PngDir | Out-Null
        $i = 0
        foreach ($s in $pres.Slides) {
            $i++
            $s.Export((Join-Path $PngDir ("slide_{0:D2}.png" -f $i)), "PNG", 1600, 900)
        }
    }
    $pres.Close()
} finally {
    $ppt.Quit()
}
