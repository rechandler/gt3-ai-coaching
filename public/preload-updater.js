const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Auto-updater functions
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
  installUpdate: () => ipcRenderer.invoke('install-update'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  showUpdateDialog: (updateInfo) => ipcRenderer.invoke('show-update-dialog', updateInfo),
  
  // Auto-updater event listeners
  onUpdateAvailable: (callback) => ipcRenderer.on('update-available', callback),
  onDownloadProgress: (callback) => ipcRenderer.on('download-progress', callback),
  onUpdateDownloaded: (callback) => ipcRenderer.on('update-downloaded', callback),
  
  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  
  // Utility functions
  platform: process.platform,
  isDev: process.env.NODE_ENV === 'development'
});
