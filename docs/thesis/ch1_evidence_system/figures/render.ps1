[CmdletBinding()]
param(
    [switch]$SkipPng
)

$ErrorActionPreference = 'Stop'

# This script deliberately keeps Mermaid installation out of the repository.
$figuresRoot = $PSScriptRoot
$sourceDir = Join-Path $figuresRoot 'src'
$outputDir = Join-Path $figuresRoot 'out'
$themeFile = Join-Path $figuresRoot 'theme\ch1-theme.json'
$mermaidVersion = '11.12.0'
$bundledNode = 'C:\Users\10647\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$bundledPnpm = 'C:\Users\10647\.cache\codex-runtimes\codex-primary-runtime\dependencies\bin\fallback\pnpm.cmd'
$chromeCandidates = @(
    'C:\Program Files\Google\Chrome\Application\chrome.exe',
    'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
)

function Resolve-Node {
    if (Test-Path $bundledNode) { return $bundledNode }
    $command = Get-Command node -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }
    throw '未找到 Node.js。请安装 Node 或使用 Codex bundled runtime；未写入仓库。'
}

function Resolve-Pnpm {
    if (Test-Path $bundledPnpm) { return $bundledPnpm }
    $command = Get-Command pnpm -ErrorAction SilentlyContinue
    if ($null -ne $command) { return $command.Source }
    throw '未找到 pnpm，不能调用固定版本 Mermaid CLI。'
}

function Resolve-Chrome {
    foreach ($candidate in $chromeCandidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    throw '未找到 Chrome/Chromium。请提供可执行浏览器路径；未写入仓库。'
}

$node = Resolve-Node
$pnpm = Resolve-Pnpm
$chrome = Resolve-Chrome
# The bundled pnpm launcher resolves `node` from PATH.  Keep this change scoped
# to the child PowerShell process that runs this script.
$env:PATH = "$(Split-Path $node -Parent);$env:PATH"

if (-not (Test-Path $themeFile)) { throw "缺少 Mermaid theme：$themeFile" }
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$puppeteerConfig = Join-Path ([System.IO.Path]::GetTempPath()) 'ursa-mermaid-puppeteer-config.json'
@{
    executablePath = $chrome
    args = @('--disable-gpu', '--font-render-hinting=medium')
} | ConvertTo-Json -Depth 3 | Set-Content -Path $puppeteerConfig -Encoding utf8

try {
    Get-ChildItem -Path $sourceDir -Filter 'CH1-FIG-*.mmd' | Sort-Object Name | ForEach-Object {
        $svg = Join-Path $outputDir ($_.BaseName + '.svg')
        $png = Join-Path $outputDir ($_.BaseName + '.png')
        Write-Host "Rendering $($_.Name)"

        # pnpm dlx stores the pinned CLI in its user cache rather than node_modules in this repository.
        & $pnpm dlx --silent "@mermaid-js/mermaid-cli@$mermaidVersion" `
            -i $_.FullName -o $svg -c $themeFile -p $puppeteerConfig -w 2400 -b transparent
        if ($LASTEXITCODE -ne 0) { throw "Mermaid SVG 渲染失败：$($_.Name)" }

        if (-not $SkipPng) {
            & $pnpm dlx --silent "@mermaid-js/mermaid-cli@$mermaidVersion" `
                -i $_.FullName -o $png -c $themeFile -p $puppeteerConfig -w 2400 -b white
            if ($LASTEXITCODE -ne 0) { throw "Mermaid PNG 渲染失败：$($_.Name)" }

            Add-Type -AssemblyName System.Drawing
            $image = [System.Drawing.Image]::FromFile($png)
            $bitmap = New-Object System.Drawing.Bitmap($image.Width, $image.Height)
            $bitmap.SetResolution(300, 300)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.Clear([System.Drawing.Color]::White)
            $graphics.DrawImage($image, 0, 0, $image.Width, $image.Height)
            $graphics.Dispose(); $image.Dispose()
            $temporaryPng = "$png.tmp"
            $bitmap.Save($temporaryPng, [System.Drawing.Imaging.ImageFormat]::Png)
            $bitmap.Dispose()
            Move-Item -Force $temporaryPng $png
        }
    }

    Get-ChildItem -Path $sourceDir -Filter 'CH1-FIG-*.mmd' | Sort-Object Name | ForEach-Object {
        $svg = Join-Path $outputDir ($_.BaseName + '.svg')
        $png = Join-Path $outputDir ($_.BaseName + '.png')
        if (-not (Test-Path $svg)) { throw "缺少 SVG 输出：$svg" }
        if (-not $SkipPng -and -not (Test-Path $png)) { throw "缺少 PNG 输出：$png" }
    }
    Get-FileHash (Join-Path $sourceDir 'CH1-FIG-*.mmd') -Algorithm SHA256 | Format-Table -AutoSize
    Get-FileHash (Join-Path $outputDir 'CH1-FIG-*.*') -Algorithm SHA256 | Format-Table -AutoSize
}
finally {
    Remove-Item -LiteralPath $puppeteerConfig -Force -ErrorAction SilentlyContinue
}
