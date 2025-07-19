import React from "react";

const DeltaTimeWidget = ({ telemetryData }) => {
  const isInPits = telemetryData?.onPitRoad;
  const hasDelta =
    telemetryData?.deltaTime !== null && telemetryData?.deltaTime !== undefined;
  const deltaSource = telemetryData?.deltaSource || "unknown";

  return (
    <div className="text-center">
      <div
        className={`text-4xl font-bold ${
          isInPits
            ? "text-gray-500"
            : hasDelta && telemetryData.deltaTime < 0
            ? "text-green-400"
            : "text-red-400"
        }`}
      >
        {isInPits
          ? "PIT"
          : hasDelta
          ? `${
              telemetryData.deltaTime >= 0 ? "+" : ""
            }${telemetryData.deltaTime.toFixed(3)}`
          : "0.000"}
      </div>
      <div className="text-sm text-gray-400">
        {isInPits ? "In Pits" : "Delta Time"}
      </div>
      {/* Show delta source for debugging/verification */}
      {deltaSource === "iRacing_native" && (
        <div className="text-xs text-green-500 mt-1">iRacing Native</div>
      )}
      {deltaSource === "calculated_fallback" && (
        <div className="text-xs text-yellow-500 mt-1">Calculated</div>
      )}
      {telemetryData?.lapBestLapTime && !isInPits && (
        <div className="text-xs text-gray-500 mt-1">
          Best: {telemetryData.lapBestLapTime.toFixed(3)}s
        </div>
      )}
      {/* Show additional delta fields if available */}
      {telemetryData?.lapDeltaToOptimalLap !== null &&
        telemetryData?.lapDeltaToOptimalLap !== undefined &&
        !isInPits && (
          <div className="text-xs text-blue-400 mt-1">
            Optimal: {telemetryData.lapDeltaToOptimalLap >= 0 ? "+" : ""}
            {telemetryData.lapDeltaToOptimalLap.toFixed(3)}
          </div>
        )}
    </div>
  );
};

export default DeltaTimeWidget;
