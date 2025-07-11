import React from 'react';
import ReactDOM from 'react-dom/client';
import GT3OverlaySystem from './components/GT3Overlay';
import './index.css';

// Initialize auto-updater IPC handlers
window.addEventListener('DOMContentLoaded', () => {
  if (window.electronAPI) {
    console.log('Auto-updater API available');
  }
});

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <GT3OverlaySystem  />
  </React.StrictMode>
);