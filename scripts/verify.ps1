<#
.SYNOPSIS
  Runs the full verification loop: Django check, tests, smoke test.
  Returns non-zero exit code only on genuine failure.
.DESCRIPTION
  Python writes progress messages to stderr (e.g. "Creating test database...").
  PowerShell's & operator treats stderr output as NativeCommandError, which
  causes misleading "Exit code 1" reports even when the process succeeded.
  This script captures stderr alongside stdout and relies solely on
  $LASTEXITCODE to detect real failures.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
$manage = Join-Path $PSScriptRoot '..\manage.py'
$smoke  = Join-Path $PSScriptRoot '..\smoke_test.py'
$failed = $false

function Run-Step {
    param([string]$Label, [string[]]$Command)
    Write-Host "`n========== $Label ==========" -ForegroundColor Cyan
    # Redirect stderr to stdout so PowerShell does not treat it as an error
    & $Command[0] $Command[1..($Command.Length-1)] 2>&1 | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            Write-Host $_.Exception.Message
        } else {
            Write-Host $_
        }
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $Label (exit code $LASTEXITCODE)" -ForegroundColor Red
        $script:failed = $true
        return $false
    }
    Write-Host "PASSED: $Label" -ForegroundColor Green
    return $true
}

Run-Step 'Django System Check'   @($python, $manage, 'check')
Run-Step 'Portfolio Tests'       @($python, $manage, 'test', 'portfolio', '--verbosity=2')
Run-Step 'Smoke Test'            @($python, $smoke)

Write-Host ''
if ($failed) {
    Write-Host 'VERIFICATION FAILED' -ForegroundColor Red
    exit 1
} else {
    Write-Host 'ALL VERIFICATION PASSED' -ForegroundColor Green
    exit 0
}
