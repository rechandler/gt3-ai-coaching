import React, { useState, useEffect, useRef } from "react";
import {
  Settings,
  X,
  Move,
  Eye,
  EyeOff,
  RotateCcw,
  Wifi,
  WifiOff,
} from "lucide-react";
import UpdateNotification from "./UpdateNotification";

const useIRacingTelemetry = () => {
  const [telemetryData, setTelemetryData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  useEffect(() => {
    const connectWebSocket = () => {
      try {
        ws.current = new WebSocket("ws://localhost:8081");

        ws.current.onopen = () => {
          console.log("Connected to iRacing telemetry server");
          setIsConnected(true);
        };

        ws.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log("Received message:", message); // Debug log

            // Handle different message types
            if (message.type === "Telemetry" && message.data) {
              // Add specific delta time debugging
              if (
                message.data.deltaTime !== undefined ||
                message.data.deltaType !== undefined
              ) {
                console.log("Delta data:", {
                  deltaTime: message.data.deltaTime,
                  deltaType: message.data.deltaType,
                  onPitRoad: message.data.onPitRoad,
                  lapCurrentLapTime: message.data.lapCurrentLapTime,
                  lapBestLapTime: message.data.lapBestLapTime,
                });
              }

              // Add specific fuel debugging
              if (
                message.data.fuelLevel !== undefined ||
                message.data.fuelLevelPct !== undefined
              ) {
                console.log("Fuel data:", {
                  fuelLevel: message.data.fuelLevel,
                  fuelLevelPct: message.data.fuelLevelPct,
                  fuelUsePerHour: message.data.fuelUsePerHour,
                });
              }

              setTelemetryData(message.data);
              setIsConnected(
                message.isConnected || message.data.isConnected || false
              );
            } else if (message.type === "Connected") {
              setIsConnected(message.isConnected || false);
            } else if (message.type === "Disconnected") {
              setIsConnected(false);
            } else {
              // For backward compatibility, treat as direct telemetry data
              setTelemetryData(message);
              setIsConnected(message.isConnected || false);
            }
          } catch (error) {
            console.error("Error parsing telemetry data:", error);
          }
        };

        ws.current.onclose = () => {
          console.log("Disconnected from telemetry server");
          setIsConnected(false);
          setTimeout(connectWebSocket, 2000);
        };

        ws.current.onerror = (error) => {
          console.error("WebSocket error:", error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error("Failed to connect to WebSocket:", error);
        setIsConnected(false);
        setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return { telemetryData, isConnected };
};

const DraggableWidget = ({
  id,
  title,
  children,
  position,
  onPositionChange,
  isVisible,
  onToggleVisibility,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const widgetRef = useRef(null);

  const handleMouseDown = (e) => {
    if (e.target.closest(".widget-content")) return;

    setIsDragging(true);
    const rect = widgetRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
    e.preventDefault();
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;

    const newPosition = {
      x: e.clientX - dragOffset.x,
      y: e.clientY - dragOffset.y,
    };

    onPositionChange(id, newPosition);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  if (!isVisible) return null;

  return (
    <div
      ref={widgetRef}
      className={`fixed bg-black bg-opacity-80 backdrop-blur-sm border border-gray-600 rounded-lg shadow-lg transition-all duration-200 draggable-widget ${
        isDragging ? "cursor-grabbing shadow-xl scale-105" : "cursor-grab"
      }`}
      style={{
        left: position.x,
        top: position.y,
        zIndex: 2147483647, // Maximum z-index value to ensure always on top
        minWidth: "200px",
        pointerEvents: "auto", // Ensure widgets can receive mouse events
        position: "fixed", // Ensure fixed positioning works in fullscreen
      }}
      onMouseDown={handleMouseDown}
    >
      <div className="flex items-center justify-between p-2 bg-gray-800 rounded-t-lg">
        <div className="flex items-center space-x-2">
          <Move size={16} className="text-gray-400" />
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <button
          onClick={() => onToggleVisibility(id)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          <X size={16} />
        </button>
      </div>
      <div className="widget-content p-3">{children}</div>
    </div>
  );
};

const GT3OverlaySystem = () => {
  const { telemetryData, isConnected } = useIRacingTelemetry();
  const [showSettings, setShowSettings] = useState(false);

  // AI Coaching message management
  const [coachingMessages, setCoachingMessages] = useState([]);
  const [messageHistory, setMessageHistory] = useState(new Set());
  const messageTimersRef = useRef({});

  const MIN_MESSAGE_DISPLAY_TIME = 5000; // 5 seconds minimum display
  const MAX_MESSAGES = 3; // Maximum number of messages to display at once

  const [widgetPositions, setWidgetPositions] = useState({
    deltaTime: { x: 50, y: 50 },
    tireTemps: { x: 300, y: 50 },
    fuel: { x: 550, y: 50 },
    brakeTemps: { x: 50, y: 300 },
    coaching: { x: 300, y: 300 },
    speedGear: { x: 550, y: 300 },
    sessionInfo: { x: 50, y: 500 },
    userProfile: { x: 800, y: 50 },
  });

  const [widgetVisibility, setWidgetVisibility] = useState({
    deltaTime: true,
    tireTemps: true,
    fuel: true,
    brakeTemps: true,
    coaching: true,
    speedGear: true,
    sessionInfo: true,
    userProfile: false,
  });

  const handlePositionChange = (widgetId, newPosition) => {
    setWidgetPositions((prev) => ({
      ...prev,
      [widgetId]: newPosition,
    }));
  };

  const handleToggleVisibility = (widgetId) => {
    setWidgetVisibility((prev) => ({
      ...prev,
      [widgetId]: !prev[widgetId],
    }));
  };

  const resetPositions = () => {
    setWidgetPositions({
      deltaTime: { x: 50, y: 50 },
      tireTemps: { x: 300, y: 50 },
      fuel: { x: 550, y: 50 },
      brakeTemps: { x: 50, y: 300 },
      coaching: { x: 300, y: 300 },
      speedGear: { x: 550, y: 300 },
      sessionInfo: { x: 50, y: 500 },
      userProfile: { x: 800, y: 50 },
    });
  };

  const getTireColor = (temp) => {
    if (!temp) return "#6B7280";
    if (temp < 175) return "#3B82F6";
    if (temp < 200) return "#10B981";
    if (temp < 250) return "#F59E0B";
    return "#EF4444";
  };

  const getBrakeColor = (temp) => {
    if (!temp) return "#6B7280";
    if (temp < 800) return "#10B981";
    if (temp < 1200) return "#F59E0B";
    return "#EF4444";
  };

  const getCoachingColor = (category, priority) => {
    if (priority >= 9) return "bg-red-900 border-red-500";
    if (priority >= 7) return "bg-orange-900 border-orange-500";
    if (priority >= 5) return "bg-yellow-900 border-yellow-500";
    return "bg-blue-900 border-blue-500";
  };

  const getCategoryIcon = (category) => {
    switch (category) {
      case "critical":
        return "🚨";
      case "warning":
        return "⚠️";
      case "technique":
        return "🎯";
      case "strategy":
        return "📊";
      default:
        return "🧠";
    }
  };

  const DeltaTimeWidget = () => {
    const isInPits = telemetryData?.onPitRoad;
    const hasDelta =
      telemetryData?.deltaTime !== null &&
      telemetryData?.deltaTime !== undefined;

    const deltaType = telemetryData?.deltaType || "unknown";
    const deltaValue = telemetryData?.deltaTime;

    return (
      <div className="text-center">
        <div
          className={`text-4xl font-bold ${
            isInPits
              ? "text-gray-500"
              : hasDelta && deltaValue < 0
              ? "text-green-400"
              : hasDelta && deltaValue > 0
              ? "text-red-400"
              : "text-gray-400"
          }`}
        >
          {isInPits
            ? "PIT"
            : hasDelta
            ? `${deltaValue >= 0 ? "+" : ""}${deltaValue.toFixed(3)}`
            : "0.000"}
        </div>
        <div className="text-sm text-gray-400">
          {isInPits ? "In Pits" : `Delta Time (${deltaType})`}
        </div>
        {telemetryData?.lapBestLapTime && !isInPits && (
          <div className="text-xs text-gray-500 mt-1">
            Best: {telemetryData.lapBestLapTime.toFixed(3)}s
          </div>
        )}
        {/* Debug info - remove this once delta is working */}
        {!isInPits && !hasDelta && (
          <div className="text-xs text-red-400 mt-1">
            No delta data (type: {deltaType})
          </div>
        )}
      </div>
    );
  };

  const TireTempsWidget = () => (
    <div className="grid grid-cols-2 gap-2">
      <div className="text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-bold mx-auto"
          style={{ backgroundColor: getTireColor(telemetryData?.tireTempLF) }}
        >
          {telemetryData?.tireTempLF
            ? telemetryData.tireTempLF.toFixed(0)
            : "--"}
        </div>
        <div className="text-xs text-gray-400 mt-1">FL</div>
      </div>
      <div className="text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-bold mx-auto"
          style={{ backgroundColor: getTireColor(telemetryData?.tireTempRF) }}
        >
          {telemetryData?.tireTempRF
            ? telemetryData.tireTempRF.toFixed(0)
            : "--"}
        </div>
        <div className="text-xs text-gray-400 mt-1">FR</div>
      </div>
      <div className="text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-bold mx-auto"
          style={{ backgroundColor: getTireColor(telemetryData?.tireTempLR) }}
        >
          {telemetryData?.tireTempLR
            ? telemetryData.tireTempLR.toFixed(0)
            : "--"}
        </div>
        <div className="text-xs text-gray-400 mt-1">RL</div>
      </div>
      <div className="text-center">
        <div
          className="w-12 h-12 rounded-full flex items-center justify-center text-white text-xs font-bold mx-auto"
          style={{ backgroundColor: getTireColor(telemetryData?.tireTempRR) }}
        >
          {telemetryData?.tireTempRR
            ? telemetryData.tireTempRR.toFixed(0)
            : "--"}
        </div>
        <div className="text-xs text-gray-400 mt-1">RR</div>
      </div>
    </div>
  );

  const FuelWidget = () => {
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

  const BrakeTempsWidget = () => (
    <div className="space-y-2">
      <div className="flex justify-between">
        <span className="text-sm">FL</span>
        <span
          className="text-sm font-bold"
          style={{ color: getBrakeColor(telemetryData?.brakeTempLF) }}
        >
          {telemetryData?.brakeTempLF
            ? telemetryData.brakeTempLF.toFixed(0)
            : "--"}
          °F
        </span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm">FR</span>
        <span
          className="text-sm font-bold"
          style={{ color: getBrakeColor(telemetryData?.brakeTempRF) }}
        >
          {telemetryData?.brakeTempRF
            ? telemetryData.brakeTempRF.toFixed(0)
            : "--"}
          °F
        </span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm">RL</span>
        <span
          className="text-sm font-bold"
          style={{ color: getBrakeColor(telemetryData?.brakeTempLR) }}
        >
          {telemetryData?.brakeTempLR
            ? telemetryData.brakeTempLR.toFixed(0)
            : "--"}
          °F
        </span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm">RR</span>
        <span
          className="text-sm font-bold"
          style={{ color: getBrakeColor(telemetryData?.brakeTempRR) }}
        >
          {telemetryData?.brakeTempRR
            ? telemetryData.brakeTempRR.toFixed(0)
            : "--"}
          °F
        </span>
      </div>
      <div className="text-xs text-gray-400 text-center">Brake Temps</div>
    </div>
  );

  const CoachingWidget = () => {
    // If we have managed messages, display them; otherwise fall back to real-time data
    const displayMessages = coachingMessages.length > 0 ? coachingMessages : [];

    // For the main display, use the highest priority message or the most recent
    const primaryMessage =
      displayMessages.length > 0
        ? displayMessages.reduce((highest, current) =>
            current.priority > highest.priority ? current : highest
          )
        : null;

    const category =
      primaryMessage?.category || telemetryData?.coachingCategory || "general";
    const priority =
      primaryMessage?.priority || telemetryData?.coachingPriority || 0;
    const confidence =
      primaryMessage?.confidence || telemetryData?.coachingConfidence || 100;

    return (
      <div
        className={`bg-opacity-50 rounded p-2 min-h-16 w-80 border-l-4 ${getCoachingColor(
          category,
          priority
        )}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-blue-300">AI Coach</span>
            <span className="text-xs">{getCategoryIcon(category)}</span>
            {displayMessages.length > 1 && (
              <span className="text-xs bg-blue-600 text-white px-1 rounded">
                {displayMessages.length}
              </span>
            )}
          </div>
          <div className="text-xs text-gray-400">{confidence}% confident</div>
        </div>

        {/* Primary message */}
        <div className="text-sm text-white mt-1">
          {primaryMessage?.message ||
            telemetryData?.coachingMessage ||
            (isConnected
              ? "Analyzing..."
              : "Waiting for iRacing connection...")}
        </div>

        {/* Additional messages */}
        {displayMessages.length > 1 && (
          <div className="mt-2 space-y-1 max-h-24 overflow-y-auto">
            {displayMessages
              .filter((msg) => msg.id !== primaryMessage?.id)
              .slice(0, 2) // Show up to 2 additional messages
              .map((msg) => (
                <div
                  key={msg.id}
                  className={`text-xs rounded px-2 py-1 ${
                    msg.isSecondary
                      ? "text-gray-300 bg-gray-800 bg-opacity-50"
                      : "text-yellow-300 bg-yellow-900 bg-opacity-30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="flex-1">
                      {getCategoryIcon(msg.category)} {msg.message}
                    </span>
                    <span
                      className={`text-xs ml-2 ${
                        currentTime - msg.timestamp >
                        MIN_MESSAGE_DISPLAY_TIME * 0.8
                          ? "text-orange-400" // Message about to expire
                          : "opacity-60"
                      }`}
                    >
                      {Math.floor((currentTime - msg.timestamp) / 1000)}s
                    </span>
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Fallback to secondary messages from telemetry if no managed messages */}
        {displayMessages.length === 0 &&
          telemetryData?.secondaryMessages &&
          telemetryData.secondaryMessages.length > 0 && (
            <div className="mt-2 space-y-1">
              {telemetryData.secondaryMessages.slice(0, 2).map((msg, index) => (
                <div
                  key={index}
                  className="text-xs text-gray-300 bg-gray-800 bg-opacity-50 rounded px-2 py-1"
                >
                  {getCategoryIcon(msg.category)} {msg.message}
                </div>
              ))}
            </div>
          )}
      </div>
    );
  };

  const SpeedGearWidget = () => (
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

  const SessionInfoWidget = () => (
    <div className="space-y-2">
      <div className="text-sm font-medium text-white">
        {telemetryData?.carName || "No Car"}
      </div>
      <div className="text-xs text-gray-400">
        {telemetryData?.trackName || "No Track"}
      </div>
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">Lap:</span>
        <span className="text-white">{telemetryData?.lap || "--"}</span>
      </div>
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">Position:</span>
        <span className="text-white">P{telemetryData?.position || "--"}</span>
      </div>
    </div>
  );

  const UserProfileWidget = () => {
    const profile = telemetryData?.userProfile;
    if (!profile) return <div className="text-gray-400">No profile data</div>;

    return (
      <div className="space-y-2">
        <div className="text-sm font-medium text-white">Driver Profile</div>
        <div className="text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-400">Level:</span>
            <span className="text-white capitalize">
              {profile.experienceLevel}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Sessions:</span>
            <span className="text-white">{profile.sessionsCompleted}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Consistency:</span>
            <span className="text-white">
              {profile.consistency ? profile.consistency.toFixed(0) : "--"}%
            </span>
          </div>
          {profile.weakAreas && profile.weakAreas.length > 0 && (
            <div className="mt-2">
              <div className="text-xs text-gray-400 mb-1">Focus Areas:</div>
              {profile.weakAreas.map((area, index) => (
                <div
                  key={index}
                  className="text-xs text-orange-400 bg-orange-900 bg-opacity-30 rounded px-2 py-1 mb-1"
                >
                  {area.replace("_", " ")}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Add real-time timestamp updates for messages
  const [currentTime, setCurrentTime] = useState(Date.now());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(Date.now());
    }, 1000); // Update every second

    return () => clearInterval(timer);
  }, []);

  // Handle new coaching messages from telemetry
  useEffect(() => {
    if (telemetryData?.coachingMessage) {
      const newMessage = {
        id: Date.now() + Math.random(), // Unique ID
        message: telemetryData.coachingMessage,
        category: telemetryData.coachingCategory || "general",
        priority: telemetryData.coachingPriority || 0,
        confidence: telemetryData.coachingConfidence || 100,
        timestamp: Date.now(),
        hash: `${telemetryData.coachingMessage}_${telemetryData.coachingCategory}`, // For duplicate detection
      };

      // Check if this message is a duplicate
      if (!messageHistory.has(newMessage.hash)) {
        setCoachingMessages((prev) => {
          // Add new message
          const updated = [...prev, newMessage];

          // Keep only the most recent MAX_MESSAGES
          if (updated.length > MAX_MESSAGES) {
            updated.shift(); // Remove oldest message
          }

          return updated;
        });

        // Add to history to prevent duplicates
        setMessageHistory((prev) => new Set([...prev, newMessage.hash]));

        // Set timer to remove message after minimum display time
        messageTimersRef.current[newMessage.id] = setTimeout(() => {
          setCoachingMessages((prev) =>
            prev.filter((msg) => msg.id !== newMessage.id)
          );
          delete messageTimersRef.current[newMessage.id];
        }, MIN_MESSAGE_DISPLAY_TIME);
      }
    }
  }, [
    telemetryData?.coachingMessage,
    telemetryData?.coachingCategory,
    telemetryData?.coachingPriority,
  ]);

  // Handle secondary messages
  useEffect(() => {
    if (
      telemetryData?.secondaryMessages &&
      telemetryData.secondaryMessages.length > 0
    ) {
      telemetryData.secondaryMessages.forEach((secondaryMsg) => {
        const newMessage = {
          id: Date.now() + Math.random(),
          message: secondaryMsg.message,
          category: secondaryMsg.category || "general",
          priority: secondaryMsg.priority || 0,
          confidence: secondaryMsg.confidence || 100,
          timestamp: Date.now(),
          hash: `${secondaryMsg.message}_${secondaryMsg.category}`,
          isSecondary: true,
        };

        // Check for duplicates
        if (!messageHistory.has(newMessage.hash)) {
          setCoachingMessages((prev) => {
            const updated = [...prev, newMessage];
            if (updated.length > MAX_MESSAGES) {
              updated.shift();
            }
            return updated;
          });

          setMessageHistory((prev) => new Set([...prev, newMessage.hash]));

          // Shorter display time for secondary messages
          messageTimersRef.current[newMessage.id] = setTimeout(() => {
            setCoachingMessages((prev) =>
              prev.filter((msg) => msg.id !== newMessage.id)
            );
            delete messageTimersRef.current[newMessage.id];
          }, MIN_MESSAGE_DISPLAY_TIME * 0.8); // 4 seconds for secondary messages
        }
      });
    }
  }, [telemetryData?.secondaryMessages]);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      Object.values(messageTimersRef.current).forEach((timer) =>
        clearTimeout(timer)
      );
    };
  }, []);

  // Clear old message hashes periodically to prevent memory buildup
  useEffect(() => {
    const clearHistory = setInterval(() => {
      setMessageHistory(new Set()); // Clear duplicate detection history every 5 minutes
    }, 5 * 60 * 1000);

    return () => clearInterval(clearHistory);
  }, []);

  return (
    <div
      className="min-h-screen bg-transparent"
      style={{ pointerEvents: "none" }}
    >
      <div
        className="fixed top-4 right-4 z-50 flex items-center space-x-2"
        style={{ zIndex: 2147483647, pointerEvents: "auto" }}
      >
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
        <button
          onClick={() => setShowSettings(!showSettings)}
          className="bg-gray-800 bg-opacity-80 backdrop-blur-sm border border-gray-600 rounded-lg p-2 text-white hover:bg-gray-700 transition-colors"
        >
          <Settings size={20} />
        </button>
      </div>

      {showSettings && (
        <div
          className="fixed top-16 right-4 z-50 bg-gray-800 bg-opacity-90 backdrop-blur-sm border border-gray-600 rounded-lg p-4 min-w-64"
          style={{ zIndex: 2147483647, pointerEvents: "auto" }}
        >
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
              className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
            >
              <RotateCcw size={16} />
              <span>Reset Positions</span>
            </button>
          </div>
        </div>
      )}

      <DraggableWidget
        id="deltaTime"
        title="Delta Time"
        position={widgetPositions.deltaTime}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.deltaTime}
        onToggleVisibility={handleToggleVisibility}
      >
        <DeltaTimeWidget />
      </DraggableWidget>

      <DraggableWidget
        id="tireTemps"
        title="Tire Temps"
        position={widgetPositions.tireTemps}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.tireTemps}
        onToggleVisibility={handleToggleVisibility}
      >
        <TireTempsWidget />
      </DraggableWidget>

      <DraggableWidget
        id="fuel"
        title="Fuel"
        position={widgetPositions.fuel}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.fuel}
        onToggleVisibility={handleToggleVisibility}
      >
        <FuelWidget />
      </DraggableWidget>

      <DraggableWidget
        id="brakeTemps"
        title="Brake Temps"
        position={widgetPositions.brakeTemps}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.brakeTemps}
        onToggleVisibility={handleToggleVisibility}
      >
        <BrakeTempsWidget />
      </DraggableWidget>

      <DraggableWidget
        id="coaching"
        title="AI Coaching"
        position={widgetPositions.coaching}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.coaching}
        onToggleVisibility={handleToggleVisibility}
      >
        <CoachingWidget />
      </DraggableWidget>

      <DraggableWidget
        id="speedGear"
        title="Speed & Gear"
        position={widgetPositions.speedGear}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.speedGear}
        onToggleVisibility={handleToggleVisibility}
      >
        <SpeedGearWidget />
      </DraggableWidget>

      <DraggableWidget
        id="sessionInfo"
        title="Session Info"
        position={widgetPositions.sessionInfo}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.sessionInfo}
        onToggleVisibility={handleToggleVisibility}
      >
        <SessionInfoWidget />
      </DraggableWidget>

      <DraggableWidget
        id="userProfile"
        title="Driver Profile"
        position={widgetPositions.userProfile}
        onPositionChange={handlePositionChange}
        isVisible={widgetVisibility.userProfile}
        onToggleVisibility={handleToggleVisibility}
      >
        <UserProfileWidget />
      </DraggableWidget>

      <UpdateNotification />
    </div>
  );
};

export default GT3OverlaySystem;
