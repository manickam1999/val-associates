# Quick Start Guide - Building Windows Executable

## For Windows Users (Simplest Method)

1. **Open Command Prompt or PowerShell**
   - Press `Win + R`, type `cmd`, press Enter

2. **Navigate to the desktop directory**
   ```bash
   cd vel-pdf-desktop
   ```

3. **Run the automated build script**
   ```bash
   scripts\build-windows.bat
   ```

4. **Wait for the build to complete** (may take 5-15 minutes)
   - The script will:
     - Install all required dependencies
     - Bundle the Python backend
     - Bundle the Next.js frontend
     - Create the Windows executables

5. **Find your executables**
   - Location: `vel-pdf-desktop\dist\`
   - Files:
     - `VelPDFConverter-Portable.exe` - No installation needed
     - `Vel PDF Converter Setup.exe` - Full installer

## For macOS/Linux Users (Cross-compilation)

### Prerequisites
- You can prepare the build on macOS/Linux
- Final packaging MUST be done on Windows

### Steps on macOS/Linux:

```bash
cd vel-pdf-desktop
npm install
node scripts/bundle-frontend.js
```

Then transfer the project to a Windows machine and run:
```bash
cd vel-pdf-desktop
scripts\build-windows.bat
```

## Testing the Executable

### Portable Version
1. Double-click `VelPDFConverter-Portable.exe`
2. Wait for the loading screen
3. App will open automatically

### Installer Version
1. Double-click `Vel PDF Converter Setup.exe`
2. Follow the installation wizard
3. Launch from Start Menu or Desktop shortcut

## Distribution

### Option 1: USB/Network Drive (Portable)
- Copy `VelPDFConverter-Portable.exe` to any location
- Run directly without installation
- Perfect for testing or personal use

### Option 2: Network Deployment (Installer)
- Share `Vel PDF Converter Setup.exe`
- Users run the installer
- Creates proper Start Menu entries and uninstaller
- Recommended for business environments

### File Sizes
- **Portable**: ~40-60 MB
- **Installer**: ~40-60 MB

## Troubleshooting

### "Windows protected your PC" message
This is normal for unsigned executables. To proceed:
1. Click "More info"
2. Click "Run anyway"

To avoid this, you need to code-sign the executable (requires purchasing a certificate).

### Antivirus Warnings
Some antivirus software may flag the executable:
- This is a false positive (common with PyInstaller)
- Add to exclusions if you trust the source
- Code signing helps reduce these warnings

### Build Errors

**"Node.js is not installed"**
- Download and install from: https://nodejs.org/

**"Python is not installed"**
- Download and install from: https://www.python.org/
- Make sure "Add Python to PATH" is checked during installation

**"npm: command not found"**
- Restart your terminal after installing Node.js
- Ensure Node.js is in your PATH

**Build fails during PyInstaller step**
```bash
pip install --upgrade pyinstaller
```

## What Gets Bundled?

The executable includes:
- Python runtime and all libraries
- Node.js runtime
- FastAPI backend server
- Next.js frontend application
- All PDF processing libraries
- Everything needed to run the app

Users don't need to install anything else!

## Next Steps

- Review the full README.md for advanced configuration
- Customize the app icon (see build/icon-info.txt)
- Set up code signing for production distribution
- Configure auto-updates (optional)

## Support

If you encounter issues:
1. Check the full README.md
2. Review build logs in the terminal
3. Ensure all prerequisites are installed
4. Try building on a clean Windows installation
