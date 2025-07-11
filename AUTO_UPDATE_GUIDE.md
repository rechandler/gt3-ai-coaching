# GT3 AI Coaching - Auto-Update Setup Guide

## Overview

The GT3 AI Coaching application now includes automatic update functionality using GitHub releases. When you publish a new version, users will automatically be notified and can update with one click.

## Quick Setup

### 1. Build with Auto-Update Support

```powershell
# Run the automated build script
.\build-with-updater.ps1
```

### 2. Configure GitHub Repository

Update the publish configuration in `package-electron.json`:

```json
"publish": {
  "provider": "github",
  "owner": "your-github-username",
  "repo": "gt3-ai-coaching",
  "private": false
}
```

### 3. Create a GitHub Release

1. Create a new tag: `git tag v1.0.1 && git push origin v1.0.1`
2. GitHub Actions will automatically build and create a release
3. Or manually upload the files from the `dist/` folder to a GitHub release

## How Auto-Updates Work

### For Users:

- **Startup Check**: App checks for updates when launched
- **Manual Check**: Click the "Check for Updates" button in the overlay
- **Notification**: Users see a notification when updates are available
- **One-Click Install**: Download and install with a single click
- **Auto-Restart**: App automatically restarts with the new version

### For Developers:

- **GitHub Integration**: Uses GitHub releases as the update server
- **Secure Downloads**: Updates are downloaded directly from GitHub
- **Automatic Signing**: Electron-builder handles code signing
- **Version Management**: Uses semantic versioning (e.g., v1.0.1)

## Files Added for Auto-Update

- `electron-updater.js` - Main process auto-updater integration
- `preload-updater.js` - Secure IPC bridge for renderer process
- `UpdateNotification.jsx` - React component for update UI
- `UpdateNotification.css` - Styling for update notifications
- `package-electron.json` - Electron-builder configuration with GitHub publishing
- `build-with-updater.ps1` - Automated build script
- `.github/workflows/build-release.yml` - GitHub Actions for automated releases

## Manual Release Process

If you prefer manual releases:

1. **Build the application:**

   ```powershell
   npm run build
   npx electron-builder --config package-electron.json
   ```

2. **Create GitHub Release:**

   - Go to your GitHub repository
   - Click "Releases" → "Create a new release"
   - Choose or create a tag (e.g., v1.0.1)
   - Upload these files from the `dist/` folder:
     - `GT3 AI Coaching Setup 1.0.1.exe` (installer)
     - `GT3 AI Coaching Setup 1.0.1.exe.blockmap` (update verification)
     - `latest.yml` (update metadata)

3. **Publish the release** - Users will be notified automatically

## Automated Release Process

The included GitHub Actions workflow automatically:

- Builds the app when you push a version tag
- Creates a GitHub release with the installer files
- Publishes update metadata for the auto-updater

To trigger an automated release:

```bash
git tag v1.0.1
git push origin v1.0.1
```

## Testing Auto-Updates

1. **Install Current Version**: Install the app normally
2. **Create Test Release**: Create a new release with a higher version number
3. **Launch App**: The installed app should detect the update
4. **Verify Update**: Check that the update notification appears

## Troubleshooting

### Updates Not Detected

- Verify the GitHub repository settings in `package-electron.json`
- Ensure the release includes `latest.yml` file
- Check that the version number in the release is higher than the installed version

### Update Download Fails

- Verify your GitHub repository is public or properly configured for private repos
- Check that all required files are included in the release
- Ensure the release is marked as "Latest release"

### Code Signing (Production)

For production releases, consider code signing:

```json
"win": {
  "certificateFile": "path/to/certificate.p12",
  "certificatePassword": "password"
}
```

## Security Notes

- Updates are downloaded from GitHub's secure CDN
- File integrity is verified using blockmap files
- The preload script uses context isolation for security
- No sensitive operations are exposed to the renderer process

## Version Management

Follow semantic versioning:

- **Patch**: v1.0.1 (bug fixes)
- **Minor**: v1.1.0 (new features)
- **Major**: v2.0.0 (breaking changes)

The auto-updater will notify users of any version increase and provide appropriate update messaging based on the version type.

---

Your GT3 AI Coaching application now has professional auto-update capabilities! Users will always have the latest features and improvements without manual intervention.
