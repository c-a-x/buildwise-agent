$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$OutputDir = Join-Path $Root "data_demo\images"
New-Item -ItemType Directory -Force $OutputDir | Out-Null

Add-Type -AssemblyName System.Drawing

function New-DemoImage {
    param(
        [string]$Path,
        [bool]$HasHazard
    )

    $bitmap = New-Object System.Drawing.Bitmap(960, 640)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try {
        $background = if ($HasHazard) { [System.Drawing.Color]::FromArgb(231, 238, 244) } else { [System.Drawing.Color]::FromArgb(226, 239, 232) }
        $graphics.Clear($background)
        $graphics.FillRectangle([System.Drawing.Brushes]::DarkSlateGray, 0, 470, 960, 170)
        $graphics.FillRectangle([System.Drawing.Brushes]::LightSteelBlue, 80, 180, 800, 22)
        $graphics.FillRectangle([System.Drawing.Brushes]::Gray, 120, 200, 18, 270)
        $graphics.FillRectangle([System.Drawing.Brushes]::Gray, 820, 200, 18, 270)
        $graphics.FillRectangle([System.Drawing.Brushes]::SteelBlue, 360, 245, 240, 225)
        $graphics.FillEllipse([System.Drawing.Brushes]::SandyBrown, 430, 150, 100, 100)
        if ($HasHazard) {
            $graphics.DrawRectangle([System.Drawing.Pens]::OrangeRed, 405, 140, 150, 345)
            $graphics.FillRectangle([System.Drawing.Brushes]::OrangeRed, 640, 105, 230, 48)
            $graphics.DrawString("NO HELMET DEMO", [System.Drawing.SystemFonts]::DefaultFont, [System.Drawing.Brushes]::White, 657, 120)
        } else {
            $graphics.FillEllipse([System.Drawing.Brushes]::Gold, 422, 135, 116, 38)
            $graphics.DrawString("NORMAL SITE DEMO", [System.Drawing.SystemFonts]::DefaultFont, [System.Drawing.Brushes]::DarkGreen, 640, 120)
        }
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Jpeg)
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

New-DemoImage (Join-Path $OutputDir "safety_no_helmet.jpg") $true
New-DemoImage (Join-Path $OutputDir "safety_normal.jpg") $false
Write-Output "Demo images created in $OutputDir"

