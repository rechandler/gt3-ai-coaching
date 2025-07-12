# Firebase Session History Setup

This guide will help you set up Firebase for cloud syncing your GT3 AI coaching sessions.

## Quick Start (Anonymous Users)

The app will automatically sign users in anonymously, so cloud sync works immediately without any setup. However, for production use, you'll want to set up a proper Firebase project.

## Firebase Project Setup

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Enter project name: `gt3-ai-coaching` (or whatever you prefer)
4. Enable Google Analytics (optional)
5. Click "Create project"

### 2. Enable Authentication

1. In your Firebase project, go to **Authentication** > **Sign-in method**
2. Enable these providers:
   - **Anonymous** ✅ (for instant access)
   - **Email/Password** ✅ (for upgrading anonymous users)
   - **Google** (optional, for easy sign-in)

### 3. Setup Firestore Database

1. Go to **Firestore Database**
2. Click "Create database"
3. Start in **test mode** (we'll secure it later)
4. Choose a location closest to your users

### 4. Configure Security Rules

Replace the default Firestore rules with:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own sessions
    match /sessions/{sessionId} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.userId;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.userId;
    }

    // Users can access their own preferences
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### 5. Get Configuration

1. Go to **Project Settings** > **General**
2. Scroll to "Your apps" section
3. Click "Web app" (</>) icon
4. Register app with nickname: `gt3-overlay`
5. Copy the config object

### 6. Environment Variables

1. Copy `.env.example` to `.env.local`
2. Fill in your Firebase configuration:

```env
REACT_APP_FIREBASE_API_KEY=your_api_key_here
REACT_APP_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
REACT_APP_FIREBASE_PROJECT_ID=your_project_id
REACT_APP_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=123456789
REACT_APP_FIREBASE_APP_ID=1:123456789:web:abcdef123456
```

## Features

### What Gets Synced

- ✅ **Session Records** - Track name, car, start/end time
- ✅ **Coaching Messages** - All AI feedback with priorities
- ✅ **Lap Times** - Best times and lap-by-lap data
- ✅ **Session Statistics** - Total laps, fuel usage, etc.

### How It Works

1. **Auto Sign-in**: Users are automatically signed in anonymously
2. **Session Detection**: New session starts when you connect to iRacing
3. **Real-time Sync**: Coaching messages and lap times sync as they happen
4. **Session End**: Session ends when you disconnect from iRacing
5. **History**: View all past sessions in the cloud

### User Journey

```
Anonymous User → iRacing Session → Data Synced → Optional Account Upgrade
```

### Authentication Options

1. **Anonymous** (default): Instant access, data tied to device
2. **Email/Password**: Create account to access data across devices
3. **Upgrade**: Convert anonymous account to permanent account

## Data Structure

```javascript
// Session document
{
  userId: "user123",
  startTime: timestamp,
  endTime: timestamp,
  track_name: "Spa-Francorchamps",
  car_name: "BMW M4 GT3",
  session_type: "Practice",
  coaching_messages: [
    {
      id: "msg123",
      message: "Brake earlier for turn 1",
      category: "technique",
      priority: 7,
      timestamp: timestamp
    }
  ],
  lap_times: [
    {
      lap_number: 1,
      lap_time: 142.345,
      timestamp: timestamp
    }
  ],
  best_lap_time: 142.345,
  total_laps: 15
}
```

## Development Mode

For local development, the app can use Firebase emulators:

```bash
npm install -g firebase-tools
firebase login
firebase init emulators
firebase emulators:start
```

This lets you test without affecting production data.

## Privacy & Security

- Each user can only access their own data
- Anonymous users get a unique ID tied to their device
- No personal information required to start using
- Optional account creation for cross-device access
- All data encrypted in transit and at rest
