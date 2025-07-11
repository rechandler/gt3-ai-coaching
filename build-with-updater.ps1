# Auto-Update Build Script for GT3 AI Coaching

# Set error handling
$ErrorActionPreference = "Stop"

Write-Host "Building GT3 AI Coaching with Auto-Update Support..." -ForegroundColor Cyan

# 1. Install dependencies for auto-updater
Write-Host "`n1. Installing auto-updater dependencies..." -ForegroundColor Yellow
npm install electron-updater electron-builder

# 2. Build React app
Write-Host "`n2. Building React application..." -ForegroundColor Yellow
npm run build

# 3. Copy auto-updater files to build directory
Write-Host "`n3. Copying auto-updater files..." -ForegroundColor Yellow
Copy-Item "electron-updater.js" "build/"
Copy-Item "preload-updater.js" "build/"

# 4. Update electron.js in build directory to use auto-updater
Write-Host "`n4. Updating Electron main process..." -ForegroundColor Yellow
$electronContent = @"
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');
const { autoUpdater } = require('electron-updater');

// Configure auto-updater
if (!isDev) {
  autoUpdater.checkForUpdatesAndNotify();
}

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload-updater.js'),
    },
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
  });

  const startUrl = isDev 
    ? 'http://localhost:3000' 
    : `file://`+path.join(__dirname, '../build/index.html');
  
  mainWindow.loadURL(startUrl);
}

// Auto-updater event handlers
autoUpdater.on('checking-for-update', () => {
  console.log('Checking for update...');
});

autoUpdater.on('update-available', (info) => {
  console.log('Update available.');
  mainWindow.webContents.send('update-available', info);
});

autoUpdater.on('update-not-available', (info) => {
  console.log('Update not available.');
  mainWindow.webContents.send('update-not-available', info);
});

autoUpdater.on('error', (err) => {
  console.log('Error in auto-updater. ' + err);
  mainWindow.webContents.send('update-error', err);
});

autoUpdater.on('download-progress', (progressObj) => {
  let log_message = "Download speed: " + progressObj.bytesPerSecond;
  log_message = log_message + ' - Downloaded ' + progressObj.percent + '%';
  log_message = log_message + ' (' + progressObj.transferred + "/" + progressObj.total + ')';
  console.log(log_message);
  mainWindow.webContents.send('download-progress', progressObj);
});

autoUpdater.on('update-downloaded', (info) => {
  console.log('Update downloaded');
  mainWindow.webContents.send('update-downloaded', info);
});

// IPC handlers
ipcMain.handle('check-for-updates', () => {
  if (!isDev) {
    autoUpdater.checkForUpdates();
  }
});

ipcMain.handle('restart-app', () => {
  autoUpdater.quitAndInstall();
});

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
"@

$electronContent | Out-File -FilePath "build/electron.js" -Encoding utf8

# 5. Build Electron package with auto-updater
Write-Host "`n5. Building Electron package..." -ForegroundColor Yellow
npx electron-builder --config package-electron.json

Write-Host "`nBuild complete! Auto-updater enabled." -ForegroundColor Green
Write-Host "To set up auto-updates:" -ForegroundColor White
Write-Host "1. Create a GitHub release with the generated installer" -ForegroundColor White
Write-Host "2. Update the 'publish' configuration in package-electron.json with your repo details" -ForegroundColor White
Write-Host "3. The app will automatically check for updates on startup" -ForegroundColor White
