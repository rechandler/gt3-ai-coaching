import React, { useState, useEffect, useRef, useCallback } from "react";
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
  const telemetryWs = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    const connectWebSocket = () => {
      // Clear any existing connection
      if (telemetryWs.current) {
        try {
          telemetryWs.current.close();
        } catch (error) {
          console.warn("Error closing existing telemetry WebSocket:", error);
        }
        telemetryWs.current = null;
      }

      try {
        telemetryWs.current = new WebSocket("ws://localhost:8081");

        telemetryWs.current.onopen = () => {
          console.log("Connected to iRacing telemetry server");
          setIsConnected(true);
        };

        telemetryWs.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            // Handle different message types
            if (message.type === "Telemetry" && message.data) {
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

        telemetryWs.current.onclose = (event) => {
          console.log(
            "Disconnected from telemetry server",
            event.code,
            event.reason
          );
          setIsConnected(false);

          // Clear the WebSocket reference
          telemetryWs.current = null;

          // Only reconnect if it wasn't a manual close (code 1000)
          if (event.code !== 1000) {
            reconnectTimeoutRef.current = setTimeout(connectWebSocket, 2000);
          }
        };

        telemetryWs.current.onerror = (error) => {
          console.error("WebSocket error:", error);
          setIsConnected(false);
        };
      } catch (error) {
        console.error("Failed to connect to WebSocket:", error);
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
      }
    };

    connectWebSocket();

    return () => {
      // Clear reconnection timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close WebSocket connection
      if (telemetryWs.current) {
        try {
          telemetryWs.current.close(1000, "Component unmounting");
        } catch (error) {
          console.warn("Error closing telemetry WebSocket on cleanup:", error);
        }
        telemetryWs.current = null;
      }
    };
  }, []);

  return { telemetryData, isConnected };
};

