const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { autoUpdater } = require('electron-updater');
const log = require('electron-log');
const path = require('path');
const isDev = require('electron-is-dev');

// Configure auto-updater logging
autoUpdater.logger = log;
autoUpdater.logger.transports.file.level = 'info';
log.info('App starting...');

// Configure auto-updater
autoUpdater.checkForUpdatesAndNotify();

// Auto-updater events
autoUpdater.on('checking-for-update', () => {
  log.info('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  log.info('Update available.');
  // Show notification to user
  if (mainWindow) {
    mainWindow.webContents.send('update-available', info);
  }
});

autoUpdater.on('update-not-available', (info) => {
  log.info('Update not available.');
});

autoUpdater.on('error', (err) => {
  log.error('Error in auto-updater. ' + err);
});

autoUpdater.on('download-progress', (progressObj) => {
  let log_message = "Download speed: " + progressObj.bytesPerSecond;
  log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
  log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
  log.info(log_message);
  
  // Send progress to renderer
  if (mainWindow) {
    mainWindow.webContents.send('download-progress', progressObj);
  }
});

autoUpdater.on('update-downloaded', (info) => {
  log.info('Update downloaded');
  // Show restart dialog
  if (mainWindow) {
    mainWindow.webContents.send('update-downloaded', info);
  }
});

let mainWindow;

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../assets/icon.ico'),
    title: 'GT3 AI Coaching',
    show: false // Don't show until ready
  });

  // Load the app
  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://${path.join(__dirname, '../build/index.html')}`;
  
  mainWindow.loadURL(startUrl);

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    
    // Check for updates after window is shown (only in production)
    if (!isDev) {
      setTimeout(() => {
        autoUpdater.checkForUpdatesAndNotify();
      }, 2000);
    }
  });

  // Open DevTools in development
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App event handlers
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC handlers for auto-updater
ipcMain.handle('check-for-updates', async () => {
  if (!isDev) {
    try {
      const result = await autoUpdater.checkForUpdates();
      return { success: true, updateInfo: result.updateInfo };
    } catch (error) {
      log.error('Error checking for updates:', error);
      return { success: false, error: error.message };
    }
  }
  return { success: false, error: 'Updates disabled in development mode' };
});

ipcMain.handle('download-update', async () => {
  if (!isDev) {
    try {
      await autoUpdater.downloadUpdate();
      return { success: true };
    } catch (error) {
      log.error('Error downloading update:', error);
      return { success: false, error: error.message };
    }
  }
  return { success: false, error: 'Updates disabled in development mode' };
});

ipcMain.handle('install-update', async () => {
  if (!isDev) {
    // This will restart the app and install the update
    autoUpdater.quitAndInstall();
    return { success: true };
  }
  return { success: false, error: 'Updates disabled in development mode' };
});

ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

// Handle app updates in menu (optional)
ipcMain.handle('show-update-dialog', async (event, updateInfo) => {
  const result = await dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'Update Available',
    message: `GT3 AI Coaching v${updateInfo.version} is available!`,
    detail: 'Would you like to download and install the update now?',
    buttons: ['Download & Install', 'Later'],
    defaultId: 0,
    cancelId: 1
  });
  
  return result.response === 0;
});

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    // Someone tried to run a second instance, focus our window instead
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}
