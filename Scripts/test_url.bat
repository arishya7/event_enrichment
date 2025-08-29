@echo off
echo Single URL AgentQL Test
echo.

if "%1"=="" (
    echo Usage: test_url.bat [URL]
    echo Example: test_url.bat sassymamasg.com
    echo.
    echo Or run without arguments to enter URL interactively
    echo.
    pause
    exit /b
)

REM Activate virtual environment if it exists
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
)

echo Testing URL: %1
python test_single_url.py %1

echo.
echo Test complete! Check data/single_url_test_results.json for results
pause 