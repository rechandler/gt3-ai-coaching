# GT3 AI Coach - Cloud Sync Setup Guide

The AI Coach supports **optional** cloud synchronization to backup your session data and access it from multiple devices.

## 🚀 Quick Start (Local Only)

```python
# Default setup - no cloud required
coach = LocalAICoach()  # All data stays local
```

## ☁️ Cloud Options

### Option 1: Firebase (Recommended - Free tier available)

#### Setup:

1. **Install Firebase SDK**:

```bash
pip install firebase-admin
```

2. **Create Firebase Project**:

   - Go to https://console.firebase.google.com
   - Create new project
   - Enable Firestore Database
   - Generate service account key (Settings > Service Accounts > Generate Key)

3. **Enable Cloud Sync**:

```python
# In your coaching server or main script
coach = LocalAICoach(cloud_sync_enabled=True)
coach.persistence_manager.setup_firebase_sync("path/to/serviceAccountKey.json")
```

#### Benefits:

- ✅ **Free tier**: 1GB storage, 50k reads/day
- ✅ **Real-time sync** across devices
- ✅ **Built-in backup** and versioning
- ✅ **Web dashboard** to view data

### Option 2: AWS S3

#### Setup:

1. **Install AWS SDK**:

```bash
pip install boto3
```

2. **Configure AWS**:

```python
aws_config = {
    'access_key': 'your_access_key',
    'secret_key': 'your_secret_key',
    'region': 'us-east-1',
    'bucket_name': 'gt3-coaching-data'
}

coach = LocalAICoach(cloud_sync_enabled=True)
coach.persistence_manager.setup_aws_sync(aws_config)
```

#### Benefits:

- ✅ **Extremely reliable** (99.999999999% durability)
- ✅ **Pay per use** (very cheap for session data)
- ✅ **Enterprise grade** security

### Option 3: Google Cloud Storage

#### Setup:

```bash
pip install google-cloud-storage
```

### Option 4: Custom API/Database

You can implement any custom cloud storage by overriding:

```python
def _sync_to_cloud(self, session_id: str):
    # Your custom implementation
    pass
```

## 🔧 How It Works

### Hybrid Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Local Files   │───▶│  Background     │───▶│   Cloud Store   │
│  (Immediate)    │    │  Sync Thread    │    │   (Backup)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
       ▲                         │                       │
       │                         │                       │
   Real-time                 Non-blocking              Multi-device
   Coaching                    Upload                    Access
```

1. **Local First**: All coaching works instantly from local files
2. **Background Sync**: Cloud uploads happen in background
3. **Fault Tolerant**: If cloud fails, local coaching continues
4. **Multi-Device**: Access your data from anywhere

### Data Synced

- ✅ **Session files**: Complete lap data and AI learning
- ✅ **Baselines**: Track/car specific performance data
- ✅ **Progress**: Best times, consistency improvements
- ✅ **Settings**: Driving style, coaching preferences

## 🎛️ Usage Examples

### Basic Usage (Local Only)

```python
coach = LocalAICoach()
coach.start_session("Fuji Speedway", "BMW M4 GT3")
# Data saved locally in coaching_data/
```

### With Firebase Cloud Sync

```python
coach = LocalAICoach(cloud_sync_enabled=True)
coach.persistence_manager.setup_firebase_sync("firebase-key.json")
coach.start_session("Fuji Speedway", "BMW M4 GT3")
# Data saved locally AND synced to Firebase
```

### Load Previous Sessions from Cloud

```python
# On a different computer
coach = LocalAICoach(cloud_sync_enabled=True)
coach.persistence_manager.setup_firebase_sync("firebase-key.json")

# Download previous sessions
previous = coach.get_previous_sessions(limit=5)
print(f"Found {len(previous)} previous sessions")

# Start with previous baseline
coach.start_session("Fuji Speedway", "BMW M4 GT3", load_previous=True)
```

### Reset Baseline Across All Devices

```python
coach.reset_baseline()  # Resets locally and in cloud
```

## 🔒 Security & Privacy

### Local Data

- Stored in `coaching_data/` folder
- Plain JSON files (can inspect/backup manually)
- No external connections unless cloud sync enabled

### Cloud Data (When Enabled)

- Encrypted in transit (HTTPS/TLS)
- Stored in your cloud account (you control access)
- Can be deleted anytime
- No personal info stored (just telemetry and lap times)

## 💾 Storage Requirements

### Local Storage

- ~1-5KB per lap
- ~100KB per session (20 laps)
- ~10MB for 100 sessions

### Cloud Storage

- Same as local
- Firebase free tier: 1GB (= ~10,000 sessions)
- AWS S3: ~$0.023 per GB per month

## 🛠️ Troubleshooting

### Cloud Sync Not Working

1. Check internet connection
2. Verify cloud credentials
3. Check logs: `logger.info` messages show sync status
4. Local coaching continues working regardless

### Lost Cloud Access

```python
# Download all sessions from cloud
sessions = coach.persistence_manager.find_previous_sessions(track, car, limit=100)

# Or disable cloud and continue locally
coach.persistence_manager.disable_cloud_sync()
```

### Migrate Between Cloud Providers

1. Export local data: Copy `coaching_data/` folder
2. Setup new cloud provider
3. Local files automatically sync to new cloud

## 🎯 Recommendations

- **For most users**: Start local-only, add Firebase later if needed
- **For sim racing teams**: Use AWS S3 with shared access
- **For privacy-focused**: Stay local-only
- **For multiple PCs**: Any cloud option works great

The system is designed to **work perfectly without any cloud setup** - cloud sync is purely a convenience feature!
