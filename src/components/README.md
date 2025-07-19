# GT3 Overlay Components

This directory contains the modular components that make up the GT3 AI Coaching overlay system.

## Component Structure

### Main Components

- **`GT3Overlay.jsx`** - Main orchestrating component that brings everything together
- **`DraggableWidget.jsx`** - Reusable draggable container for all widgets
- **`StatusIndicators.jsx`** - Connection status indicators (iRacing, Cloud)
- **`SettingsPanel.jsx`** - Settings overlay with widget visibility controls

### Widgets (`/widgets/`)

Individual widget components that display specific data:

- **`DeltaTimeWidget.jsx`** - Shows lap time delta information
- **`FuelWidget.jsx`** - Displays fuel level and estimated laps remaining
- **`SpeedGearWidget.jsx`** - Shows current speed and gear
- **`SessionInfoWidget.jsx`** - Displays session and car information
- **`UserProfileWidget.jsx`** - Driver profile information
- **`CoachingWidget.jsx`** - AI coaching messages display

## Benefits of This Structure

1. **Modularity** - Each component has a single responsibility
2. **Reusability** - Components can be easily reused or tested independently
3. **Maintainability** - Easier to find and modify specific functionality
4. **Performance** - React can optimize re-renders more effectively
5. **Testing** - Each component can be unit tested in isolation

## Adding New Widgets

To add a new widget:

1. Create a new component file in the `widgets/` directory
2. Export it from `widgets/index.js`
3. Import and use it in `GT3Overlay.jsx` with a `DraggableWidget` wrapper
4. Add the widget to the `useWidgetLayout` hook for position management

## Component Props

### DraggableWidget

- `id` - Unique identifier for the widget
- `title` - Display title in the header
- `children` - The actual widget content
- `position` - Current position {x, y}
- `onPositionChange` - Callback for position updates
- `isVisible` - Visibility state
- `onToggleVisibility` - Callback for visibility changes

### Individual Widgets

Most widgets receive `telemetryData` and other relevant props based on their specific needs.
