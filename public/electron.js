const { app, BrowserWindow, screen, globalShortcut, Menu, Tray, dialog, nativeImage, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const { autoUpdater } = require('electron-updater');
const EnhancedIRacingTelemetryServer = require('../src/telemetry-server');

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
  
  const isDev = process.env.ELECTRON_IS_DEV === 'true';
  const isTransparentMode = process.env.TRANSPARENT_MODE === 'true';
  
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
    focusable: isDev && !isTransparentMode, // Not focusable in transparent mode
    visibleOnAllWorkspaces: true,
    fullscreenable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: isDev ? false : true,
      allowRunningInsecureContent: isDev,
      backgroundThrottling: false
    },
    show: true,
    backgroundColor: 'rgba(0, 0, 0, 0)' // Explicitly set transparent background
  });

  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
  
  console.log('Development mode:', isDev);
  console.log('Loading URL:', startUrl);
  overlayWindow.loadURL(startUrl);
  
  // Don't start with click-through for debugging
  // overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  
  // Show dev tools in development (but not in transparent mode or by default)
  if (isDev && !isTransparentMode && process.env.SHOW_DEVTOOLS === 'true') {
    overlayWindow.webContents.openDevTools();
  }
  
  overlayWindow.webContents.on('did-finish-load', () => {
    console.log('Overlay loaded successfully');
    
    // Enable click-through mode by default in production or transparent mode
    if (!isDev || isTransparentMode) {
      setTimeout(() => {
        overlayWindow.setIgnoreMouseEvents(true, { forward: true });
        console.log('Click-through mode enabled for gaming overlay');
      }, 1000); // Small delay to ensure overlay is ready
    }
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
        label: 'Toggle DevTools',
        click: () => {
          if (overlayWindow) {
            if (overlayWindow.webContents.isDevToolsOpened()) {
              overlayWindow.webContents.closeDevTools();
            } else {
              overlayWindow.webContents.openDevTools();
            }
          }
        }
      },
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
    console.log('[Electron] Starting telemetry server...');
    
    // Create an instance of the telemetry server (imports the module)
    telemetryServer = new EnhancedIRacingTelemetryServer();
    
    // Handle telemetry events - FIXED: Use overlayWindow instead of mainWindow
    telemetryServer.on('Connected', () => {
      console.log('[Electron] ✅ Connected to Python telemetry server');
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('telemetry-status', 'connected');
      }
    });
    
    telemetryServer.on('Disconnected', () => {
      console.log('[Electron] ❌ Disconnected from Python telemetry server');
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('telemetry-status', 'disconnected');
      }
    });
    
    telemetryServer.on('GT3Telemetry', (data) => {
      // Send telemetry data to your renderer process
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('telemetry-data', data);
      }
    });
    
    telemetryServer.on('GT3CarDetected', (car) => {
      console.log(`[Electron] 🏎️ GT3 Car detected: ${car.name}`);
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('gt3-car-detected', car);
      }
    });
    
    telemetryServer.on('TireWarning', (warning) => {
      console.log('[Electron] 🔥 Tire warning:', warning.warnings);
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('tire-warning', warning);
      }
    });
    
    telemetryServer.on('FuelWarning', (warning) => {
      console.log('[Electron] ⛽ Fuel warning:', warning.message);
      if (overlayWindow) {  // ✅ FIXED: Changed from mainWindow to overlayWindow
        overlayWindow.webContents.send('fuel-warning', warning);
      }
    });
    
    telemetryServer.on('BrakeWarning', (warning) => {
      console.log('[Electron] 🛑 Brake warning:', warning.message);
      if (overlayWindow) {  // ✅ NEW: Added brake warning handler
        overlayWindow.webContents.send('brake-warning', warning);
      }
    });
    
    telemetryServer.on('LapCompleted', (lapTime) => {
      console.log('[Electron] 🏁 Lap completed:', telemetryServer.formatTime ? telemetryServer.formatTime(lapTime) : lapTime);
      if (overlayWindow) {  // ✅ NEW: Added lap completed handler
        overlayWindow.webContents.send('lap-completed', lapTime);
      }
    });
    
    telemetryServer.on('BestLap', (lapTime) => {
      console.log('[Electron] 🎯 New best lap:', telemetryServer.formatTime ? telemetryServer.formatTime(lapTime) : lapTime);
      if (overlayWindow) {  // ✅ NEW: Added best lap handler
        overlayWindow.webContents.send('best-lap', lapTime);
      }
    });
    
    telemetryServer.on('Error', (error) => {
      console.error('[Electron] Telemetry error:', error);
      if (overlayWindow) {  // ✅ NEW: Send errors to overlay for debugging
        overlayWindow.webContents.send('telemetry-error', error.message);
      }
    });
    
    console.log('[Electron] ✅ Telemetry server initialized (will connect to Python server)');
    
  } catch (error) {
    console.error('[Electron] Error starting telemetry server:', error);
  }
}

// IPC handlers for auto-updater and app info
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

ipcMain.handle('check-for-updates', () => {
  if (process.env.NODE_ENV === 'development') {
    console.log('Skipping update check in development mode');
    return false;
  }
  return autoUpdater.checkForUpdatesAndNotify();
});

ipcMain.handle('download-update', () => {
  return autoUpdater.downloadUpdate();
});

ipcMain.handle('install-update', () => {
  autoUpdater.quitAndInstall();
});

// Auto-updater events
autoUpdater.on('checking-for-update', () => {
  console.log('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  console.log('Update available.');
  if (overlayWindow) {
    overlayWindow.webContents.send('update-available', info);
  }
});

autoUpdater.on('update-not-available', (info) => {
  console.log('Update not available.');
});

autoUpdater.on('error', (err) => {
  console.log('Error in auto-updater. ' + err);
  if (overlayWindow) {
    overlayWindow.webContents.send('update-error', err.message);
  }
});

autoUpdater.on('download-progress', (progressObj) => {
  let log_message = "Download speed: " + progressObj.bytesPerSecond;
  log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
  log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
  console.log(log_message);
  if (overlayWindow) {
    overlayWindow.webContents.send('download-progress', progressObj);
  }
});

autoUpdater.on('update-downloaded', (info) => {
  console.log('Update downloaded');
  if (overlayWindow) {
    overlayWindow.webContents.send('update-downloaded', info);
  }
});

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

function stopTelemetryServer() {
  if (telemetryServer) {
    console.log('[Electron] Stopping telemetry server...');
    // Instead of killing a process, disconnect the WebSocket client
    telemetryServer.disconnect();
    telemetryServer = null;
  }
}

// Make sure to call stopTelemetryServer in your app.on('window-all-closed') handler
app.on('window-all-closed', () => {
  stopTelemetryServer();  // Clean up
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  console.log('App quitting, cleaning up...');
  stopTelemetryServer();
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