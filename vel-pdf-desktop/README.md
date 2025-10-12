# Vel PDF Converter - Desktop Application

Windows desktop application for converting Malaysian STR (Statutory Reports) PDFs to Excel format.

## Overview

This Electron-based desktop application packages both the FastAPI backend and Next.js frontend into a single Windows executable (.exe) file that can be distributed to users without requiring them to install Python, Node.js, or any other dependencies.

## Features

- **Standalone Windows Executable**: Single .exe file with all dependencies bundled
- **No Installation Required**: Portable version available
- **System Tray Integration**: Runs in the background
- **Auto-start Services**: Automatically starts backend and frontend servers
- **Professional Installer**: NSIS installer with uninstaller support

## Prerequisites for Building

### Required Software

1. **Node.js** (v18 or higher)
   - Download from: https://nodejs.org/

2. **Python** (v3.8 or higher)
   - Download from: https://www.python.org/
   - Make sure Python is added to PATH

3. **PyInstaller** (will be installed by build script)
   - Used to package Python backend

4. **Windows OS** (for building Windows executables)
   - Can build on macOS/Linux but final packaging must be on Windows

## Quick Start - Building for Windows

### Option 1: Automated Build (Recommended)

On Windows, run the automated build script:

```bash
cd vel-pdf-desktop
scripts\build-windows.bat
```

On macOS/Linux (cross-compilation to Windows):

```bash
cd vel-pdf-desktop
chmod +x scripts/build-windows.sh
./scripts/build-windows.sh
```

### Option 2: Manual Build Steps

1. **Install Dependencies**
   ```bash
   cd vel-pdf-desktop
   npm install
   ```

2. **Bundle Backend**
   ```bash
   npm run bundle-backend
   ```
   This creates a standalone Python executable using PyInstaller.

3. **Bundle Frontend**
   ```bash
   npm run bundle-frontend
   ```
   This builds Next.js in standalone mode and copies all necessary files.

4. **Build Electron App**
   ```bash
   npm run dist:win
   ```
   This packages everything into Windows executables.

## Build Output

After a successful build, you'll find the following in the `dist/` directory:

1. **VelPDFConverter-Portable.exe** (30-60 MB)
   - Portable version that doesn't require installation
   - Can be run from any location
   - All settings stored in the executable's directory

2. **Vel PDF Converter Setup.exe** (30-60 MB)
   - Full installer with NSIS
   - Installs to Program Files
   - Creates Start Menu shortcuts
   - Creates Desktop shortcut (optional)
   - Includes uninstaller

## Distribution

You can distribute either or both executables to your users:

- **For single users or testing**: Use the portable version
- **For enterprise deployment**: Use the installer version

### System Requirements (for end users)

- **OS**: Windows 10 or higher (64-bit)
- **RAM**: 2 GB minimum (4 GB recommended)
- **Disk Space**: 200 MB for installation
- **Additional**: No other software required (all dependencies bundled)

## Project Structure

```
vel-pdf-desktop/
├── src/
│   ├── main.js           # Electron main process
│   ├── preload.js        # Preload script for IPC
│   └── loading.html      # Loading screen
├── scripts/
│   ├── bundle-backend.js # Backend bundling script
│   ├── bundle-frontend.js# Frontend bundling script
│   ├── build-windows.bat # Windows build script
│   └── build-windows.sh  # Unix build script
├── build/
│   ├── icon.ico          # App icon (Windows)
│   ├── icon.png          # App icon (PNG)
│   └── icon-info.txt     # Icon requirements
├── resources/
│   ├── backend/          # Bundled Python backend (generated)
│   └── frontend/         # Bundled Next.js frontend (generated)
├── dist/                 # Build output (generated)
├── package.json          # NPM configuration
└── README.md            # This file
```

## How It Works

### Architecture

1. **Electron Wrapper**
   - Creates a native Windows application window
   - Manages backend and frontend processes
   - Provides system tray integration

2. **Backend Service**
   - Python FastAPI server bundled as .exe using PyInstaller
   - Runs on localhost with dynamic port allocation
   - Handles PDF processing and Excel generation

3. **Frontend Service**
   - Next.js application in standalone mode
   - Runs on localhost
   - Communicates with backend via REST API and WebSocket

4. **Process Management**
   - Automatically starts both services on app launch
   - Gracefully shuts down all processes on exit
   - Monitors service health

### Port Management

