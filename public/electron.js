const { app, BrowserWindow, screen, globalShortcut, Menu, Tray, dialog, nativeImage } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let overlayWindow;
let telemetryServer;
let tray;

// Create a simple icon programmatically if file doesn't exist
function createTrayIcon() {
  try {
    // Try to use existing icon first
    const iconPath = path.join(__dirname, 'favicon.ico');
    return nativeImage.createFromPath(iconPath);
  } catch (error) {
    // Create a simple 16x16 icon programmatically
    const canvas = require('electron').nativeImage.createEmpty();
    // Create a simple colored square as fallback
    return nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAFYSURBVDiNpZM9SwNBEIafgwQLG1sLwcJCG1sLG0uxsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQsLGwsLBQ');
  }
}

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
    show: true // Start visible for debugging
  });

  const isDev = process.env.ELECTRON_IS_DEV === 'true';
  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
  
  console.log('Loading URL:', startUrl);
  overlayWindow.loadURL(startUrl);
  
  // Don't start with click-through for debugging
  // overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  
  // Show dev tools in development
  if (isDev) {
    overlayWindow.webContents.openDevTools();
  }
  
  overlayWindow.webContents.on('did-finish-load', () => {
    console.log('Overlay loaded successfully');
  });
  
  overlayWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load overlay:', errorCode, errorDescription);
  });
}

function createTray() {
  try {
    console.log('Creating system tray...');
    
    // Create tray icon
    const icon = createTrayIcon();
    tray = new Tray(icon);
    
    const contextMenu = Menu.buildFromTemplate([
      { 
        label: 'GT3 AI Coaching v1.0.0', 
        enabled: false,
        icon: icon.resize({ width: 16, height: 16 })
      },
      { type: 'separator' },
      { 
        label: 'Show Overlay', 
        click: () => {
          console.log('Show overlay clicked');
          if (overlayWindow) {
            overlayWindow.show();
            overlayWindow.focus();
          }
        }
      },
      { 
        label: 'Hide Overlay', 
        click: () => {
          console.log('Hide overlay clicked');
          if (overlayWindow) {
            overlayWindow.hide();
          }
        }
      },
      { type: 'separator' },
      {
        label: 'Toggle Click-Through',
        click: () => {
          if (overlayWindow) {
            const isClickThrough = overlayWindow.isIgnoreMouseEvents();
            overlayWindow.setIgnoreMouseEvents(!isClickThrough, { forward: true });
            console.log('Click-through:', !isClickThrough);
          }
        }
      },
      { type: 'separator' },
      {
        label: 'Debug - Force Show',
        click: () => {
          if (overlayWindow) {
            overlayWindow.show();
            overlayWindow.setAlwaysOnTop(true);
            overlayWindow.focus();
            overlayWindow.setIgnoreMouseEvents(false);
            console.log('Force showing overlay');
          }
        }
      },
      {
        label: 'About',
        click: () => {
          dialog.showMessageBox({
            type: 'info',
            title: 'GT3 AI Coaching',
            message: 'GT3 AI Coaching Overlay v1.0.0',
            detail: 'Professional AI coaching for iRacing GT3 cars\n\n• Press F10 to toggle overlay\n• Press F11 to toggle click-through\n• Right-click tray icon for options\n\nOverlay Status: ' + (overlayWindow && overlayWindow.isVisible() ? 'Visible' : 'Hidden'),
            buttons: ['OK']
          });
        }
      },
      { type: 'separator' },
      { 
        label: 'Quit', 
        click: () => {
          console.log('Quitting application');
          app.quit();
        }
      }
    ]);
    
    tray.setToolTip('GT3 AI Coaching Overlay\nPress F10 to toggle overlay');
    tray.setContextMenu(contextMenu);
    
    // Double-click to toggle overlay
    tray.on('double-click', () => {
      console.log('Tray double-clicked');
      if (overlayWindow) {
        if (overlayWindow.isVisible()) {
          overlayWindow.hide();
        } else {
          overlayWindow.show();
          overlayWindow.focus();
        }
      }
    });
    
    // Single click to show menu (Windows behavior)
    tray.on('click', () => {
      console.log('Tray clicked');
      tray.popUpContextMenu();
    });
    
    console.log('System tray created successfully');
    
    // Show notification that app is running
    tray.displayBalloon({
      iconType: 'info',
      title: 'GT3 AI Coaching',
      content: 'GT3 AI Coaching is running in the system tray.\nPress F10 to toggle overlay.'
    });
    
  } catch (error) {
    console.error('Failed to create system tray:', error);
    
    // Show dialog if tray creation fails
    dialog.showErrorBox('Tray Icon Error', 
      'Failed to create system tray icon.\nThe application is still running.\nPress F10 to toggle overlay.\n\nError: ' + error.message
    );
  }
}

