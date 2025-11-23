# Test Cases for Measurement Security Fix

This document provides test cases to verify that the security fix prevents riders from bypassing the measurements endpoint.

## Test Scenario

**Issue:** Riders could set `rider_status: "measurement_taken"` via `/update-status/` endpoint without actually adding measurements.

**Fix:** Added validation to require measurements to be added via `/measurements/` endpoint before allowing `measurement_taken` status.

---

## Automated Tests

### Run Django Test Suite

```bash
# Run the test file
python manage.py test test_measurement_security_fix

# Or run with verbose output
python manage.py test test_measurement_security_fix -v 2
```

### Expected Results

All 5 test cases should pass:
1. ✅ `test_cannot_set_measurement_taken_without_measurements` - Should fail with 400
2. ✅ `test_can_set_measurement_taken_after_adding_measurements` - Should succeed
3. ✅ `test_fabric_only_order_not_affected` - Should succeed (fabric_only doesn't need measurements)
4. ✅ `test_validation_only_applies_to_fabric_with_stitching` - Should fail with 400
5. ✅ `test_validation_checks_both_measurements_and_timestamp` - Should fail with 400

---

## Manual Testing with cURL

### Prerequisites

1. Create a `fabric_with_stitching` order
2. Assign a rider to the order
3. Get rider authentication token

### Test Case 1: Try to Bypass Measurements (Should FAIL)

**This should fail with error message:**

```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/{order_id}/update-status/' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
    "rider_status": "measurement_taken",
    "notes": "Trying to bypass measurements"
}'
```

**Expected Response (400 Bad Request):**
```json
{
    "success": false,
    "message": "Cannot mark measurements as taken without adding measurements",
    "data": null,
    "errors": null
}
```

### Test Case 2: Proper Flow (Should SUCCEED)

**Step 1: Update status to on_way_to_measurement**
```bash
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/{order_id}/update-status/' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
    "rider_status": "on_way_to_measurement",
    "notes": "On my way to take measurements"
}'
```

**Step 2: Add measurements via proper endpoint**
```bash
curl --location --request POST 'http://localhost:8000/api/riders/orders/{order_id}/measurements/' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
    "measurements": {
        "chest": "40",
        "waist": "36",
        "shoulder": "18",
        "sleeve_length": "24",
        "length": "42"
    },
    "notes": "Measurements taken successfully"
}'
```

**Expected Response (200 OK):**
```json
{
    "success": true,
    "message": "Measurements added successfully. Tailor can now proceed with cutting.",
    "data": {
        "id": 123,
        "rider_status": "measurement_taken",
        "rider_measurements": {
            "chest": "40",
            "waist": "36",
            "shoulder": "18",
            "sleeve_length": "24",
            "length": "42"
        },
        "measurement_taken_at": "2024-12-18T11:30:00Z"
    }
}
```

**Step 3: Now try to update status (should work if measurements exist)**
```bash
# This should work now because measurements are already added
# But actually, the /measurements/ endpoint already sets status to measurement_taken
# So this step is just to verify the order state
curl --location 'http://localhost:8000/api/riders/orders/{order_id}/' \
--header 'Authorization: Bearer RIDER_TOKEN'
```

### Test Case 3: Fabric Only Order (Should NOT be affected)

**For `fabric_only` orders, the validation should NOT apply:**

```bash
# Create a fabric_only order and try normal status updates
curl --location --request PATCH 'http://localhost:8000/api/riders/orders/{fabric_only_order_id}/update-status/' \
--header 'Authorization: Bearer RIDER_TOKEN' \
--header 'Content-Type: application/json' \
--data '{
    "rider_status": "on_way_to_pickup",
    "notes": "On way to pickup"
}'
```

**Expected:** Should succeed (fabric_only orders don't need measurements)

---

## Testing Checklist

- [ ] **Test 1:** Try to set `measurement_taken` without measurements → Should FAIL (400)
- [ ] **Test 2:** Add measurements via `/measurements/` endpoint → Should SUCCEED (200)
- [ ] **Test 3:** Verify measurements are stored in `rider_measurements` field
- [ ] **Test 4:** Verify `measurement_taken_at` timestamp is set
- [ ] **Test 5:** Verify `fabric_only` orders are not affected
- [ ] **Test 6:** Verify error message is clear and helpful

---

## Admin Panel Testing

### Steps to Test in Admin Panel

1. **Login to Admin:** `http://localhost:8000/admin`
2. **Navigate to Orders:** Find a `fabric_with_stitching` order
3. **Check Order State:**
   - Order should have `rider_status: "on_way_to_measurement"` or `"accepted"`
   - `rider_measurements` should be empty/null
   - `measurement_taken_at` should be empty/null

4. **Try to Manually Set Status:**
   - Try to change `rider_status` to `measurement_taken` via admin
   - This should work in admin (admin has full control), but verify the API blocks it

5. **Verify via API:**
   - Use the cURL commands above to verify API validation works

---

## Edge Cases to Test

1. **Empty measurements object:** `rider_measurements: {}` → Should fail
2. **Missing timestamp:** `rider_measurements` exists but `measurement_taken_at` is null → Should fail
3. **Missing measurements:** `measurement_taken_at` exists but `rider_measurements` is null → Should fail
4. **Both missing:** Both null → Should fail
5. **Both present:** Both exist → Should succeed (via /measurements/ endpoint)

---

## Verification Points

After running tests, verify:

1. ✅ API returns 400 error when trying to bypass
2. ✅ Error message is clear: "Cannot mark measurements as taken without adding measurements"
3. ✅ `/measurements/` endpoint still works correctly
4. ✅ Measurements are properly stored
5. ✅ `fabric_only` orders are not affected
6. ✅ Normal flow (on_way_to_measurement → measurements → measurement_taken) works

---

## Quick Test Script

Save this as `quick_test.sh`:

```bash
#!/bin/bash

# Set your values
BASE_URL="http://localhost:8000"
RIDER_TOKEN="YOUR_RIDER_TOKEN"
ORDER_ID="YOUR_ORDER_ID"

echo "Test 1: Try to bypass measurements (should fail)"
curl -X PATCH "${BASE_URL}/api/riders/orders/${ORDER_ID}/update-status/" \
  -H "Authorization: Bearer ${RIDER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "rider_status": "measurement_taken",
    "notes": "Trying to bypass"
  }'

echo -e "\n\nTest 2: Add measurements properly (should succeed)"
curl -X POST "${BASE_URL}/api/riders/orders/${ORDER_ID}/measurements/" \
  -H "Authorization: Bearer ${RIDER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "measurements": {
      "chest": "40",
      "waist": "36",
      "shoulder": "18",
      "sleeve_length": "24",
      "length": "42"
    },
    "notes": "Measurements taken"
  }'
```

Make it executable and run:
```bash
chmod +x quick_test.sh
./quick_test.sh
```

---

## Expected Behavior Summary

| Action | Order Type | Has Measurements? | Expected Result |
|--------|-----------|------------------|-----------------|
| Set `measurement_taken` | `fabric_with_stitching` | No | ❌ FAIL (400) |
| Set `measurement_taken` | `fabric_with_stitching` | Yes | ✅ SUCCEED (via /measurements/) |
| Set `on_way_to_pickup` | `fabric_only` | N/A | ✅ SUCCEED |
| Add measurements | `fabric_with_stitching` | N/A | ✅ SUCCEED (200) |

---

**Last Updated:** 2024-12-18  
**Version:** 1.0




