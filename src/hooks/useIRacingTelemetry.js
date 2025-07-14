import { useState, useEffect, useRef } from "react";

export const useIRacingTelemetry = () => {
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
        telemetryWs.current = new WebSocket("ws://localhost:8082");

        telemetryWs.current.onopen = () => {
          console.log("Connected to iRacing telemetry server");
          setIsConnected(true);
        };

        telemetryWs.current.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);

            // Handle different message types
            if ((message.type === "Telemetry" || message.type === "telemetry") && message.data) {
              setTelemetryData(message.data);
              setIsConnected(
                message.isConnected || message.data.isConnected || true // Default to true if telemetry data is received
              );
            } else if (message.type === "Connected" || message.type === "connected") {
              setIsConnected(message.isConnected !== false); // Default to true unless explicitly false
            } else if (message.type === "Disconnected" || message.type === "disconnected") {
              setIsConnected(false);
            } else {
              // For backward compatibility, treat as direct telemetry data
              setTelemetryData(message);
              setIsConnected(message.isConnected !== false); // Default to true unless explicitly false
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