const useCoachingMessages = () => {
  const [coachingMessages, setCoachingMessages] = useState([]);
  const [isCoachingConnected, setIsCoachingConnected] = useState(false);
  const coachingWs = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    const connectCoachingWebSocket = () => {
      // Clear any existing connection
      if (coachingWs.current) {
        try {
          coachingWs.current.close();
        } catch (error) {
          console.warn("Error closing existing coaching WebSocket:", error);
        }
        coachingWs.current = null;
      }

      try {
        coachingWs.current = new WebSocket("ws://localhost:8082");

        coachingWs.current.onopen = () => {
          console.log("Connected to AI coaching server");
          setIsCoachingConnected(true);

          // Request recent message history
          try {
            if (
              coachingWs.current &&
              coachingWs.current.readyState === WebSocket.OPEN
            ) {
              coachingWs.current.send(
                JSON.stringify({
                  type: "get_history",
                  count: 5,
                })
              );
            }
          } catch (error) {
            console.error("Error sending history request:", error);
          }
        };

        coachingWs.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === "coaching" && message.data) {
              console.log("Received coaching message:", message.data);

              const newMessage = {
                id: message.id,
                message: message.data.message,
                category: message.data.category || "general",
                priority: message.data.priority || 0,
                confidence: message.data.confidence || 100,
                timestamp: message.timestamp * 1000, // Convert to ms
                isNew: true,
                secondaryMessages: message.data.secondary_messages || [],
                improvementPotential: message.data.improvement_potential,
              };

              setCoachingMessages((prev) => {
                // Check if this message already exists
                const exists = prev.some((msg) => msg.id === newMessage.id);
                if (exists) {
                  return prev;
                }

                // Add new message at the beginning (top) and keep sorted by timestamp (newest first)
                const updated = [newMessage, ...prev]
                  .sort((a, b) => b.timestamp - a.timestamp)
                  .slice(0, 6); // Keep max 6 messages for the improved UI

                return updated;
              });
            } else if (message.type === "history" && message.messages) {
              console.log(
                "Received coaching message history:",
                message.messages.length
              );

              const historyMessages = message.messages.map((msg) => ({
                id: msg.id,
                message: msg.data.message,
                category: msg.data.category || "general",
                priority: msg.data.priority || 0,
                confidence: msg.data.confidence || 100,
                timestamp: msg.timestamp * 1000,
                isNew: false,
                secondaryMessages: msg.data.secondary_messages || [],
                improvementPotential: msg.data.improvement_potential,
              }));

              setCoachingMessages(
                historyMessages
                  .sort((a, b) => b.timestamp - a.timestamp)
                  .slice(0, 6)
              );
            }
          } catch (error) {
            console.error("Error parsing coaching message:", error);
          }
        };

        coachingWs.current.onclose = (event) => {
          console.log(
            "Disconnected from coaching server",
            event.code,
            event.reason
          );
          setIsCoachingConnected(false);

          // Clear the WebSocket reference
          coachingWs.current = null;

          // Only reconnect if it wasn't a manual close (code 1000)
          if (event.code !== 1000) {
            reconnectTimeoutRef.current = setTimeout(
              connectCoachingWebSocket,
              2000
            );
          }
        };

        coachingWs.current.onerror = (error) => {
          console.error("Coaching WebSocket error:", error);
          setIsCoachingConnected(false);
        };
      } catch (error) {
        console.error("Failed to connect to coaching WebSocket:", error);
        setIsCoachingConnected(false);
        reconnectTimeoutRef.current = setTimeout(
          connectCoachingWebSocket,
          5000
        );
      }
    };

    connectCoachingWebSocket();

    return () => {
      // Clear reconnection timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      // Close WebSocket connection
      if (coachingWs.current) {
        try {
          coachingWs.current.close(1000, "Component unmounting");
        } catch (error) {
          console.warn("Error closing coaching WebSocket on cleanup:", error);
        }
        coachingWs.current = null;
      }
    };
  }, []);

  return { coachingMessages, setCoachingMessages, isCoachingConnected };
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
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const widgetRef = useRef(null);

  const startDrag = useCallback(
    (e) => {
      console.log(
        "Mouse down on header for widget:",
        id,
        "Target:",
        e.target.tagName
      );

      setIsDragging(true);
      setDragStart({
        x: e.clientX - position.x,
        y: e.clientY - position.y,
      });

      document.body.style.userSelect = "none";
      e.preventDefault();
    },
    [position.x, position.y, id]
  );

  const onDrag = useCallback(
    (e) => {
      if (!isDragging) return;

      console.log("Dragging widget:", id);

      const newX = e.clientX - dragStart.x;
      const newY = e.clientY - dragStart.y;

      onPositionChange(id, { x: newX, y: newY });
    },
    [isDragging, dragStart.x, dragStart.y, onPositionChange, id]
  );

  const stopDrag = useCallback(() => {
    console.log("Stopping drag for widget:", id);
    setIsDragging(false);
    document.body.style.userSelect = "";
  }, [id]);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener("mousemove", onDrag);
      document.addEventListener("mouseup", stopDrag);

      return () => {
        document.removeEventListener("mousemove", onDrag);
        document.removeEventListener("mouseup", stopDrag);
      };
    }
  }, [isDragging, onDrag, stopDrag]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      document.body.style.userSelect = "";
    };
  }, []);

  if (!isVisible) return null;

  return (
    <div
      ref={widgetRef}
      className={`fixed bg-black bg-opacity-80 backdrop-blur-sm border border-gray-600 rounded-lg shadow-lg ${
        isDragging ? "shadow-xl scale-105" : ""
      }`}
      style={{
        left: position.x,
        top: position.y,
        zIndex: isDragging ? 1001 : 1000,
        minWidth: "200px",
        transition: isDragging ? "none" : "all 0.2s",
        pointerEvents: "auto",
      }}
    >
      <div
        className={`widget-header flex items-center justify-between p-2 bg-gray-800 rounded-t-lg transition-colors hover:bg-gray-700 ${
          isDragging ? "cursor-grabbing bg-gray-700" : "cursor-grab"
        }`}
        onMouseDown={startDrag}
        onMouseEnter={() => console.log("Hovering over header for widget:", id)}
        style={{
          userSelect: "none",
          WebkitUserSelect: "none",
          MozUserSelect: "none",
          msUserSelect: "none",
          cursor: isDragging ? "grabbing" : "grab",
          pointerEvents: "auto",
        }}
      >
        <div className="flex items-center space-x-2">
          <Move
            size={16}
            className={`transition-colors ${
              isDragging ? "text-blue-400" : "text-gray-400 hover:text-gray-200"
            }`}
          />
          <span className="text-sm font-medium text-white">{title}</span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleVisibility(id);
          }}
          onMouseDown={(e) => e.stopPropagation()}
          className="text-gray-400 hover:text-white transition-colors hover:bg-gray-600 rounded p-1"
          style={{ cursor: "pointer" }}
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
  const { coachingMessages, setCoachingMessages, isCoachingConnected } =
    useCoachingMessages();
  const [showSettings, setShowSettings] = useState(false);

  const [widgetPositions, setWidgetPositions] = useState({
    deltaTime: { x: 50, y: 50 },
    fuel: { x: 550, y: 50 },
    coaching: { x: 300, y: 300 },
    speedGear: { x: 550, y: 300 },
    sessionInfo: { x: 50, y: 500 },
    userProfile: { x: 800, y: 50 },
  });

  const [widgetVisibility, setWidgetVisibility] = useState({
    deltaTime: true,
    fuel: true,
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
      fuel: { x: 550, y: 50 },
      coaching: { x: 300, y: 300 },
      speedGear: { x: 550, y: 300 },
      sessionInfo: { x: 50, y: 500 },
      userProfile: { x: 800, y: 50 },
    });
  };

  // Note: Tire and brake temperature color functions removed since iRacing doesn't provide reliable data

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

  // Note: TireTempsWidget removed - iRacing doesn't provide reliable tire temperature data

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

  // Note: BrakeTempsWidget removed - iRacing doesn't provide reliable brake temperature data

  const CoachingWidget = () => {
    const MESSAGE_DISPLAY_TIME = 5000; // 5 seconds per message as requested
    const MAX_MESSAGES = 6; // Maximum messages to show at once

    // Clean up expired messages - remove them completely from the UI
    useEffect(() => {
      const interval = setInterval(() => {
        setCoachingMessages((prev) => {
          const currentTime = Date.now();
          const filtered = prev.filter((msg) => {
            const messageAge = currentTime - msg.timestamp;
            const isExpired = messageAge >= MESSAGE_DISPLAY_TIME;

            if (isExpired) {
              console.log(
                `Message auto-expired and removed: "${msg.message}" (${(
                  messageAge / 1000
                ).toFixed(1)}s old)`
              );
            }

            return !isExpired; // Only keep non-expired messages
          });

          // Log when messages are removed
          if (filtered.length !== prev.length) {
            console.log(
              `Auto-removed ${
                prev.length - filtered.length
              } expired messages. Remaining: ${filtered.length}`
            );
          }

          return filtered;
        });
      }, 100); // Check every 100ms for smooth removal

      return () => clearInterval(interval);
    }, [setCoachingMessages]);

    // Mark messages as no longer new after a brief period
    useEffect(() => {
      const timer = setTimeout(() => {
        setCoachingMessages((prev) =>
          prev.map((msg) => ({ ...msg, isNew: false }))
        );
      }, 800);

      return () => clearTimeout(timer);
    }, [coachingMessages.length, setCoachingMessages]);

    return (
      <div className="bg-opacity-50 rounded p-2 min-h-16 w-96 border-l-4 border-blue-500">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-blue-300">AI Coach</span>
            <span className="text-xs">🧠</span>
            {isCoachingConnected ? (
              <span className="text-xs text-green-400">●</span>
            ) : (
              <span className="text-xs text-red-400">●</span>
            )}
          </div>
          <div className="text-xs text-gray-400">Auto-expire in 5s</div>
        </div>

        {!isConnected || !isCoachingConnected ? (
          <div className="text-sm text-gray-400 mt-1">
            {!isConnected
              ? "Waiting for iRacing connection..."
              : "Connecting to AI coach..."}
          </div>
        ) : coachingMessages.length === 0 ? (
          <div className="text-sm text-gray-400">Analyzing your driving...</div>
        ) : (
          <div className="space-y-2 max-h-80 overflow-hidden">
            {/* Messages sorted to show newest at top and scroll down */}
            {coachingMessages
              .sort((a, b) => b.timestamp - a.timestamp) // Newest first
              .slice(0, MAX_MESSAGES)
              .map((msg, index) => {
                const age = (Date.now() - msg.timestamp) / 1000;
                const remainingTime = Math.max(
                  0,
                  MESSAGE_DISPLAY_TIME / 1000 - age
                );

                // Since messages are auto-removed when expired, we don't need opacity fading
                const opacity = 1; // Always full opacity since expired messages are removed

                return (
                  <div
                    key={msg.id}
                    className={`coaching-message-container transition-all duration-300 transform ${
                      msg.isNew ? "animate-slideInDown" : ""
                    } ${getCoachingColor(msg.category, msg.priority)} 
                    rounded-lg px-3 py-2 border-l-4 shadow-lg hover:shadow-xl`}
                    style={{
                      opacity,
                      transform: msg.isNew
                        ? "translateY(-10px)"
                        : "translateY(0)",
                      animationDuration: "0.4s",
                    }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm">
                          {getCategoryIcon(msg.category)}
                        </span>
                        <span className="text-xs font-bold text-white bg-black bg-opacity-30 px-1.5 py-0.5 rounded">
                          P{msg.priority}
                        </span>
                        {msg.isNew && (
                          <span className="text-xs bg-blue-500 text-white px-1.5 py-0.5 rounded font-medium animate-pulse">
                            NEW
                          </span>
                        )}
                      </div>
                      <div className="flex flex-col items-end text-xs text-gray-300">
                        <span>{msg.confidence}%</span>
                        <span className="text-xs text-gray-400 font-medium">
                          {Math.ceil(remainingTime)}s
                        </span>
                      </div>
                    </div>
                    <div className="text-sm text-white mt-2 leading-relaxed font-medium">
                      {msg.message}
                    </div>
                    {msg.improvementPotential && (
                      <div className="text-xs text-green-400 mt-1 font-medium">
                        Potential improvement:{" "}
                        {msg.improvementPotential.toFixed(2)}s
                      </div>
                    )}
                    {/* Progress bar showing time remaining */}
                    <div className="mt-2">
                      <div className="w-full bg-black bg-opacity-30 rounded-full h-1">
                        <div
                          className="bg-blue-400 h-1 rounded-full transition-all duration-100"
                          style={{
                            width: `${Math.max(
                              0,
                              (remainingTime / (MESSAGE_DISPLAY_TIME / 1000)) *
                                100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
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
    // User profile data will now come from the coaching server
    // For now, show a placeholder
    return (
      <div className="space-y-2">
        <div className="text-sm font-medium text-white">Driver Profile</div>
        <div className="text-xs space-y-1">
          <div className="flex justify-between">
            <span className="text-gray-400">Status:</span>
            <span className="text-white">
              {isCoachingConnected ? "AI Active" : "Offline"}
            </span>
          </div>
          <div className="text-xs text-gray-400">
            Profile data will be available via coaching server
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-transparent">
      <div className="fixed top-4 right-4 z-50 flex items-center space-x-2">
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

      {/* Note: Tire and brake temperature widgets removed - iRacing doesn't provide reliable data */}

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
