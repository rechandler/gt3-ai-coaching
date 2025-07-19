import { useState } from "react";

export const useWidgetLayout = () => {
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

  return {
    widgetPositions,
    widgetVisibility,
    handlePositionChange,
    handleToggleVisibility,
    resetPositions,
  };
};
