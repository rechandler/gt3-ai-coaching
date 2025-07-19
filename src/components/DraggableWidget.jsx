import React, { useState, useRef, useCallback, useEffect } from "react";
import { Move, X } from "lucide-react";

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

export default DraggableWidget;
