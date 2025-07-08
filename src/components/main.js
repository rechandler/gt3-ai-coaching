const { app, BrowserWindow, screen, globalShortcut, Menu, Tray, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let overlayWindow;
let telemetryServer;
let tray;

function createOverlayWindow() {
  const { width, height } = screen.getPrimaryDisplay().bounds;
  
  overlayWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    show: false
  });

  const isDev = process.env.NODE_ENV === 'development';
  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
  
  overlayWindow.loadURL(startUrl);
  overlayWindow.setIgnoreMouseEvents(true, { forward: true });
}

function createTray() {
  // Create a simple tray icon
  tray = new Tray(path.join(__dirname, '../public/favicon.ico'));
  
  const contextMenu = Menu.buildFromTemplate([
    { label: 'GT3 AI Coaching v1.0.0', enabled: false },
    { type: 'separator' },
    { 
      label: 'Show Overlay', 
      click: () => {
        if (overlayWindow) overlayWindow.show();
      }
    },
    { 
      label: 'Hide Overlay', 
      click: () => {
        if (overlayWindow) overlayWindow.hide();
      }
    },
    { type: 'separator' },
    {
      label: 'About',
      click: () => {
        dialog.showMessageBox({
          type: 'info',
          title: 'GT3 AI Coaching',
          message: 'GT3 AI Coaching Overlay v1.0.0',
          detail: 'Professional AI coaching for iRacing GT3 cars\n\n• 26 supported tracks\n• 10 GT3 cars\n• Real-time coaching\n\nPress F10 to toggle overlay\nPress F11 to toggle click-through'
        });
      }
    },
    { 
      label: 'Quit', 
      click: () => app.quit() 
    }
  ]);
  
  tray.setToolTip('GT3 AI Coaching Overlay');
  tray.setContextMenu(contextMenu);
  
  tray.on('double-click', () => {
    if (overlayWindow) {
      overlayWindow.isVisible() ? overlayWindow.hide() : overlayWindow.show();
    }
  });
}

function startTelemetryServer() {
  const serverPath = path.join(__dirname, 'telemetry-server.js');
  telemetryServer = spawn('node', [serverPath], { 
    stdio: 'pipe'
  });

  telemetryServer.stdout.on('data', (data) => {
    console.log(`Telemetry: ${data}`);
  });

  telemetryServer.stderr.on('data', (data) => {
    console.error(`Telemetry Error: ${data}`);
  });

  telemetryServer.on('error', (err) => {
    console.error('Telemetry server error:', err);
  });
}

app.whenReady().then(() => {
  createOverlayWindow();
  createTray();
  startTelemetryServer();

  // Global shortcuts
  globalShortcut.register('F10', () => {
    if (overlayWindow) {
      overlayWindow.isVisible() ? overlayWindow.hide() : overlayWindow.show();
    }
  });

  globalShortcut.register('F11', () => {
    if (overlayWindow) {
      const isClickThrough = overlayWindow.isIgnoreMouseEvents();
      overlayWindow.setIgnoreMouseEvents(!isClickThrough, { forward: true });
    }
  });

  // Hide dock on macOS
  if (process.platform === 'darwin') {
    app.dock.hide();
  }
});

app.on('window-all-closed', (e) => {
  e.preventDefault(); // Keep app running in tray
});

app.on('before-quit', () => {
  if (telemetryServer) {
    telemetryServer.kill();
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});