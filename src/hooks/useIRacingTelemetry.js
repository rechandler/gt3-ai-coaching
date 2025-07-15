import { useState, useEffect, useRef } from "react";

export const useIRacingTelemetry = () => {
  if (typeof window !== 'undefined') {
    console.warn('useIRacingTelemetry is deprecated. Use useCoachingMessages for telemetry data.');
  }
  return { telemetryData: null, isConnected: false };
};