The application automatically finds available ports:
- Backend: Attempts 8000-8100
- Frontend: Attempts 3000-3100

If the default ports are in use, it will automatically use the next available port.

### Data Storage

User data is stored in:
```
C:\Users\<YourName>\AppData\Roaming\vel-pdf-desktop\
├── uploads/    # Temporary uploaded PDFs
└── outputs/    # Generated Excel files
```

## Development

### Running in Development Mode

```bash
# Install dependencies
npm install

# Start Electron in dev mode
npm start
```

Note: In development mode, you'll need to have the backend and frontend running separately:

**Terminal 1 - Backend:**
```bash
cd ../vel-pdf-api
python -m uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd ../vel-pdf-web
npm run dev
```

**Terminal 3 - Electron:**
```bash
cd vel-pdf-desktop
npm start
```

### Debugging

- Open Developer Tools: `Ctrl+Shift+I` (when running in dev mode)
- Check console logs in the terminal for backend/frontend output
- Main process logs appear in the Electron terminal

## Customization

### Application Icon

1. Create a 512x512 PNG icon
2. Convert to .ico format (with multiple sizes: 16, 32, 48, 64, 128, 256)
3. Place files in `build/`:
   - `build/icon.ico` (Windows)
   - `build/icon.png` (System tray)

### Application Name and Metadata

Edit `package.json`:
```json
{
  "name": "your-app-name",
  "productName": "Your App Display Name",
  "description": "Your app description",
  "author": "Your Name",
  "version": "1.0.0",
  "build": {
    "appId": "com.yourcompany.yourapp",
    ...
  }
}
```

### Build Configuration

Modify the `build` section in `package.json` for advanced customization:
- Change installer options
- Add file associations
- Configure auto-updates
- Set up code signing (requires certificate)

## Troubleshooting

### Build Issues

**Issue: PyInstaller not found**
```bash
pip install pyinstaller
```

**Issue: Build fails on macOS/Linux**
- Windows executables must be built on Windows for best compatibility
- Use a Windows VM or dual-boot setup

**Issue: Missing dependencies**
```bash
npm install
cd ../vel-pdf-api && pip install -r requirements.txt
cd ../vel-pdf-web && npm install
```

### Runtime Issues

**Issue: App won't start**
- Check if ports 8000 and 3000 are available
- Run as Administrator (if needed)
- Check antivirus settings (may block unsigned .exe)

**Issue: Backend/Frontend won't connect**
- Check Windows Firewall settings
- Ensure localhost is accessible
- Review logs in: `%APPDATA%\vel-pdf-desktop\logs\`

## Building for Production

### Code Signing (Recommended for Production)

To avoid Windows security warnings:

1. Get a code signing certificate
2. Configure in `package.json`:
   ```json
   "win": {
     "certificateFile": "path/to/cert.pfx",
     "certificatePassword": "your-password",
     "signingHashAlgorithms": ["sha256"]
   }
   ```

### Continuous Integration

You can automate builds using GitHub Actions or similar:

```yaml
# .github/workflows/build-windows.yml
name: Build Windows
on: [push]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - uses: actions/setup-python@v2
      - run: cd vel-pdf-desktop && npm install
      - run: cd vel-pdf-desktop && npm run build-all
      - uses: actions/upload-artifact@v2
        with:
          name: windows-executables
          path: vel-pdf-desktop/dist/*.exe
```

## Advanced Features

### Auto-Update

To enable auto-updates:

1. Set up a server to host update files
2. Configure in `package.json`:
   ```json
   "build": {
     "publish": {
       "provider": "generic",
       "url": "https://your-server.com/updates"
     }
   }
   ```

3. Use electron-updater in your main process

### Custom Protocols

Register custom URL protocols (e.g., `velpdf://`) to open the app from links.

### Packaging with Installer Options

Customize NSIS installer in `package.json`:
```json
"nsis": {
  "oneClick": false,
  "allowToChangeInstallationDirectory": true,
  "createDesktopShortcut": true,
  "license": "LICENSE.txt"
}
```

## License

MIT License - see main project LICENSE file

## Support

For issues and questions:
1. Check the main project README
2. Review logs in application data directory
3. Open an issue in the repository

## Credits

Built with:
- [Electron](https://www.electronjs.org/)
- [electron-builder](https://www.electron.build/)
- [PyInstaller](https://www.pyinstaller.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Next.js](https://nextjs.org/)
