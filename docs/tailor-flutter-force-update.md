# Tailor App — Force Update (Flutter)

Simple mobile version check for **customer**, **tailor**, and **rider** apps.

---

## API

```http
GET /api/config/mobile-version/?app=tailor&platform=android&version=1.0.27
```

| Param      | Values                    |
|-----------|---------------------------|
| `app`     | `customer`, `tailor`, `rider` |
| `platform`| `ios`, `android`          |
| `version` | Installed app version e.g. `1.0.27` |

No auth required. Flutter sends `PackageInfo.version` (not build number).

---

## Response (only 2 flags)

**Up to date**
```json
{
  "success": true,
  "data": {
    "soft_update": false,
    "force_update": false
  }
}
```

**Soft update (optional)**
```json
{
  "success": true,
  "data": {
    "soft_update": true,
    "force_update": false
  }
}
```

**Force update (blocking)**
```json
{
  "success": true,
  "data": {
    "soft_update": false,
    "force_update": true
  }
}
```

Store URL and messages are handled in the Flutter app (hardcoded).

---

## Admin control

**Django admin → Mobile App Version Policies**

Each row = one app + platform (6 rows total).

| Field | Purpose |
|-------|---------|
| `latest_version` | Store version e.g. `1.0.27` |
| `soft_update_enabled` | ON = optional update for users below latest |
| `force_update_enabled` | ON = block users below latest |
| `is_active` | OFF = no checks for this app/platform |

### Examples (tailor @ 1.0.27)

**No prompts**
- `latest_version` = `1.0.27`
- both toggles OFF

**Soft update** (new 1.0.28 in store, old apps still work)
- `latest_version` = `1.0.28`
- `soft_update_enabled` = ON
- `force_update_enabled` = OFF

**Force update** (block everyone below 1.0.28)
- `latest_version` = `1.0.28`
- `force_update_enabled` = ON

If both toggles ON, **force wins**.

---

## Flutter logic

```dart
if (data['force_update'] == true) {
  // blocking screen
} else if (data['soft_update'] == true) {
  // optional dialog with Later
} else {
  // continue
}
```

---

## Migrate

```bash
uv run python manage.py migrate core
```

---

## Test with curl

```bash
curl "https://prod.mgask.net/api/config/mobile-version/?app=tailor&platform=android&version=1.0.27"
```
