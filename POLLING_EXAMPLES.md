# Polling Examples for Delivery Tracking

## What is Polling?

**Polling** means repeatedly calling an API endpoint at regular intervals (like every 15 seconds) to get or send updated information, instead of using real-time connections like WebSockets.

In our delivery tracking system:
- **Rider app** polls to **SEND** location updates every 15 seconds
- **Customer app** polls to **GET** location updates every 15 seconds

---

## Rider App - Polling to Send Location Updates

The rider's mobile app should continuously send their GPS location every 15 seconds while delivering an order.

### JavaScript/React Native Example

```javascript
import { useEffect, useRef } from 'react';
import Geolocation from '@react-native-community/geolocation';

function RiderDeliveryTracking({ orderId, isActive }) {
  const intervalRef = useRef(null);
  const watchIdRef = useRef(null);

  useEffect(() => {
    if (!isActive || !orderId) return;

    // Start watching GPS location
    watchIdRef.current = Geolocation.watchPosition(
      (position) => {
        const { latitude, longitude, accuracy, speed, heading } = position.coords;
        
        // Send location update to API
        updateLocation(orderId, {
          latitude,
          longitude,
          accuracy,
          speed: speed ? speed * 3.6 : null, // Convert m/s to km/h
          heading,
        });
      },
      (error) => {
        console.error('GPS Error:', error);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );

    // Also poll every 15 seconds as backup
    intervalRef.current = setInterval(() => {
      Geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude, accuracy, speed, heading } = position.coords;
          updateLocation(orderId, {
            latitude,
            longitude,
            accuracy,
            speed: speed ? speed * 3.6 : null,
            heading,
          });
        },
        (error) => console.error('GPS Error:', error),
        { enableHighAccuracy: true }
      );
    }, 15000); // Every 15 seconds

    // Cleanup
    return () => {
      if (watchIdRef.current) {
        Geolocation.clearWatch(watchIdRef.current);
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [orderId, isActive]);

  const updateLocation = async (orderId, locationData) => {
    try {
      const response = await fetch(
        `https://your-api.com/api/deliveries/rider/orders/${orderId}/update-location/`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${yourAuthToken}`,
          },
          body: JSON.stringify(locationData),
        }
      );

      const data = await response.json();
      if (data.success) {
        console.log('Location updated:', data.data.distance_from_previous_km, 'km');
      }
    } catch (error) {
      console.error('Failed to update location:', error);
    }
  };

  return null; // This is a background service component
}
```

### Swift (iOS) Example

```swift
import CoreLocation

class RiderLocationTracker: NSObject, CLLocationManagerDelegate {
    var locationManager: CLLocationManager
    var orderId: Int
    var updateTimer: Timer?
    
    init(orderId: Int) {
        self.orderId = orderId
        self.locationManager = CLLocationManager()
        super.init()
        setupLocationManager()
    }
    
    func setupLocationManager() {
        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyBest
        locationManager.requestWhenInUseAuthorization()
    }
    
    func startTracking() {
        locationManager.startUpdatingLocation()
        
        // Poll every 15 seconds
        updateTimer = Timer.scheduledTimer(withTimeInterval: 15.0, repeats: true) { [weak self] _ in
            self?.sendLocationUpdate()
        }
    }
    
    func stopTracking() {
        locationManager.stopUpdatingLocation()
        updateTimer?.invalidate()
    }
    
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        sendLocationUpdate(location: location)
    }
    
    func sendLocationUpdate(location: CLLocation? = nil) {
        let currentLocation = location ?? locationManager.location
        guard let loc = currentLocation else { return }
        
        let locationData: [String: Any] = [
            "latitude": loc.coordinate.latitude,
            "longitude": loc.coordinate.longitude,
            "accuracy": loc.horizontalAccuracy,
            "speed": loc.speed >= 0 ? loc.speed * 3.6 : nil, // Convert m/s to km/h
            "heading": loc.course >= 0 ? loc.course : nil,
        ]
        
        // Send to API
        updateLocationAPI(orderId: orderId, data: locationData)
    }
    
    func updateLocationAPI(orderId: Int, data: [String: Any]) {
        // API call implementation
        // POST to /api/deliveries/rider/orders/{orderId}/update-location/
    }
}
```

### Kotlin (Android) Example

```kotlin
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import java.util.Timer
import java.util.TimerTask

