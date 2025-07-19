import { useState, useEffect, useRef } from "react";

export const useCoachingMessages = () => {
  const [coachingMessages, setCoachingMessages] = useState([]);
  const [isCoachingConnected, setIsCoachingConnected] = useState(false);
  const [sessionInfo, setSessionInfo] = useState(null); // Add session info state
  const [telemetryData, setTelemetryData] = useState(null); // Add telemetry data state
  const [isTelemetryConnected, setIsTelemetryConnected] = useState(false); // Add telemetry connection state
  const coachingWs = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const MESSAGE_DISPLAY_TIME = 8000; // 8 seconds per message

  // Auto-cleanup expired messages
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
    }, 500); // Check every 500ms for smooth removal

    return () => clearInterval(interval);
  }, []); // Empty dependency array - this should run independently

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
                audio: message.data.audio || null, // Attach audio if present
              };

              // Update session info if provided
              if (message.data.session_info) {
                console.log(
                  "Received session info:",
                  message.data.session_info
                );
                setSessionInfo(message.data.session_info);
              }

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
            } else if (message.type === "sessionInfo" && message.data) {
              // Handle session info messages from coaching data service
              console.log("Received session info:", message.data);
              setSessionInfo(message.data);
            } else if (message.type === "session_info" && message.data.session_info) {
              // Handle session-info-only messages
              console.log("Received session info update:", message.data.session_info);
              setSessionInfo(message.data.session_info);
            } else if (message.type === "history" && message.messages) {
              console.log(
                "Received coaching message history:",
                message.messages.length
              );

              // Only load recent history (last 2 minutes) to avoid overwhelming the UI
              const currentTime = Date.now();
              const twoMinutesAgo = currentTime - (2 * 60 * 1000);

              const historyMessages = message.messages
                .filter((msg) => (msg.timestamp * 1000) > twoMinutesAgo) // Filter to recent messages only
                .map((msg) => ({
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
                  .slice(0, 4) // Match the max messages in UI
              );
            }
            // Handle telemetry messages
            if (message.type === "telemetry" && message.data) {
              setTelemetryData(message.data);
              setIsTelemetryConnected(true);
              return;
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
          setIsTelemetryConnected(false);

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
          setIsTelemetryConnected(false);
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

  // Function to manually clear all messages
  const clearMessages = () => {
    setCoachingMessages([]);
  };

  // Function to mark messages as no longer new
  const markMessagesAsRead = () => {
    setCoachingMessages((prev) =>
      prev.map((msg) => ({ ...msg, isNew: false }))
    );
  };

  return {
    coachingMessages,
    setCoachingMessages,
    clearMessages,
    markMessagesAsRead,
    isCoachingConnected,
    sessionInfo,
    telemetryData,
    isTelemetryConnected,
  };
};
