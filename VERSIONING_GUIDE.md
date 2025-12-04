# Versioning System Guide

## Overview

The application now has a proper versioning system that allows you to verify deployments. Each deployment automatically bumps the version and verifies it matches on the server.

## Version Endpoint

### Get Version Information

**Endpoint:** `GET /api/config/version/`

**Response:**
```json
{
  "success": true,
  "message": "Version information retrieved successfully",
  "data": {
    "version": "1.0.1",
    "commit_hash": "a1b2c3d",
    "branch": "main",
    "commit_date": "2025-01-15 10:30:00 +0000"
  }
}
```

**No authentication required** - Public endpoint for verification

## How It Works

### 1. Version File

Version is stored in `VERSION` file at project root:
```
1.0.0
```

### 2. Automatic Version Bumping

When you push to `main` branch:
1. GitHub Actions workflow runs
2. Automatically bumps patch version (1.0.0 → 1.0.1)
3. Commits version bump back to repo
4. Deploys to server
5. Verifies deployed version matches expected version

### 3. Version Verification

After deployment, the workflow:
- Checks `/api/config/version/` endpoint
- Compares deployed version with expected version
- Reports success/failure

## Manual Version Bumping

If you need to bump version manually:

```bash
# Bump patch version (1.0.0 → 1.0.1)
./bump_version.sh patch

# Bump minor version (1.0.0 → 1.1.0)
./bump_version.sh minor

# Bump major version (1.0.0 → 2.0.0)
./bump_version.sh major
```

Then commit:
```bash
git add VERSION
git commit -m "Bump version to 1.0.1"
git push origin main
```

## Verifying Deployment

### Check Version on Server

```bash
# Get version from API
curl http://69.62.126.95/api/config/version/

# Or check locally
curl http://localhost:8000/api/config/version/
```

### Compare Versions

```bash
# Local version
cat VERSION

# Server version
curl -s http://69.62.126.95/api/config/version/ | grep -o '"version":"[^"]*' | cut -d'"' -f4
```

### Verify Deployment Worked

After deployment, check GitHub Actions logs:
- Look for "Version matches! Deployment verified."
- If version mismatch, deployment might have issues

## Version Format

Uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes (1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (1.0.0 → 1.1.0)
- **PATCH**: Bug fixes, backward compatible (1.0.0 → 1.0.1)

## Deployment Workflow

1. **Push code** → Triggers GitHub Actions
2. **Version bumped** → Automatically incremented
3. **Code deployed** → Pulled to server
4. **Service restarted** → Gunicorn reloaded
5. **Version verified** → Checked via API endpoint
6. **Success reported** → In GitHub Actions logs

## Troubleshooting

### Version Mismatch

If deployed version doesn't match expected:

1. **Check if code was pulled:**
   ```bash
   ssh root@69.62.126.95 "cd /home/zthob-backend && git log -1"
   ```

2. **Check if service restarted:**
   ```bash
   ssh root@69.62.126.95 "systemctl status gunicorn"
   ```

3. **Check VERSION file on server:**
   ```bash
   ssh root@69.62.126.95 "cat /home/zthob-backend/VERSION"
   ```

4. **Check API endpoint:**
   ```bash
   curl http://69.62.126.95/api/config/version/
   ```

### Version Endpoint Returns 404

If `/api/config/version/` returns 404:

1. Check if `apps.core` is in INSTALLED_APPS
2. Check if URL is in `apps/core/urls.py`
3. Check if service restarted after code update

### Version Shows "unknown"

If version shows "unknown":

1. Check if VERSION file exists on server
2. Check file permissions
3. Check if version.py can read the file

## Best Practices

1. **Always check version after deployment**
   ```bash
   curl http://your-domain.com/api/config/version/
   ```

2. **Use version in API responses** (optional)
   - Can add version header to all responses
   - Helps with debugging client issues

3. **Tag releases with version**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

4. **Document version changes**
   - Keep CHANGELOG.md
   - Note what changed in each version

## Integration with Frontend

Frontend can check version:

```javascript
// Check if update is available
fetch('/api/config/version/')
  .then(res => res.json())
  .then(data => {
    const serverVersion = data.data.version;
    const clientVersion = '1.0.0'; // From package.json
    
    if (serverVersion !== clientVersion) {
      console.log('Server has new version:', serverVersion);
      // Show update notification
    }
  });
```

## Example Workflow

```bash
# 1. Make changes
git add .
git commit -m "Add new feature"

# 2. Push (triggers deployment)
git push origin main

# 3. Wait for deployment

# 4. Verify version
curl http://69.62.126.95/api/config/version/

# 5. Check GitHub Actions for verification result
```

## Summary

✅ **Automatic version bumping** on deployment  
✅ **Version verification** after deployment  
✅ **Public version endpoint** for checking  
✅ **Git commit info** included  
✅ **Deployment verification** built-in  

This ensures you can always verify if your code was actually deployed!

