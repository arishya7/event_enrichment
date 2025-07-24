@echo off
REM Script to run individual functions from the Run class
REM This prevents accidental input from disrupting the main run.start() process

setlocal enabledelayedexpansion

REM Function to show usage
if "%~1"=="" goto :usage

set FUNCTION=%1
set TIMESTAMP=%2
shift
shift

REM Get timestamp - either from command line or user input
if "%TIMESTAMP%"=="" (
    echo [INFO] Available timestamps:
    if exist "data\events_output" (
        for /f "delims=" %%i in ('dir /b "data\events_output" 2^>nul ^| findstr /r "^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]$"') do echo   %%i
    ) else (
        echo [WARNING] No events output directory found
    )
    echo.
    set /p TIMESTAMP="Enter timestamp (YYYYMMDD_HHMMSS): "
    if "!TIMESTAMP!"=="" (
        echo [ERROR] Timestamp cannot be empty
        exit /b 1
    )
)

REM Validate function
if "%FUNCTION%"=="review" goto :valid_function
if "%FUNCTION%"=="merge" goto :valid_function
if "%FUNCTION%"=="upload" goto :valid_function
if "%FUNCTION%"=="cleanup" goto :valid_function

echo [ERROR] Invalid function: %FUNCTION%
goto :usage

:valid_function
REM Check if timestamp directory exists
set TIMESTAMP_DIR=data\events_output\%TIMESTAMP%
if not exist "%TIMESTAMP_DIR%" (
    echo [WARNING] Timestamp directory does not exist: %TIMESTAMP_DIR%
    echo [INFO] Make sure you have run the main process first
)

REM Activate virtual environment and run the function
echo [INFO] Activating virtual environment...
call venv_main\Scripts\activate 2>nul
if errorlevel 1 (
    echo [ERROR] Could not activate virtual environment venv_main
    echo [INFO] Trying without virtual environment...
)

echo [INFO] Running function: %FUNCTION% with timestamp: %TIMESTAMP%
python Script\run_individual_functions.py %FUNCTION% --timestamp %TIMESTAMP% %1 %2 %3 %4 %5 %6 %7 %8 %9

if errorlevel 1 (
    echo [ERROR] Function %FUNCTION% failed
    exit /b 1
) else (
    echo [SUCCESS] Function %FUNCTION% completed successfully
)

goto :end

:usage
echo Usage: %~n0 ^<function^> [timestamp] [options]
echo.
echo Functions:
echo   review    - Launch event review/edit interface
echo   merge     - Merge events into a single file
echo   upload    - Upload files to AWS S3
echo   cleanup   - Clean up temporary files
echo.
echo Options:
echo   --merged-file ^<path^>   Path to merged events file (for upload)
echo.
echo Examples:
echo   %~n0 review                               # Will prompt for timestamp
echo   %~n0 review 20250715_103130              # Use specific timestamp
echo   %~n0 merge
echo   %~n0 upload
echo   %~n0 upload 20250715_103130 --merged-file data/events.json
echo   %~n0 cleanup
exit /b 1

:end 