function startTelemetryServer() {
  try {
    console.log('Starting telemetry server...');
    const isDev = process.env.ELECTRON_IS_DEV === 'true';
    const serverPath = isDev 
      ? path.join(__dirname, '../src/telemetry-server.js')
      : path.join(process.resourcesPath, 'app', 'src/telemetry-server.js');
    
    console.log('Telemetry server path:', serverPath);
    
    telemetryServer = spawn('node', [serverPath], { 
      stdio: ['pipe', 'pipe', 'pipe']
    });

    telemetryServer.stdout.on('data', (data) => {
      console.log(`Telemetry: ${data}`);
    });

    telemetryServer.stderr.on('data', (data) => {
      console.error(`Telemetry Error: ${data}`);
    });

    telemetryServer.on('error', (err) => {
      console.error('Failed to start telemetry server:', err);
    });
    
    telemetryServer.on('exit', (code) => {
      console.log(`Telemetry server exited with code ${code}`);
    });
    
    console.log('Telemetry server started with PID:', telemetryServer.pid);
  } catch (error) {
    console.error('Error starting telemetry server:', error);
  }
}

app.whenReady().then(() => {
  console.log('App ready, initializing...');
  
  createOverlayWindow();
  createTray();
  startTelemetryServer();

  // Register global shortcuts
  try {
    const f10Success = globalShortcut.register('F10', () => {
      console.log('F10 pressed - toggling overlay');
      if (overlayWindow) {
        if (overlayWindow.isVisible()) {
          overlayWindow.hide();
          console.log('Overlay hidden');
        } else {
          overlayWindow.show();
          overlayWindow.focus();
          console.log('Overlay shown');
        }
      }
    });

    const f11Success = globalShortcut.register('F11', () => {
      console.log('F11 pressed - toggling click-through');
      if (overlayWindow) {
        const isClickThrough = overlayWindow.isIgnoreMouseEvents();
        overlayWindow.setIgnoreMouseEvents(!isClickThrough, { forward: true });
        console.log('Click-through mode:', !isClickThrough);
        
        // Show balloon notification
        if (tray) {
          tray.displayBalloon({
            iconType: 'info',
            title: 'GT3 AI Coaching',
            content: `Click-through ${!isClickThrough ? 'enabled' : 'disabled'}`
          });
        }
      }
    });
    
    console.log('Global shortcuts registered:', { F10: f10Success, F11: f11Success });
  } catch (error) {
    console.error('Failed to register global shortcuts:', error);
  }

  // Hide dock on macOS
  if (process.platform === 'darwin') {
    app.dock.hide();
  }
  
  console.log('Application fully initialized');
});

app.on('window-all-closed', (e) => {
  console.log('All windows closed, preventing quit');
  e.preventDefault(); // Keep app running in tray
});

app.on('before-quit', () => {
  console.log('App quitting, cleaning up...');
  if (telemetryServer) {
    telemetryServer.kill();
  }
});

app.on('will-quit', () => {
  console.log('Unregistering global shortcuts');
  globalShortcut.unregisterAll();
});

// Handle any uncaught exceptions
process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
});

console.log('GT3 AI Coaching Electron main process loaded');