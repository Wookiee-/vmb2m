@echo off
REM Valzhar's MBII Server Manager — Setup (Windows)

echo ========================================
echo   Valzhar's MBII Server Manager
echo ========================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3 not found.
    echo   Install from https://python.org
    pause
    exit /b 1
)
python --version
echo   [OK] Python found

echo.
echo   .NET SDK 6.0 (x86) is required for MBII updates.
echo   Download from: https://dotnet.microsoft.com/en-us/download/dotnet/6.0
echo.
echo   Or install via winget:
echo     winget install Microsoft.DotNet.SDK.6
echo.

if exist "updater" (
    xcopy /E /Y updater\* "%USERPROFILE%\openjk\" >nul 2>&1
    echo   [OK] Updater files copied
)

if exist "mimalloc" (
    xcopy /Y mimalloc\*.dll "%USERPROFILE%\openjk\" >nul 2>&1
    echo   [OK] mimalloc DLLs copied to openjk\
)

echo.
echo ========================================
echo   Setup complete
echo ========================================
echo.
echo   Commands:
echo     python manager.py ^<name^> start^|stop^|restart^|status
echo     python manager.py --update
echo.
pause
