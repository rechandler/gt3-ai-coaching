import React, { useState, useEffect, useCallback } from "react";
import UpdateNotification from "./UpdateNotification";
import DraggableWidget from "./DraggableWidget";
import StatusIndicators from "./StatusIndicators";
import SettingsPanel from "./SettingsPanel";
import {
  DeltaTimeWidget,
  FuelWidget,
  SpeedGearWidget,
  SessionInfoWidget,
  UserProfileWidget,
  CoachingWidget,
} from "./widgets";
import { useAuth } from "../firebase/auth";
import { useSessionHistory } from "../firebase/sessionHistory";
import { useCoachingMessages } from "../hooks/useCoachingMessages";
import { useWidgetLayout } from "../hooks/useWidgetLayout";

const GT3OverlaySystem = () => {
  const {
    coachingMessages,
    setCoachingMessages,
    clearMessages,
    markMessagesAsRead,
    isCoachingConnected,
    sessionInfo,
    telemetryData,
    isTelemetryConnected,
  } = useCoachingMessages();

  // Firebase hooks
  const { user, isAuthenticated, signInAnonymous, logout, isAnonymous } =
    useAuth();
  const {
    sessions,
    currentSessionId,
    hasActiveSession,
    startSession,
    endSession,
    addCoachingMessage,
    addLapTime,
  } = useSessionHistory();

  // Widget layout hook
  const {
    widgetPositions,
    widgetVisibility,
    handlePositionChange,
    handleToggleVisibility,
    resetPositions,
  } = useWidgetLayout();

  const [showSettings, setShowSettings] = useState(false);
  const [lastLapNumber, setLastLapNumber] = useState(0);

  // Auto sign-in anonymously when component mounts
  useEffect(() => {
    if (!isAuthenticated) {
      signInAnonymous().catch(console.error);
    }
  }, [isAuthenticated, signInAnonymous]);

  // Session management - start session when we have session info and user is authenticated
  useEffect(() => {
    if (isAuthenticated && sessionInfo && !hasActiveSession && isTelemetryConnected) {
      console.log("Starting new session:", sessionInfo);
      startSession(sessionInfo, telemetryData).catch(console.error);
    }
  }, [
    isAuthenticated,
    sessionInfo,
    hasActiveSession,
    isTelemetryConnected,
    startSession,
    telemetryData,
  ]);

  // End session when disconnected from iRacing
  useEffect(() => {
    if (!isTelemetryConnected && hasActiveSession) {
      console.log("iRacing disconnected, ending session");
      endSession({
        total_laps: telemetryData?.lap || 0,
        final_fuel_level: telemetryData?.fuelLevel || 0,
      }).catch(console.error);
    }
  }, [isTelemetryConnected, hasActiveSession, endSession, telemetryData]);

  // Track lap completions and save to Firebase
  useEffect(() => {
    if (
      telemetryData?.lap &&
      telemetryData.lap > lastLapNumber &&
      hasActiveSession
    ) {
      const lapTime = telemetryData.lapLastLapTime;
      if (lapTime && lapTime > 0) {
        console.log(
          `Lap ${telemetryData.lap} completed: ${lapTime.toFixed(3)}s`
        );
        addLapTime(lapTime, telemetryData.lap).catch(console.error);
      }
      setLastLapNumber(telemetryData.lap);
    }
  }, [
    telemetryData?.lap,
    telemetryData?.lapLastLapTime,
    lastLapNumber,
    hasActiveSession,
    addLapTime,
  ]);

  // Optimized coaching message saving with useCallback to prevent unnecessary re-renders
  const saveLatestMessage = useCallback(() => {
    if (coachingMessages.length > 0 && hasActiveSession) {
      const latestMessage = coachingMessages[0];
      if (latestMessage.isNew) {
        addCoachingMessage(latestMessage).catch(console.error);
      }
    }
  }, [coachingMessages, hasActiveSession, addCoachingMessage]);

  // Save coaching messages to Firebase with optimized effect
  useEffect(() => {
    saveLatestMessage();
  }, [saveLatestMessage]);

  return (
    <div className="min-h-screen bg-transparent">
      <div className="fixed top-4 right-4 z-50 flex items-center space-x-2">
        <StatusIndicators
          isConnected={isTelemetryConnected}
          isAuthenticated={isAuthenticated}
          hasActiveSession={hasActiveSession}
        />

        <SettingsPanel
          showSettings={showSettings}
          setShowSettings={setShowSettings}
          widgetVisibility={widgetVisibility}
          handleToggleVisibility={handleToggleVisibility}
          resetPositions={resetPositions}
          isAuthenticated={isAuthenticated}
          isAnonymous={isAnonymous}
          sessions={sessions}
          hasActiveSession={hasActiveSession}
          logout={logout}
          signInAnonymous={signInAnonymous}
        />
      </div>

      <DraggableWidget
        id="deltaTime"
        title="Delta Time"
        position={widgetPositions.deltaTime}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.deltaTime}
        onToggleVisibility={handleToggleVisibility}
      >
        <DeltaTimeWidget telemetryData={telemetryData} />
      </DraggableWidget>

      <DraggableWidget
        id="fuel"
        title="Fuel"
        position={widgetPositions.fuel}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.fuel}
        onToggleVisibility={handleToggleVisibility}
      >
        <FuelWidget telemetryData={telemetryData} />
      </DraggableWidget>

      <DraggableWidget
        id="coaching"
        title="AI Coaching"
        position={widgetPositions.coaching}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.coaching}
        onToggleVisibility={handleToggleVisibility}
      >
        <CoachingWidget
          coachingMessages={coachingMessages}
          setCoachingMessages={setCoachingMessages}
          clearMessages={clearMessages}
          markMessagesAsRead={markMessagesAsRead}
          isCoachingConnected={isCoachingConnected}
          isConnected={isTelemetryConnected}
        />
      </DraggableWidget>

      <DraggableWidget
        id="speedGear"
        title="Speed & Gear"
        position={widgetPositions.speedGear}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.speedGear}
        onToggleVisibility={handleToggleVisibility}
      >
        <SpeedGearWidget telemetryData={telemetryData} />
      </DraggableWidget>

      <DraggableWidget
        id="sessionInfo"
        title="Session Info"
        position={widgetPositions.sessionInfo}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.sessionInfo}
        onToggleVisibility={handleToggleVisibility}
      >
        <SessionInfoWidget
          telemetryData={telemetryData}
          sessionInfo={sessionInfo}
        />
      </DraggableWidget>

      <DraggableWidget
        id="userProfile"
        title="Driver Profile"
        position={widgetPositions.userProfile}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.userProfile}
        onToggleVisibility={handleToggleVisibility}
      >
        <UserProfileWidget isCoachingConnected={isCoachingConnected} />
      </DraggableWidget>

      <UpdateNotification />
    </div>
  );
};

export default GT3OverlaySystem;
