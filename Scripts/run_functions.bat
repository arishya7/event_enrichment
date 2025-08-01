@echo off
REM Script to run individual functions from the Run class
REM This prevents accidental input from disrupting the main run.start() process

setlocal enabledelayedexpansion

REM Function to show usage
if "%~1"=="" goto :usage

set FUNCTION=%1
REM Set default events output directory
set EVENTS_OUTPUT=data/events_output
set MERGED_FILEPATH=
set FOLDER_NAME=
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
if "%~1"=="--merged-filepath" (
    set MERGED_FILEPATH=%~2
    shift
    shift
    goto :parse_args
)
REM For review and merge functions, the first argument is the folder name
if "%FUNCTION%"=="review" (
    if "%FOLDER_NAME%"=="" (
        set FOLDER_NAME=%~1
        shift
        goto :parse_args
    )
)
if "%FUNCTION%"=="merge" (
    if "%FOLDER_NAME%"=="" (
        set FOLDER_NAME=%~1
        shift
        goto :parse_args
    )
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
call venv\Scripts\activate 2>nul
if errorlevel 1 (
    echo [ERROR] Could not activate virtual environment venv
    echo [INFO] Trying without virtual environment...
)

echo [INFO] Running function: %FUNCTION%

REM Build command based on function
if "%FUNCTION%"=="review" (
    if "%FOLDER_NAME%"=="" (
        echo [ERROR] Review function requires a folder name argument
        echo [ERROR] Usage: %~n0 review ^<folder_name^>
        exit /b 1
    )
    echo [INFO] Using folder: %FOLDER_NAME%
    python Scripts\run_individual_functions.py review --events-output "%EVENTS_OUTPUT%" --folder-name "%FOLDER_NAME%"
) else if "%FUNCTION%"=="merge" (
    if "%FOLDER_NAME%"=="" (
        echo [ERROR] Merge function requires a folder name argument
        echo [ERROR] Usage: %~n0 merge ^<folder_name^>
        exit /b 1
    )
    echo [INFO] Using folder: %FOLDER_NAME%
    python Scripts\run_individual_functions.py merge --events-output "%EVENTS_OUTPUT%" --folder-name "%FOLDER_NAME%"
) else if "%FUNCTION%"=="upload" (
    if "%MERGED_FILEPATH%"=="" (
        echo [ERROR] Upload function requires --merged-filepath argument
        echo [ERROR] Usage: %~n0 upload --merged-filepath ^<path_to_merged_file^>
        exit /b 1
    )
    echo [INFO] Using merged file: %MERGED_FILEPATH%
    python Scripts\run_individual_functions.py upload --events-output "%EVENTS_OUTPUT%" --merged-filepath "%MERGED_FILEPATH%"
) else if "%FUNCTION%"=="cleanup" (
    echo [INFO] Starting cleanup process...
    python Scripts\run_individual_functions.py cleanup
)

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
echo Functions and their specific options:
echo.
echo   review ^<folder_name^>
echo     - Launch event review/edit interface
echo     - Required: folder_name (timestamp, evergreen, or non-evergreen)
echo     - Options: --events-output (default: data/events_output)
echo.
echo   merge ^<folder_name^>
echo     - Merge events into a single file
echo     - Required: folder_name (timestamp, evergreen, or non-evergreen)
echo     - Options: --events-output (default: data/events_output)
echo.
echo   upload --merged-filepath ^<path^>
echo     - Upload files to AWS S3
echo     - Required: --merged-filepath (path to merged events file)
echo     - Options: --events-output (default: data/events_output)
echo.
echo   cleanup
echo     - Clean up temporary files
echo     - No arguments required
echo.
echo Examples:
echo   %~n0 review 20250717_142233                    # Review timestamp folder
echo   %~n0 review evergreen                          # Review evergreen folder
echo   %~n0 review non-evergreen                      # Review non-evergreen folder
echo   %~n0 review 20250717_142233 --events-output "data/events"
echo   %~n0 merge 20250717_142233                     # Merge timestamp folder
echo   %~n0 merge evergreen                           # Merge evergreen folder
echo   %~n0 merge non-evergreen                       # Merge non-evergreen folder
echo   %~n0 merge 20250717_142233 --events-output "data/events"
echo   %~n0 upload --merged-filepath data/merged_events.json
echo   %~n0 upload --merged-filepath "data/events/20250717_142233/merged.json" --events-output "data/events"
echo   %~n0 cleanup                                   # Clean up temporary files
exit /b 1

:end 