import React from "react";
import { Wifi, WifiOff, Cloud, CloudOff } from "lucide-react";

const StatusIndicators = ({
  isConnected,
  isAuthenticated,
  hasActiveSession,
}) => {
  return (
    <div className="flex items-center space-x-2">
      <div
        className={`flex items-center space-x-2 px-3 py-1 rounded-full ${
          isConnected ? "bg-green-600" : "bg-red-600"
        }`}
      >
        {isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
        <span className="text-sm text-white">
          {isConnected ? "iRacing Connected" : "iRacing Disconnected"}
        </span>
      </div>

      <div
        className={`flex items-center space-x-2 px-3 py-1 rounded-full ${
          isAuthenticated ? "bg-blue-600" : "bg-gray-600"
        }`}
      >
        {isAuthenticated ? <Cloud size={16} /> : <CloudOff size={16} />}
        <span className="text-sm text-white">
          {isAuthenticated
            ? hasActiveSession
              ? "Session Recording"
              : "Cloud Ready"
            : "Cloud Offline"}
        </span>
      </div>
    </div>
  );
};

export default StatusIndicators;
