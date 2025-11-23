# Tailor Analytics API - cURL Examples for Live Server

## Server Information
Based on your configuration:
- **Domain**: `mgask.net` (or `http://mgask.net`)
- **IP Address**: `69.62.126.95` (or `http://69.62.126.95`)

**Note**: Replace `YOUR_ACCESS_TOKEN` with your actual JWT token obtained from `/api/accounts/login/`

---

## 1. Basic Analytics Request (Default: 30 days, 12 weeks)

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using HTTPS (if configured)
```bash
curl -X GET "https://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 2. Custom Time Periods (60 days, 24 weeks)

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/?days=60&weeks=24" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/?days=60&weeks=24" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 3. Last 7 Days Only

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/?days=7&weeks=4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/?days=7&weeks=4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 4. Full Year Data (365 days, 52 weeks)

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/?days=365&weeks=52" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/?days=365&weeks=52" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 5. Last 90 Days with 12 Weeks Trends

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/?days=90&weeks=12" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/?days=90&weeks=12" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 6. Pretty Print JSON Response

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" | python -m json.tool
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" | python -m json.tool
```

---

## 7. Save Response to File

### Using Domain
```bash
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -o analytics_response.json
```

### Using IP Address
```bash
curl -X GET "http://69.62.126.95/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -o analytics_response.json
```

---

## 8. Using Environment Variable (Bash Script)

Create a script `get_analytics.sh`:

```bash
#!/bin/bash

# Configuration
BASE_URL="http://mgask.net"  # or "http://69.62.126.95"
ACCESS_TOKEN="YOUR_ACCESS_TOKEN"
DAYS=${1:-30}  # Default to 30 days if not provided
WEEKS=${2:-12}  # Default to 12 weeks if not provided

# Make the request
curl -X GET "${BASE_URL}/api/tailors/analytics/?days=${DAYS}&weeks=${WEEKS}" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" | python -m json.tool
```

Usage:
```bash
chmod +x get_analytics.sh
./get_analytics.sh          # Uses defaults (30 days, 12 weeks)
./get_analytics.sh 60 24    # Custom: 60 days, 24 weeks
```

---

## 9. Complete Example with Login Flow

```bash
#!/bin/bash

BASE_URL="http://mgask.net"  # or "http://69.62.126.95"
TAILOR_USERNAME="your_tailor_username"
TAILOR_PASSWORD="your_tailor_password"

# Step 1: Login and get token
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/accounts/login/" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"${TAILOR_USERNAME}\",
    \"password\": \"${TAILOR_PASSWORD}\"
  }")

# Extract access token (adjust based on your response format)
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "Token obtained: ${ACCESS_TOKEN:0:20}..."

# Step 2: Get analytics
echo "Fetching analytics..."
curl -X GET "${BASE_URL}/api/tailors/analytics/?days=30&weeks=12" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json" | python -m json.tool
```

---

## 10. Using Postman/Insomnia Collection

### Base URL
```
http://mgask.net
```
or
```
http://69.62.126.95
```

### Endpoint
```
GET /api/tailors/analytics/
```

### Headers
```
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json
```

### Query Parameters
- `days` (optional): 1-365, default: 30
- `weeks` (optional): 1-52, default: 12

---

## Expected Response Format

```json
{
  "success": true,
  "message": "Analytics data retrieved successfully",
  "data": {
    "total_revenue": "5000.00",
    "formatted_total_revenue": "5000.00",
    "completed_orders_count": 25,
    "total_orders_count": 30,
    "completion_percentage": 83.33,
    "formatted_completion_percentage": "83.33%",
    "daily_earnings": [
      {
        "date": "2024-01-01",
        "earnings": "150.00",
        "formatted_earnings": "150.00"
      }
    ],
    "weekly_trends": [
      {
        "week_start": "2024-01-01",
        "week_end": "2024-01-07",
        "week_label": "Jan 01 - Jan 07, 2024",
        "orders_created": 5,
        "orders_completed": 4,
        "revenue": "500.00",
        "formatted_revenue": "500.00"
      }
    ],
    "analytics_period": {
      "daily_earnings_days": 30,
      "weekly_trends_weeks": 12,
      "generated_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

## Troubleshooting

### 401 Unauthorized
```bash
# Make sure you have a valid token
curl -X POST "http://mgask.net/api/accounts/login/" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

### 403 Forbidden
- Ensure the user has `TAILOR` role
- Check user permissions in Django admin

### Connection Refused
- Verify server is running
- Check firewall settings
- Try IP address instead of domain or vice versa

### SSL/HTTPS Issues
If using HTTPS:
```bash
curl -k -X GET "https://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

---

## Quick Test Command

Replace `YOUR_ACCESS_TOKEN` and run:

```bash
curl -X GET "http://mgask.net/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" | python -m json.tool
```

---

## Notes

1. **Authentication**: All requests require a valid JWT token
2. **Role**: User must have `TAILOR` role
3. **Performance**: Larger date ranges may take longer to process
4. **Rate Limiting**: Be mindful of API rate limits if configured
5. **HTTPS**: If your server uses HTTPS, replace `http://` with `https://`


