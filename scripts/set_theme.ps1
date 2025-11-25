param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("light","dark","blue","green","purple")]
    [string]$Theme = "light"
)
$cssDir = Join-Path (Get-Location) "static\css"
$source = Join-Path $cssDir ("theme_$Theme.css")
$dest = Join-Path $cssDir "theme.css"
if (-not (Test-Path $source)) {
    Write-Host "Theme file not found: $source" -ForegroundColor Red
    exit 1
}
Copy-Item -Path $source -Destination $dest -Force
Write-Host "Theme set to $Theme. Copied $source -> $dest"
