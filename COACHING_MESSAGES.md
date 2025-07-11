# Enhanced AI Coaching Message System

## Overview

The GT3 AI Coaching system now features an improved message display system that handles multiple coaching tips simultaneously while preventing duplicate spam.

## New Features

### Multiple Message Display

- **Up to 4 messages** can be displayed simultaneously in the coaching widget
- Messages are **sorted by priority** (highest first)
- Each message shows its **priority level** (P1-P10) and **confidence percentage**

### Smart Duplicate Prevention

- **Frontend filtering**: Prevents identical messages from appearing within 12 seconds
- **Backend filtering**: AI coach won't generate the same message within 8 seconds
- **Critical message override**: High priority messages (P8+) can bypass cooldown for urgent warnings

### Message Persistence

- Messages stay visible for **12 seconds** (configurable)
- **Fade effect**: Messages gradually become more transparent as they age
- **"NEW" indicator**: Recently received messages are highlighted
- **Timestamp display**: Shows how long ago each message was received

### Visual Improvements

- **Color coding** by category and priority:
  - Red: Critical issues (P9-10)
  - Orange: Important warnings (P7-8)
  - Yellow: Moderate advice (P5-6)
  - Blue: General tips (P1-4)
- **Smooth animations**: Messages fade in/out with transitions
- **Clean layout**: Stacked message cards with clear visual hierarchy

## Configuration

### Frontend Settings (GT3Overlay.jsx)

```javascript
const MESSAGE_DISPLAY_TIME = 12000; // 12 seconds per message
const MAX_MESSAGES = 4; // Maximum messages to show at once
```

### Backend Settings (ai_coach.py)

```python
self.message_cooldown = 8.0  # Seconds before same message can be sent again
```

## Message Categories

The system recognizes these coaching categories:

- **braking**: Brake technique and temperature warnings
- **throttle**: Throttle application and traction advice
- **tires**: Tire temperature and pressure management
- **racing_line**: Racing line optimization
- **general**: Lap times, consistency, and overall performance

## Priority Levels

- **P10**: Critical safety warnings (brake overheating)
- **P8-9**: Important performance issues
- **P6-7**: Moderate advice and warnings
- **P4-5**: Technique improvements
- **P1-3**: General encouragement and minor tips

## Benefits

1. **No message spam**: Duplicate prevention ensures you won't see the same tip repeatedly
2. **Better visibility**: 12-second display time gives you enough time to read and process advice
3. **Priority awareness**: Important warnings are always visible and clearly marked
4. **Context retention**: Multiple messages let you see patterns in your driving
5. **Clean interface**: Professional appearance that doesn't clutter your screen

## Technical Details

- **Real-time filtering**: Both frontend and backend prevent duplicates
- **Memory efficient**: Automatic cleanup of expired messages
- **Performance optimized**: Minimal impact on racing performance
- **Responsive design**: Adapts to different message volumes smoothly
