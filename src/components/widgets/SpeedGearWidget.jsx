import React from "react";

const SpeedGearWidget = ({ telemetryData }) => (
  <div className="text-center">
    <div className="text-3xl font-bold text-white">
      {telemetryData?.speed ? telemetryData.speed.toFixed(0) : "--"}
    </div>
    <div className="text-sm text-gray-400">MPH</div>
    <div className="text-xl font-bold text-orange-400 mt-1">
      {telemetryData?.gear || "-"}
    </div>
    <div className="text-xs text-gray-400">Gear</div>
  </div>
);

export default SpeedGearWidget;
