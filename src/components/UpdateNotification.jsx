import React, { useState, useEffect } from "react";
import "./UpdateNotification.css";

const UpdateNotification = () => {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);
  const [isDownloading, setIsDownloading] = useState(false);
  const [updateDownloaded, setUpdateDownloaded] = useState(false);
  const [updateInfo, setUpdateInfo] = useState(null);
  const [currentVersion, setCurrentVersion] = useState("");

  useEffect(() => {
    // Get current app version
    if (window.electronAPI && window.electronAPI.getAppVersion) {
      window.electronAPI
        .getAppVersion()
        .then((version) => {
          setCurrentVersion(version);
        })
        .catch((error) => {
          console.error("Failed to get app version:", error);
          setCurrentVersion("Unknown");
        });

      // Set up auto-updater event listeners
      if (window.electronAPI.onUpdateAvailable) {
        window.electronAPI.onUpdateAvailable((event, info) => {
          setUpdateInfo(info);
          setUpdateAvailable(true);
        });
      }

      if (window.electronAPI.onDownloadProgress) {
        window.electronAPI.onDownloadProgress((event, progressObj) => {
          setDownloadProgress(Math.round(progressObj.percent));
        });
      }

      if (window.electronAPI.onUpdateDownloaded) {
        window.electronAPI.onUpdateDownloaded((event, info) => {
          setIsDownloading(false);
          setUpdateDownloaded(true);
        });
      }

      if (window.electronAPI.onUpdateError) {
        window.electronAPI.onUpdateError((event, error) => {
          console.error("Update error:", error);
          setIsDownloading(false);
        });
      }

      // Check for updates on component mount
      if (window.electronAPI.checkForUpdates) {
        window.electronAPI.checkForUpdates();
      }
    } else {
      console.log("Electron API not available - running in browser mode");
      setCurrentVersion("Browser Mode");
    }

    return () => {
      // Clean up listeners
      if (window.electronAPI) {
        window.electronAPI.removeAllListeners("update-available");
        window.electronAPI.removeAllListeners("download-progress");
        window.electronAPI.removeAllListeners("update-downloaded");
      }
    };
  }, []);

  const handleDownloadUpdate = async () => {
    if (!window.electronAPI || !window.electronAPI.downloadUpdate) {
      console.error("Download update API not available");
      return;
    }

    setIsDownloading(true);
    setDownloadProgress(0);
    try {
      await window.electronAPI.downloadUpdate();
    } catch (error) {
      console.error("Error downloading update:", error);
      setIsDownloading(false);
    }
  };

  const handleInstallUpdate = async () => {
    if (!window.electronAPI || !window.electronAPI.installUpdate) {
      console.error("Install update API not available");
      return;
    }

    try {
      await window.electronAPI.installUpdate();
    } catch (error) {
      console.error("Error installing update:", error);
    }
  };

  const handleDismiss = () => {
    setUpdateAvailable(false);
    setUpdateDownloaded(false);
  };

  const handleCheckForUpdates = async () => {
    try {
      const result = await window.electronAPI.checkForUpdates();
      if (!result.success && result.error) {
        console.log("No updates available or error:", result.error);
      }
    } catch (error) {
      console.error("Error checking for updates:", error);
    }
  };

  if (!window.electronAPI) {
    return null; // Not in Electron environment
  }

  return (
    <div className="update-container">
      {/* Manual check button */}
      <div className="update-check-section">
        <button
          className="update-check-button"
          onClick={handleCheckForUpdates}
          title="Check for updates"
        >
          <span className="update-icon">🔄</span>v{currentVersion}
        </button>
      </div>

      {/* Update available notification */}
      {updateAvailable && !updateDownloaded && (
        <div className="update-notification update-available">
          <div className="update-content">
            <div className="update-header">
              <span className="update-icon">🚀</span>
              <h3>Update Available!</h3>
              <button className="update-close" onClick={handleDismiss}>
                ×
              </button>
            </div>
            <p>
              GT3 AI Coaching v{updateInfo?.version} is available!
              <br />
              <small>Current version: v{currentVersion}</small>
            </p>
            {updateInfo?.releaseNotes && (
              <div className="update-notes">
                <strong>What's new:</strong>
                <div
                  dangerouslySetInnerHTML={{ __html: updateInfo.releaseNotes }}
                />
              </div>
            )}
            <div className="update-actions">
              {isDownloading ? (
                <div className="download-progress">
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${downloadProgress}%` }}
                    ></div>
                  </div>
                  <span>Downloading... {downloadProgress}%</span>
                </div>
              ) : (
                <>
                  <button
                    className="update-button primary"
                    onClick={handleDownloadUpdate}
                  >
                    Download Update
                  </button>
                  <button
                    className="update-button secondary"
                    onClick={handleDismiss}
                  >
                    Later
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Update downloaded notification */}
      {updateDownloaded && (
        <div className="update-notification update-ready">
          <div className="update-content">
            <div className="update-header">
              <span className="update-icon">✅</span>
              <h3>Update Ready!</h3>
              <button className="update-close" onClick={handleDismiss}>
                ×
              </button>
            </div>
            <p>
              GT3 AI Coaching v{updateInfo?.version} has been downloaded and is
              ready to install.
            </p>
            <div className="update-actions">
              <button
                className="update-button primary"
                onClick={handleInstallUpdate}
              >
                Restart & Install
              </button>
              <button
                className="update-button secondary"
                onClick={handleDismiss}
              >
                Install Later
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UpdateNotification;
