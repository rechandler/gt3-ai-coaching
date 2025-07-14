import React, { useEffect } from "react";

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
    case "braking":
      return "🛑";
    case "throttle":
      return "⚡";
    case "racing_line":
      return "🏁";
    case "baseline":
      return "📐";
    case "tip":
      return "💡";
    case "llm":
      return "🤖";
    default:
      return "🧠";
  }
};

const CoachingWidget = ({
  coachingMessages,
  clearMessages,
  markMessagesAsRead,
  isCoachingConnected,
  isConnected,
}) => {
  const MESSAGE_DISPLAY_TIME = 8000; // 8 seconds per message for better readability
  const MAX_MESSAGES = 4; // Reduced to 4 messages for better UI

  // Mark messages as no longer new after a brief period
  useEffect(() => {
    const timer = setTimeout(() => {
      markMessagesAsRead();
    }, 1000); // Give a bit more time for the "NEW" badge

    return () => clearTimeout(timer);
  }, [coachingMessages.length, markMessagesAsRead]);

  return (
    <div className="bg-gray-900 bg-opacity-95 rounded-lg p-3 min-h-16 w-96 border border-gray-600 shadow-xl">
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
        <div className="flex items-center space-x-2">
          {coachingMessages.length > 0 && (
            <button
              onClick={clearMessages}
              className="text-xs text-gray-400 hover:text-red-400 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
              title="Clear all messages"
            >
              Clear
            </button>
          )}
          <div className="text-xs text-gray-400">Auto-expire in 8s</div>
        </div>
      </div>

      {!isConnected || !isCoachingConnected ? (
        <div className="text-sm text-gray-300 mt-1">
          {!isConnected
            ? "Waiting for iRacing connection..."
            : "Connecting to AI coach..."}
        </div>
      ) : coachingMessages.length === 0 ? (
        <div className="text-sm text-gray-300">Analyzing your driving...</div>
      ) : (
        <div className="space-y-3 max-h-80 overflow-hidden">
          {/* Messages sorted to show newest at top */}
          {coachingMessages
            .sort((a, b) => b.timestamp - a.timestamp) // Newest first
            .slice(0, MAX_MESSAGES)
            .map((msg, index) => {
              const age = (Date.now() - msg.timestamp) / 1000;
              const remainingTime = Math.max(
                0,
                MESSAGE_DISPLAY_TIME / 1000 - age
              );

              return (
                <div
                  key={msg.id}
                  className="coaching-message-container bg-gray-800 bg-opacity-60 rounded-lg px-3 py-2 border-l-4 border-blue-400 transition-all duration-300"
                  style={{
                    transform: msg.isNew
                      ? "translateY(-10px)"
                      : "translateY(0)",
                    animationDuration: "0.4s",
                  }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm">
                        {getCategoryIcon(msg.category)}
                      </span>
                      <span className="text-xs text-gray-300 bg-gray-700 px-2 py-1 rounded">
                        P{msg.priority}
                      </span>
                      {msg.isNew && (
                        <span className="text-xs bg-blue-500 text-white px-2 py-1 rounded font-medium">
                          NEW
                        </span>
                      )}
                    </div>
                    <div className="flex flex-col items-end text-xs text-gray-400">
                      <span>{msg.confidence}%</span>
                      <span className="font-medium">
                        {Math.ceil(remainingTime)}s
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-gray-300 leading-relaxed">
                    {msg.message}
                  </div>
                  {msg.secondaryMessages &&
                    msg.secondaryMessages.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {msg.secondaryMessages.map((secondaryMsg, idx) => (
                          <div
                            key={idx}
                            className="text-xs text-gray-400 italic pl-2 border-l-2 border-gray-600"
                          >
                            {typeof secondaryMsg === "string"
                              ? secondaryMsg
                              : secondaryMsg.message}
                          </div>
                        ))}
                      </div>
                    )}
                  {msg.improvementPotential && (
                    <div className="text-xs text-green-400 mt-2">
                      Potential improvement:{" "}
                      {msg.improvementPotential.toFixed(2)}s
                    </div>
                  )}
                  {/* Progress bar showing time remaining */}
                  <div className="mt-2">
                    <div className="w-full bg-gray-600 rounded-full h-1">
                      <div
                        className="bg-blue-400 h-1 rounded-full transition-all duration-500"
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

export default CoachingWidget;
