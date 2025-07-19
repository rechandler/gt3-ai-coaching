import React from "react";
import { Settings, Eye, EyeOff, RotateCcw } from "lucide-react";

const SettingsPanel = ({
  showSettings,
  setShowSettings,
  widgetVisibility,
  handleToggleVisibility,
  resetPositions,
  isAuthenticated,
  isAnonymous,
  sessions,
  hasActiveSession,
  logout,
  signInAnonymous,
}) => {
  return (
    <>
      <button
        onClick={() => setShowSettings(!showSettings)}
        className="bg-gray-800 bg-opacity-80 backdrop-blur-sm border border-gray-600 rounded-lg p-2 text-white hover:bg-gray-700 transition-colors"
      >
        <Settings size={20} />
      </button>

      {showSettings && (
        <div className="fixed top-16 right-4 z-50 bg-gray-800 bg-opacity-90 backdrop-blur-sm border border-gray-600 rounded-lg p-4 min-w-64">
          <h3 className="text-lg font-bold text-white mb-4">Widget Settings</h3>
          <div className="space-y-3">
            {Object.entries(widgetVisibility).map(([widgetId, isVisible]) => (
              <div key={widgetId} className="flex items-center justify-between">
                <span className="text-sm text-white capitalize">
                  {widgetId.replace(/([A-Z])/g, " $1").trim()}
                </span>
                <button
                  onClick={() => handleToggleVisibility(widgetId)}
                  className={`p-1 rounded transition-colors ${
                    isVisible
                      ? "text-green-400 hover:text-green-300"
                      : "text-gray-400 hover:text-gray-300"
                  }`}
                >
                  {isVisible ? <Eye size={16} /> : <EyeOff size={16} />}
                </button>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-gray-600">
            <button
              onClick={resetPositions}
              className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors mb-3"
            >
              <RotateCcw size={16} />
              <span>Reset Positions</span>
            </button>

            <div className="space-y-2">
              <div className="text-sm font-medium text-white">Cloud Sync</div>
              {isAuthenticated ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Status:</span>
                    <span className="text-green-400">
                      {isAnonymous ? "Anonymous User" : "Logged In"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">Sessions:</span>
                    <span className="text-white">{sessions.length}</span>
                  </div>
                  {hasActiveSession && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Recording:</span>
                      <span className="text-green-400">Active</span>
                    </div>
                  )}
                  <button
                    onClick={logout}
                    className="w-full bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded text-xs transition-colors"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <button
                  onClick={signInAnonymous}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded text-xs transition-colors"
                >
                  Enable Cloud Sync
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SettingsPanel;
