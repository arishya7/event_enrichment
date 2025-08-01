@echo off
REM Script to run individual functions from the Run class
REM This prevents accidental input from disrupting the main run.start() process

setlocal enabledelayedexpansion

REM Function to show usage
if "%~1"=="" goto :usage

set FUNCTION=%1
set FOLDER_NAME=
shift

REM Parse additional arguments
:parse_args
if "%~1"=="" goto :done_parsing
REM For review, merge, and upload functions, the first argument is the folder name
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
if "%FUNCTION%"=="upload" (
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
if "%FUNCTION%"=="browse" goto :valid_function

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
    python Scripts\run_individual_functions.py review --folder-name "%FOLDER_NAME%"
) else if "%FUNCTION%"=="merge" (
    if "%FOLDER_NAME%"=="" (
        echo [ERROR] Merge function requires a folder name argument
        echo [ERROR] Usage: %~n0 merge ^<folder_name^>
        exit /b 1
    )
    echo [INFO] Using folder: %FOLDER_NAME%
    python Scripts\run_individual_functions.py merge --folder-name "%FOLDER_NAME%"
) else if "%FUNCTION%"=="upload" (
    if "%FOLDER_NAME%"=="" (
        echo [ERROR] Upload function requires a folder name argument
        echo [ERROR] Usage: %~n0 upload ^<folder_name^>
        exit /b 1
    )
    echo [INFO] Using folder: %FOLDER_NAME%
    python Scripts\run_individual_functions.py upload --folder-name "%FOLDER_NAME%"
) else if "%FUNCTION%"=="cleanup" (
    echo [INFO] Starting cleanup process...
    python Scripts\run_individual_functions.py cleanup
) else if "%FUNCTION%"=="browse" (
    echo [INFO] Starting S3 interactive browser...
    python Scripts\run_individual_functions.py browse
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
echo   review [folder_name]
echo     - Launch event review/edit interface
echo     - Required: folder_name (timestamp, evergreen, or non-evergreen)
echo.
echo   merge [folder_name]
echo     - Merge events into a single file
echo     - Required: folder_name (timestamp, evergreen, or non-evergreen)
echo.
echo   upload [folder_name]
echo     - Upload files to AWS S3
echo     - Required: folder_name (timestamp, evergreen, or non-evergreen)
echo.
echo   browse
echo     - Interactive S3 file browser
echo     - No arguments required
echo.
echo   cleanup
echo     - Clean up temporary files
echo     - No arguments required
exit /b 1

:end 