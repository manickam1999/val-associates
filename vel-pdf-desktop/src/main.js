const { app, BrowserWindow, ipcMain, Tray, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const findFreePort = require('find-free-port');
const treeKill = require('tree-kill');

let mainWindow = null;
let tray = null;
let backendProcess = null;
let frontendProcess = null;
let backendPort = 8000;
let frontendPort = 3000;

const isDev = !app.isPackaged;

// Get resource paths
function getResourcePath(relativePath) {
  if (isDev) {
    return path.join(__dirname, '..', relativePath);
  }
  return path.join(process.resourcesPath, relativePath);
}

// Find available ports
async function findAvailablePorts() {
  try {
    const [backendFreePort] = await findFreePort(8000, 8100);
    const [frontendFreePort] = await findFreePort(3000, 3100);
    backendPort = backendFreePort;
    frontendPort = frontendFreePort;
    console.log(`Using ports - Backend: ${backendPort}, Frontend: ${frontendPort}`);
  } catch (error) {
    console.error('Error finding free ports:', error);
  }
}

// Start Python backend
async function startBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = getResourcePath('backend');

    let command, args;

    if (process.platform === 'win32') {
      // On Windows, use the bundled executable
      const exePath = isDev
        ? path.join(backendPath, 'main.exe')
        : path.join(backendPath, 'main.exe');

      command = exePath;
      args = [];
    } else {
      // On macOS/Linux (for development)
      command = 'python3';
      args = ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', backendPort.toString()];
    }

    console.log('Starting backend:', command, args);

    const env = {
      ...process.env,
      PORT: backendPort.toString(),
      UPLOAD_DIR: path.join(app.getPath('userData'), 'uploads'),
      OUTPUT_DIR: path.join(app.getPath('userData'), 'outputs'),
      CORS_ORIGINS: `http://localhost:${frontendPort}`,
    };

    backendProcess = spawn(command, args, {
      cwd: backendPath,
      env: env,
      stdio: 'pipe'
    });

    backendProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
      if (data.toString().includes('Uvicorn running') || data.toString().includes('Application startup complete')) {
        resolve();
      }
    });

    backendProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });

    backendProcess.on('error', (error) => {
      console.error('Failed to start backend:', error);
      reject(error);
    });

    backendProcess.on('close', (code) => {
      console.log(`Backend process exited with code ${code}`);
    });

    // Timeout fallback
    setTimeout(() => resolve(), 5000);
  });
}

// Start Next.js frontend
async function startFrontend() {
  return new Promise((resolve, reject) => {
    const frontendPath = getResourcePath('frontend');

    let command, args;

    if (process.platform === 'win32' && !isDev) {
      // On Windows, use node to run the server
      command = path.join(frontendPath, 'node.exe');
      args = ['server.js'];
    } else {
      // Development mode
      command = 'node';
      args = ['server.js'];
    }

    console.log('Starting frontend:', command, args);

    const env = {
      ...process.env,
      PORT: frontendPort.toString(),
      HOSTNAME: '0.0.0.0',
      NEXT_PUBLIC_API_URL: `http://localhost:${backendPort}`,
      NEXT_PUBLIC_WS_URL: `ws://localhost:${backendPort}`,
    };

    frontendProcess = spawn(command, args, {
      cwd: frontendPath,
      env: env,
      stdio: 'pipe'
    });

    frontendProcess.stdout.on('data', (data) => {
      console.log(`Frontend: ${data}`);
      if (data.toString().includes('Ready') || data.toString().includes('started server')) {
        resolve();
      }
    });

    frontendProcess.stderr.on('data', (data) => {
      console.error(`Frontend Error: ${data}`);
    });

    frontendProcess.on('error', (error) => {
      console.error('Failed to start frontend:', error);
      reject(error);
    });

    frontendProcess.on('close', (code) => {
      console.log(`Frontend process exited with code ${code}`);
    });

    // Timeout fallback
    setTimeout(() => resolve(), 5000);
  });
}

// Stop all processes
function stopProcesses() {
  return new Promise((resolve) => {
    let stopped = 0;
    const checkDone = () => {
      stopped++;
      if (stopped >= 2) resolve();
    };

    if (backendProcess) {
      console.log('Stopping backend...');
      treeKill(backendProcess.pid, 'SIGTERM', () => {
        backendProcess = null;
        checkDone();
      });
    } else {
      checkDone();
    }

    if (frontendProcess) {
      console.log('Stopping frontend...');
      treeKill(frontendProcess.pid, 'SIGTERM', () => {
        frontendProcess = null;
        checkDone();
      });
    } else {
      checkDone();
    }
  });
}

// Create main window
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
    icon: path.join(__dirname, '..', 'build', 'icon.png'),
    show: false, // Don't show until ready
  });

  // Show loading screen
  mainWindow.loadFile(path.join(__dirname, 'loading.html'));
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// Create system tray
function createTray() {
  const iconPath = path.join(__dirname, '..', 'build', 'icon.png');
  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show App',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        }
      }
    },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('Vel PDF Converter');
  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show();
    }
  });
}

// Initialize application
async function initialize() {
  try {
    console.log('Initializing application...');

    // Find available ports
    await findAvailablePorts();

    // Start backend
    console.log('Starting backend server...');
    await startBackend();

    // Start frontend
    console.log('Starting frontend server...');
    await startFrontend();

    // Wait a bit for servers to be ready
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Load the app
    console.log('Loading application UI...');
    mainWindow.loadURL(`http://localhost:${frontendPort}`);

    console.log('Application initialized successfully!');
  } catch (error) {
    console.error('Initialization error:', error);
    // Show error dialog
    const { dialog } = require('electron');
    dialog.showErrorBox('Startup Error', 'Failed to start the application: ' + error.message);
    app.quit();
  }
}

// App lifecycle
app.whenReady().then(async () => {
  createWindow();
  createTray();
  await initialize();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else if (mainWindow) {
      mainWindow.show();
    }
  });
});

app.on('window-all-closed', () => {
  // Don't quit on macOS
  if (process.platform !== 'darwin') {
    // Keep running in background
  }
});

app.on('before-quit', async () => {
  console.log('Application quitting...');
  await stopProcesses();
});

// IPC handlers
ipcMain.on('get-ports', (event) => {
  event.reply('ports', { backend: backendPort, frontend: frontendPort });
});
