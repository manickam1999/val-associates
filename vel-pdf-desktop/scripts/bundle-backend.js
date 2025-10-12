const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const rootDir = path.join(__dirname, '..', '..');
const backendSrcDir = path.join(rootDir, 'vel-pdf-api');
const backendDestDir = path.join(__dirname, '..', 'resources', 'backend');

console.log('Starting backend bundling...');
console.log('Source:', backendSrcDir);
console.log('Destination:', backendDestDir);

// Create destination directory
if (!fs.existsSync(backendDestDir)) {
  fs.mkdirSync(backendDestDir, { recursive: true });
}

// For Windows: Create PyInstaller spec file
const specContent = `# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['${backendSrcDir.replace(/\\/g, '/')}/app/main.py'],
    pathex=['${backendSrcDir.replace(/\\/g, '/')}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'pdfplumber',
        'pandas',
        'openpyxl',
        'websockets',
        'fastapi',
        'multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
`;

const specPath = path.join(__dirname, 'backend.spec');
fs.writeFileSync(specPath, specContent);

console.log('\nTo build the backend for Windows:');
console.log('1. Install PyInstaller on Windows:');
console.log('   cd vel-pdf-api');
console.log('   pip install pyinstaller');
console.log('\n2. Build the executable:');
console.log(`   pyinstaller ${specPath}`);
console.log('\n3. Copy the dist/main.exe to:');
console.log(`   ${backendDestDir}`);
console.log('\n4. Or run this script on Windows to automate it.');

// If on Windows, try to build automatically
if (process.platform === 'win32') {
  try {
    console.log('\nAttempting to build on Windows...');

    // Check if pyinstaller is available
    try {
      execSync('pyinstaller --version', { stdio: 'pipe' });
    } catch (e) {
      console.log('PyInstaller not found. Installing...');
      execSync('pip install pyinstaller', { stdio: 'inherit' });
    }

    // Build with PyInstaller
    console.log('Building backend executable...');
    execSync(`pyinstaller ${specPath} --distpath "${backendDestDir}" --workpath "${path.join(__dirname, 'build')}"`, {
      stdio: 'inherit',
      cwd: backendSrcDir
    });

    console.log('\nBackend bundled successfully!');
  } catch (error) {
    console.error('Error building backend:', error.message);
    console.log('\nPlease build manually using the instructions above.');
    process.exit(1);
  }
} else {
  console.log('\nNote: Not on Windows. This script creates the spec file for building on Windows.');
  console.log('You can also copy the backend files for development/testing:');

  // For development, just copy the Python source
  const copyRecursive = (src, dest) => {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);

      if (entry.isDirectory()) {
        if (!['__pycache__', '.git', 'venv', 'env', 'node_modules', 'uploads', 'outputs'].includes(entry.name)) {
          copyRecursive(srcPath, destPath);
        }
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  };

  copyRecursive(backendSrcDir, backendDestDir);
  console.log('Backend source copied for development.');
}
