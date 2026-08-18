<#
  Install the panel for local development on Windows.

  Unsigned extensions only load when PlayerDebugMode is on, so this sets that
  flag for every CSXS version Premiere might be using, then copies the panel
  into the per-user CEP extensions folder.

  Run from a normal PowerShell prompt (no admin needed - everything is HKCU):
    powershell -ExecutionPolicy Bypass -File .\install.ps1
#>

$ErrorActionPreference = 'Stop'

$bundle = 'com.thinksharper.talkinghead'
$src    = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest   = Join-Path $env:APPDATA "Adobe\CEP\extensions\$bundle"

Write-Host 'Enabling PlayerDebugMode...'
foreach ($v in 9, 10, 11, 12) {
    $key = "HKCU:\Software\Adobe\CSXS.$v"
    if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
    Set-ItemProperty -Path $key -Name 'PlayerDebugMode' -Value '1' -Type String
}

Write-Host "Installing to $dest"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Path $dest -Force | Out-Null

foreach ($item in 'CSXS', 'css', 'js', 'jsx', 'index.html', '.debug') {
    Copy-Item -Path (Join-Path $src $item) -Destination $dest -Recurse -Force
}

Write-Host ''
Write-Host 'Done. Restart Premiere Pro, then open:'
Write-Host '  Window > Extensions > Talking Head Overlay'
Write-Host ''
Write-Host 'To debug the panel UI, browse to http://localhost:8088 while it is open.'
