#!/usr/bin/env pwsh

# Script to run individual functions from the Run class
# This prevents accidental input from disrupting the main run.start() process

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("review", "merge", "upload", "cleanup")]
    [string]$Function,
    
    [Parameter(Mandatory=$true, Position=1)]
    [string]$Timestamp,
    
    [Parameter(Mandatory=$false)]
    [string]$MergedFile
)

# Function to show usage
function Show-Usage {
    Write-Host "Usage: .\run_functions.ps1 <function> <timestamp> [options]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Functions:" -ForegroundColor Green
    Write-Host "  review    - Launch event review/edit interface"
    Write-Host "  merge     - Merge events into a single file"
    Write-Host "  upload    - Upload files to AWS S3"
    Write-Host "  cleanup   - Clean up temporary files"
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Green
    Write-Host "  -MergedFile <path>   Path to merged events file (for upload)"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\run_functions.ps1 review 20250715_103130"
    Write-Host "  .\run_functions.ps1 merge 20250715_103130"
    Write-Host "  .\run_functions.ps1 upload 20250715_103130"
    Write-Host "  .\run_functions.ps1 upload 20250715_103130 -MergedFile data/events.json"
    Write-Host "  .\run_functions.ps1 cleanup 20250715_103130"
}

# Check if timestamp directory exists
$timestampDir = "data\events_output\$Timestamp"
if (!(Test-Path $timestampDir)) {
    Write-Host "[WARNING] Timestamp directory does not exist: $timestampDir" -ForegroundColor Yellow
    Write-Host "[INFO] Make sure you have run the main process first" -ForegroundColor Blue
}

# Activate virtual environment and run the function
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Blue

$venvPath = "venv_main\Scripts\activate"
if (Test-Path $venvPath) {
    try {
        & $venvPath
        Write-Host "[SUCCESS] Virtual environment activated" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Could not activate virtual environment venv_main" -ForegroundColor Red
        Write-Host "[INFO] Trying without virtual environment..." -ForegroundColor Blue
    }
} else {
    Write-Host "[WARNING] Virtual environment not found, proceeding without it..." -ForegroundColor Yellow
}

# Build command arguments
$args = @($Function, "--timestamp", $Timestamp)
if ($MergedFile) {
    $args += @("--merged-file", $MergedFile)
}

Write-Host "[INFO] Running function: $Function with timestamp: $Timestamp" -ForegroundColor Blue

try {
    # Run the Python script
    python Script\run_individual_functions.py @args
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Function $Function completed successfully" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Function $Function failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Error running function: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} 