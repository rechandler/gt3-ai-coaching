import React, { useEffect, useRef, useMemo, useState } from "react";

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

const CoachingWidget = React.memo(({
  coachingMessages,
  setCoachingMessages,
  clearMessages,
  markMessagesAsRead,
  isCoachingConnected,
  isConnected,
}) => {
  const MESSAGE_DISPLAY_TIME = 8000; // 8 seconds per message for better readability
  const MAX_MESSAGES = 4; // Reduced to 4 messages for better UI
  
  // Use refs to track audio elements and prevent recreation
  const audioRefs = useRef(new Map());
  const blobUrls = useRef(new Set());
  const audioSources = useRef(new Map()); // Cache audio sources
  const renderCount = useRef(0);
  const [playingAudioId, setPlayingAudioId] = useState(null);

  // Track render count for debugging
  renderCount.current += 1;
  console.log(`CoachingWidget render #${renderCount.current}`);

  // Memoize sorted messages to prevent unnecessary re-renders
  const sortedMessages = useMemo(() => {
    return coachingMessages
      .sort((a, b) => b.timestamp - a.timestamp) // Newest first
      .slice(0, MAX_MESSAGES);
  }, [coachingMessages, MAX_MESSAGES]);

  // Mark messages as no longer new after a brief period
  useEffect(() => {
    const timer = setTimeout(() => {
      markMessagesAsRead();
    }, 1000); // Give a bit more time for the "NEW" badge

    return () => clearTimeout(timer);
  }, [coachingMessages.length, markMessagesAsRead]);

  // Cleanup blob URLs when component unmounts
  useEffect(() => {
    return () => {
      // Cleanup any blob URLs that were created
      blobUrls.current.forEach(url => {
        URL.revokeObjectURL(url);
      });
      blobUrls.current.clear();
      audioRefs.current.clear();
      audioSources.current.clear();
    };
  }, []);

  // Monitor audio element lifecycle
  useEffect(() => {
    const checkAudioElements = () => {
      audioRefs.current.forEach((audioElement, messageId) => {
        if (audioElement && !audioElement.parentNode) {
          console.warn(`Audio element for message ${messageId} was removed from DOM`);
        }
      });
    };

    const interval = setInterval(checkAudioElements, 1000);
    return () => clearInterval(interval);
  }, []);

  // Helper function to create audio source (memoized per message)
  const createAudioSource = useMemo(() => {
    return (audioData, messageId) => {
      if (!audioData) return null;
      
      // Check if we already have a cached audio source for this message
      if (audioSources.current.has(messageId)) {
        console.log(`Using cached audio source for message ${messageId}`);
        return audioSources.current.get(messageId);
      }
      
      console.log("Creating new audio source for message:", messageId);
      console.log("Audio data received:", audioData.substring(0, 100) + "...");
      
      let audioSrc = null;
      
      if (audioData.startsWith('http')) {
        audioSrc = audioData;
      } else if (audioData.startsWith('data:audio')) {
        audioSrc = audioData;
      } else {
        // Convert base64 to blob URL for better browser support
        try {
          const binaryString = atob(audioData);
          const bytes = new Uint8Array(binaryString.length);
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: 'audio/mp3' });
          const blobUrl = URL.createObjectURL(blob);
          blobUrls.current.add(blobUrl);
          audioSrc = blobUrl;
          console.log("Created blob URL for audio");
        } catch (e) {
          console.error("Error creating blob URL:", e);
          // Fallback to data URL
          audioSrc = `data:audio/mp3;base64,${audioData}`;
          console.log("Fallback to data URL");
        }
      }
      
      // Cache the audio source
      if (audioSrc) {
        audioSources.current.set(messageId, audioSrc);
      }
      
      return audioSrc;
    };
  }, []);

  // Handle audio play events
  const handleAudioPlay = (messageId) => {
    console.log(`Audio started playing for message ${messageId}`);
    setPlayingAudioId(messageId);
  };

  const handleAudioEnded = (messageId) => {
    console.log(`Audio finished for message ${messageId}`);
    audioRefs.current.delete(messageId);
    setPlayingAudioId(null);
  };

  const handleAudioError = (messageId, error) => {
    console.error(`Audio error for message ${messageId}:`, error);
    setPlayingAudioId(null);
  };

  const handleAudioLoadStart = (messageId) => {
    console.log(`Audio loading started for message ${messageId}`);
  };

  const handleAudioCanPlay = (messageId) => {
    console.log(`Audio can play for message ${messageId}`);
  };

  const handleAudioPause = (messageId) => {
    console.log(`Audio paused for message ${messageId}`);
    setPlayingAudioId(null);
  };

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
          <button
            onClick={() => {
              // Add a test message with audio
              const testMessage = {
                id: `test_${Date.now()}`,
                message: "Test message with audio - Brake earlier for turn 1",
                category: "test",
                priority: 5,
                confidence: 90,
                timestamp: Date.now(),
                isNew: true,
                secondaryMessages: [],
                improvementPotential: null,
                // Longer test audio (3 seconds of silence with proper WAV header)
                audio: "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
              };
              setCoachingMessages(prev => [testMessage, ...prev.slice(0, 3)]);
            }}
            className="text-xs text-blue-400 hover:text-blue-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
            title="Test audio"
          >
            Test Audio
          </button>
          <button
            onClick={() => {
              // Add a test message with longer audio
              const testMessage = {
                id: `test_long_${Date.now()}`,
                message: "Test message with longer audio - Focus on your racing line",
                category: "test",
                priority: 5,
                confidence: 90,
                timestamp: Date.now(),
                isNew: true,
                secondaryMessages: [],
                improvementPotential: null,
                // Create a longer test audio using data URL
                audio: "data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUarm7blmGgU7k9n1unEiBC13yO/eizEIHWq+8+OWT"
              };
              setCoachingMessages(prev => [testMessage, ...prev.slice(0, 3)]);
            }}
            className="text-xs text-green-400 hover:text-green-300 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
            title="Test longer audio"
          >
            Test Long Audio
          </button>
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
          {sortedMessages.map((msg, index) => {
            const age = (Date.now() - msg.timestamp) / 1000;
            const remainingTime = Math.max(
              0,
              MESSAGE_DISPLAY_TIME / 1000 - age
            );

            // Audio playback: only for the newest message
            const isNewest = index === 0;
            let audioSrc = null;
            
            if (msg.audio && isNewest) {
              audioSrc = createAudioSource(msg.audio, msg.id);
              console.log("Audio source for message:", msg.id, audioSrc ? "Yes" : "No");
            } else {
              console.log("No audio data in message or not newest");
            }

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
                {/* Audio playback for newest message only */}
                {isNewest && audioSrc && (
                  <div className="mt-2">
                    <audio 
                      ref={(el) => {
                        if (el) {
                          audioRefs.current.set(msg.id, el);
                          console.log(`Audio element created for message ${msg.id}`);
                        }
                      }}
                      src={audioSrc} 
                      controls 
                      autoPlay 
                      style={{ width: '100%' }}
                      onError={(e) => handleAudioError(msg.id, e)}
                      onLoadStart={() => handleAudioLoadStart(msg.id)}
                      onCanPlay={() => handleAudioCanPlay(msg.id)}
                      onPlay={() => handleAudioPlay(msg.id)}
                      onPause={() => handleAudioPause(msg.id)}
                      onEnded={() => handleAudioEnded(msg.id)}
                    />
                    {playingAudioId === msg.id && (
                      <div className="text-xs text-green-400 mt-1">
                        🔊 Playing audio...
                      </div>
                    )}
                  </div>
                )}
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
                    Potential improvement: {" "}
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
});

CoachingWidget.displayName = 'CoachingWidget';

export default CoachingWidget;
