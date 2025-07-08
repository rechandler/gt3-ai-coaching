import React from 'react';
import ReactDOM from 'react-dom/client';
import GT3OverlaySystem from './components/GT3Overlay';
import './index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <GT3OverlaySystem />
  </React.StrictMode>
);