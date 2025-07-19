import React from "react";

const FuelWidget = ({ telemetryData }) => {
  // Calculate laps remaining more accurately
  // We need fuel use per lap, not per hour
  // If we have current lap time and fuel use per hour, we can estimate
  let lapsRemaining = "--";

  if (
    telemetryData?.fuelLevel &&
    telemetryData?.fuelUsePerHour &&
    telemetryData?.lapLastLapTime
  ) {
    // Convert lap time from seconds to hours for calculation
    const lapTimeHours = telemetryData.lapLastLapTime / 3600;
    const fuelPerLap = telemetryData.fuelUsePerHour * lapTimeHours;

    if (fuelPerLap > 0) {
      lapsRemaining = (telemetryData.fuelLevel / fuelPerLap).toFixed(1);
    }
  } else if (telemetryData?.fuelLevel && telemetryData?.fuelUsePerHour) {
    // Fallback: estimate based on 90-second laps (typical for many tracks)
    const estimatedLapTimeHours = 90 / 3600; // 90 seconds in hours
    const estimatedFuelPerLap =
      telemetryData.fuelUsePerHour * estimatedLapTimeHours;

    if (estimatedFuelPerLap > 0) {
      lapsRemaining = (telemetryData.fuelLevel / estimatedFuelPerLap).toFixed(
        1
      );
    }
  }

  return (
    <div className="text-center">
      <div className="text-2xl font-bold text-blue-400">
        {telemetryData?.fuelLevel ? telemetryData.fuelLevel.toFixed(1) : "--"}
      </div>
      <div className="text-sm text-gray-400">Gallons</div>
      <div className="w-full bg-gray-700 rounded-full h-2 mt-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${(telemetryData?.fuelLevelPct || 0) * 100}%` }}
        />
      </div>
      <div className="text-xs text-gray-400 mt-1">{lapsRemaining} laps</div>
    </div>
  );
};

export default FuelWidget;
