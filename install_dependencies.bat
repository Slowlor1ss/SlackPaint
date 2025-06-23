@echo off
setlocal EnableDelayedExpansion

set PACKAGES=numpy pillow

echo The following Python packages will be installed:
for %%P in (%PACKAGES%) do (
    echo     %%P
)

set /p userInput=Do you want to proceed with the installation? (Y/N): 
if /I not "!userInput!"=="Y" (
    echo Installation cancelled.
    exit /b
)

where pip >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo pip is not installed or not added to PATH.
    echo Please install Python and ensure pip is available before running this script.
    pause
    exit /b
)

echo.
echo Installing packages...
for %%P in (%PACKAGES%) do (
    echo Installing %%P...
    pip install %%P
)

echo.
echo All required packages are installed.
pause
