@echo off
echo ============================================
echo Vel PDF Converter - Windows Build Script
echo ============================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed or not in PATH
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo Step 1: Installing desktop dependencies...
echo.
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Step 2: Installing PyInstaller...
echo.
pip install pyinstaller
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo Step 3: Bundling backend (Python)...
echo.
node scripts\bundle-backend.js
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to bundle backend
    pause
    exit /b 1
)

echo.
echo Step 4: Bundling frontend (Next.js)...
echo.
node scripts\bundle-frontend.js
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to bundle frontend
    pause
    exit /b 1
)

echo.
echo Step 5: Building Electron application...
echo.
npm run dist:win
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to build Electron app
    pause
    exit /b 1
)

echo.
echo ============================================
echo BUILD COMPLETE!
echo ============================================
echo.
echo Your Windows executable can be found in:
echo   dist\VelPDFConverter-Portable.exe (Portable version)
echo   dist\Vel PDF Converter Setup.exe (Installer)
echo.
echo You can now distribute these files to Windows users.
echo.
pause
