@echo off
REM Script to run individual functions from the Run class
REM This prevents accidental input from disrupting the main run.start() process

setlocal enabledelayedexpansion

REM Function to show usage
if "%~1"=="" goto :usage

set FUNCTION=%1
REM Set default events output directory
set EVENTS_OUTPUT=data/events_output
shift

REM Parse additional arguments
:parse_args
if "%~1"=="" goto :done_parsing
if "%~1"=="--events-output" (
    set EVENTS_OUTPUT=%~2
    shift
    shift
    goto :parse_args
)
REM Handle other arguments by shifting
shift
goto :parse_args

:done_parsing

REM Validate function
if "%FUNCTION%"=="review" goto :valid_function
if "%FUNCTION%"=="merge" goto :valid_function
if "%FUNCTION%"=="upload" goto :valid_function
if "%FUNCTION%"=="cleanup" goto :valid_function

echo [ERROR] Invalid function: %FUNCTION%
goto :usage

:valid_function
REM Activate virtual environment and run the function
echo [INFO] Activating virtual environment...
call venv_main\Scripts\activate 2>nul
if errorlevel 1 (
    echo [ERROR] Could not activate virtual environment venv_main
    echo [INFO] Trying without virtual environment...
)

echo [INFO] Running function: %FUNCTION%
echo [INFO] Using events output directory: %EVENTS_OUTPUT%
python Script\run_individual_functions.py %FUNCTION% --events-output "%EVENTS_OUTPUT%" %1 %2 %3 %4 %5 %6 %7 %8 %9

if errorlevel 1 (
    echo [ERROR] Function %FUNCTION% failed
    exit /b 1
) else (
    echo [SUCCESS] Function %FUNCTION% completed successfully
)

goto :end

:usage
echo Usage: %~n0 ^<function^> [options]
echo.
echo Functions:
echo   review    - Launch event review/edit interface
echo   merge     - Merge events into a single file
echo   upload    - Upload files to AWS S3
echo   cleanup   - Clean up temporary files
echo.
echo Options:
echo   --events-output ^<path^>  Path to events output directory (default: data/events_output)
echo   --merged-file ^<path^>    Path to merged events file (for upload)
echo.
echo Examples:
echo   %~n0 review                               # Use default events output directory
echo   %~n0 review --events-output "custom/events/path"
echo   %~n0 merge
echo   %~n0 upload
echo   %~n0 upload --merged-file data/events.json
echo   %~n0 cleanup
exit /b 1

:end 