class RiderLocationTracker(
    private val context: Context,
    private val orderId: Int
) : LocationListener {
    
    private val locationManager: LocationManager = 
        context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    private var updateTimer: Timer? = null
    
    fun startTracking() {
        // Request location updates
        if (ActivityCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                5000, // 5 seconds
                5f, // 5 meters
                this
            )
        }
        
        // Also poll every 15 seconds
        updateTimer = Timer()
        updateTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                sendLocationUpdate()
            }
        }, 0, 15000) // Every 15 seconds
    }
    
    fun stopTracking() {
        locationManager.removeUpdates(this)
        updateTimer?.cancel()
    }
    
    override fun onLocationChanged(location: Location) {
        sendLocationUpdate(location)
    }
    
    private fun sendLocationUpdate(location: Location? = null) {
        val currentLocation = location ?: locationManager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
        currentLocation?.let { loc ->
            val locationData = mapOf(
                "latitude" to loc.latitude,
                "longitude" to loc.longitude,
                "accuracy" to loc.accuracy,
                "speed" to (loc.speed * 3.6).takeIf { it >= 0 }, // Convert m/s to km/h
                "heading" to loc.bearing.takeIf { it >= 0 },
            )
            
            // Send to API
            updateLocationAPI(orderId, locationData)
        }
    }
    
    private fun updateLocationAPI(orderId: Int, data: Map<String, Any?>) {
        // API call implementation
        // POST to /api/deliveries/rider/orders/{orderId}/update-location/
    }
}
```

---

## Customer App - Polling to Get Location Updates

The customer's mobile app should continuously fetch the latest rider location every 15 seconds.

### JavaScript/React Native Example

```javascript
import { useEffect, useState, useRef } from 'react';

function CustomerOrderTracking({ orderId }) {
  const [trackingData, setTrackingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef(null);

  useEffect(() => {
    // Fetch immediately
    fetchTracking();

    // Then poll every 15 seconds
    intervalRef.current = setInterval(() => {
      fetchTracking();
    }, 15000); // Every 15 seconds

    // Cleanup
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [orderId]);

  const fetchTracking = async () => {
    try {
      const response = await fetch(
        `https://your-api.com/api/deliveries/customer/orders/${orderId}/tracking/`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${yourAuthToken}`,
          },
        }
      );

      const data = await response.json();
      if (data.success) {
        setTrackingData(data.data);
        setLoading(false);
        
        // Update map with new location
        updateMap(data.data.current_location, data.data.recent_route);
      }
    } catch (error) {
      console.error('Failed to fetch tracking:', error);
    }
  };

  const updateMap = (currentLocation, route) => {
    if (currentLocation) {
      // Update map marker to show rider's current location
      // Draw route line using route array
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <View>
      <MapView
        currentLocation={trackingData?.current_location}
        route={trackingData?.recent_route}
      />
      <TrackingInfo
        riderName={trackingData?.rider_name}
        status={trackingData?.current_status}
        estimatedTime={trackingData?.estimated_time_minutes}
        estimatedDistance={trackingData?.estimated_distance_km}
      />
    </View>
  );
}
```

### Swift (iOS) Example

```swift
class CustomerTrackingService {
    var orderId: Int
    var updateTimer: Timer?
    var onUpdate: ((TrackingData) -> Void)?
    
    init(orderId: Int) {
        self.orderId = orderId
    }
    
    func startTracking(onUpdate: @escaping (TrackingData) -> Void) {
        self.onUpdate = onUpdate
        
        // Fetch immediately
        fetchTracking()
        
        // Then poll every 15 seconds
        updateTimer = Timer.scheduledTimer(withTimeInterval: 15.0, repeats: true) { [weak self] _ in
            self?.fetchTracking()
        }
    }
    
    func stopTracking() {
        updateTimer?.invalidate()
    }
    
    func fetchTracking() {
        // API call to GET /api/deliveries/customer/orders/{orderId}/tracking/
        // On success, call onUpdate?(trackingData)
    }
}
```

### Kotlin (Android) Example

```kotlin
class CustomerTrackingService(private val orderId: Int) {
    private var updateTimer: Timer? = null
    var onUpdate: ((TrackingData) -> Unit)? = null
    
    fun startTracking() {
        // Fetch immediately
        fetchTracking()
        
        // Then poll every 15 seconds
        updateTimer = Timer()
        updateTimer?.scheduleAtFixedRate(object : TimerTask() {
            override fun run() {
                fetchTracking()
            }
        }, 0, 15000) // Every 15 seconds
    }
    
    fun stopTracking() {
        updateTimer?.cancel()
    }
    
    private fun fetchTracking() {
        // API call to GET /api/deliveries/customer/orders/{orderId}/tracking/
        // On success, call onUpdate?.invoke(trackingData)
    }
}
```

---

## Why Polling Instead of WebSockets?

We chose polling because:

1. **Simplicity**: Easier to implement and maintain
2. **Mobile-friendly**: Works well with mobile apps that may go to background
3. **Battery efficient**: Can be optimized to poll less frequently when needed
4. **No server overhead**: No need for WebSocket connection management
5. **Your requirement**: You specifically asked for API-based approach

### When to Poll

- **Rider**: Poll every 15 seconds while order status is active (not delivered/cancelled)
- **Customer**: Poll every 15 seconds while order is being delivered
- **Stop polling**: When order is delivered or cancelled

### Battery Optimization Tips

1. **Reduce frequency when stationary**: If rider hasn't moved much, poll less frequently
2. **Stop when app is backgrounded**: Pause polling when app goes to background
3. **Use location services efficiently**: Use appropriate accuracy levels

---

## Summary

- **Polling** = Repeatedly calling API every 15 seconds
- **Rider app**: Sends location updates (POST)
- **Customer app**: Gets location updates (GET)
- **Simple and effective** for mobile apps
- **No WebSockets needed** - just regular HTTP requests

