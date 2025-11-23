# Tailor Analytics API Documentation

## Overview
The Tailor Analytics API provides comprehensive analytics and insights for tailors, including revenue tracking, order completion statistics, daily earnings breakdown, and weekly order trends.

## Endpoint

### Get Tailor Analytics
**GET** `/api/tailors/analytics/`

Returns comprehensive analytics data for the authenticated tailor.

#### Authentication
- **Required**: Yes
- **Role**: TAILOR only

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days for daily earnings breakdown (1-365) |
| `weeks` | integer | 12 | Number of weeks for weekly trends (1-52) |

#### Response Structure

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
      },
      {
        "date": "2024-01-02",
        "earnings": "0.00",
        "formatted_earnings": "0.00"
      }
      // ... more days
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
      // ... more weeks
    ],
    "analytics_period": {
      "daily_earnings_days": 30,
      "weekly_trends_weeks": 12,
      "generated_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

#### Response Fields

**Summary Metrics:**
- `total_revenue`: Total revenue from all delivered orders (string, decimal)
- `formatted_total_revenue`: Formatted revenue string
- `completed_orders_count`: Number of delivered orders
- `total_orders_count`: Total number of orders (excluding cancelled)
- `completion_percentage`: Percentage of completed orders (float)
- `formatted_completion_percentage`: Formatted percentage string

**Daily Earnings:**
- Array of daily earnings for the specified period
- Each entry contains:
  - `date`: Date in ISO format (YYYY-MM-DD)
  - `earnings`: Earnings for that day (string, decimal)
  - `formatted_earnings`: Formatted earnings string

**Weekly Trends:**
- Array of weekly order trends
- Each entry contains:
  - `week_start`: Start date of the week (ISO format)
  - `week_end`: End date of the week (ISO format)
  - `week_label`: Human-readable week label
  - `orders_created`: Number of orders created that week
  - `orders_completed`: Number of orders completed that week
  - `revenue`: Revenue from completed orders that week (string, decimal)
  - `formatted_revenue`: Formatted revenue string

## cURL Examples

### Basic Request (Default Parameters)
```bash
curl -X GET "http://localhost:8000/api/tailors/analytics/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Custom Time Periods
```bash
# Get last 60 days of daily earnings and 24 weeks of trends
curl -X GET "http://localhost:8000/api/tailors/analytics/?days=60&weeks=24" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Using Basic Authentication
```bash
curl -X GET "http://localhost:8000/api/tailors/analytics/" \
  -u "tailor_username:password" \
  -H "Content-Type: application/json"
```

### Get Last 7 Days Only
```bash
curl -X GET "http://localhost:8000/api/tailors/analytics/?days=7&weeks=4" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### Get Full Year Data
```bash
curl -X GET "http://localhost:8000/api/tailors/analytics/?days=365&weeks=52" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden (Not a Tailor)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 400 Bad Request (Invalid Parameters)
```json
{
  "success": false,
  "message": "Days parameter must be between 1 and 365"
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Error retrieving analytics: [error details]"
}
```

## Notes

1. **Revenue Calculation**: Only includes orders with status `delivered`
2. **Order Counting**: Cancelled orders are excluded from total count
3. **Daily Earnings**: Based on `actual_delivery_date` if available, otherwise uses `created_at`
4. **Weekly Trends**: Orders are grouped by the Monday of the week they were created
5. **Performance**: For large date ranges, the API may take longer to respond. Consider using reasonable limits.

## Admin Dashboard Integration

The analytics are also available in the Django Admin dashboard:
- Navigate to **Tailors > Tailor Profiles**
- Click on any tailor profile
- Scroll to the **Analytics Summary** section
- View revenue, orders, and completion statistics

The admin dashboard also displays:
- Total revenue in the list view
- Completed/Total orders ratio in the list view
- Detailed analytics summary in the detail view

## Testing

Run the test suite:
```bash
python manage.py test apps.tailors.tests_analytics
```

Test coverage includes:
- Revenue calculation accuracy
- Order counting (completed vs total)
- Completion percentage calculation
- Daily earnings breakdown
- Weekly trends analysis
- API endpoint authentication and authorization
- Parameter validation

