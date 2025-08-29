@echo off
echo Playwright Website Access Test
echo.

REM Activate virtual environment if it exists
if exist "..\venv\Scripts\activate.bat" (
    call "..\venv\Scripts\activate.bat"
)

echo Installing Playwright...
pip install -r requirements_playwright.txt

echo.
echo Installing Playwright browsers...
playwright install chromium

echo.
echo Running Playwright tests...
python test_playwright.py

echo.
echo Tests complete! Check data/playwright_test/ for results
pause 