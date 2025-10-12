#!/bin/bash

echo "============================================"
echo "Vel PDF Converter - Windows Build Script"
echo "============================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js is not installed or not in PATH"
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python is not installed or not in PATH"
    echo "Please install Python from https://www.python.org/"
    exit 1
fi

echo "Step 1: Installing desktop dependencies..."
echo ""
npm install
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "Step 2: Installing PyInstaller..."
echo ""
pip3 install pyinstaller
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install PyInstaller"
    exit 1
fi

echo ""
echo "Step 3: Bundling backend (Python)..."
echo ""
node scripts/bundle-backend.js
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to bundle backend"
    exit 1
fi

echo ""
echo "Step 4: Bundling frontend (Next.js)..."
echo ""
node scripts/bundle-frontend.js
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to bundle frontend"
    exit 1
fi

echo ""
echo "Step 5: Building Electron application for Windows..."
echo ""
npm run dist:win
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to build Electron app"
    exit 1
fi

echo ""
echo "============================================"
echo "BUILD COMPLETE!"
echo "============================================"
echo ""
echo "Your Windows executable can be found in:"
echo "  dist/VelPDFConverter-Portable.exe (Portable version)"
echo "  dist/Vel PDF Converter Setup.exe (Installer)"
echo ""
echo "You can now distribute these files to Windows users."
echo ""
