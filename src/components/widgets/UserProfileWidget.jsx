import React from "react";

const UserProfileWidget = ({ isCoachingConnected }) => {
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

export default UserProfileWidget;
