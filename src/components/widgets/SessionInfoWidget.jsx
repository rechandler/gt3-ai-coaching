import React from "react";

const SessionInfoWidget = ({ telemetryData, sessionInfo }) => (
  <div className="space-y-2">
    <div className="text-sm font-medium text-white">
      {sessionInfo?.carName || sessionInfo?.car || "No Car"}
    </div>
    {sessionInfo?.category && (
      <div className="inline-block px-2 py-0.5 text-xs rounded bg-blue-700 text-white font-semibold mb-1">
        {sessionInfo.category}
      </div>
    )}
    <div className="text-xs text-gray-400">
      {sessionInfo?.trackName || sessionInfo?.track || "No Track"}
    </div>
    <div className="flex justify-between text-xs">
      <span className="text-gray-400">Lap:</span>
      <span className="text-white">{telemetryData?.lap || "--"}</span>
    </div>
    <div className="flex justify-between text-xs">
      <span className="text-gray-400">Position:</span>
      <span className="text-white">P{telemetryData?.position || "--"}</span>
    </div>
    {sessionInfo && (
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">Session:</span>
        <span
          className={`text-white ${
            sessionInfo.session_active ? "text-green-400" : "text-gray-400"
          }`}
        >
          {sessionInfo.session_active ? "Active" : "Inactive"}
        </span>
      </div>
    )}
  </div>
);

export default SessionInfoWidget;
