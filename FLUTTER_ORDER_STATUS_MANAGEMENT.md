# Flutter Order Status Management Guide

## Overview
This guide explains how to manage order status transitions in Flutter, ensuring proper flow validation and checking what the next allowed statuses are.

---

## 1. Order Status Models

### Create Order Status Enums

```dart
// lib/models/order_status.dart

enum OrderStatus {
  pending,
  confirmed,
  inProgress,
  readyForDelivery,
  delivered,
  cancelled;

  String get value {
    switch (this) {
      case OrderStatus.pending:
        return 'pending';
      case OrderStatus.confirmed:
        return 'confirmed';
      case OrderStatus.inProgress:
        return 'in_progress';
      case OrderStatus.readyForDelivery:
        return 'ready_for_delivery';
      case OrderStatus.delivered:
        return 'delivered';
      case OrderStatus.cancelled:
        return 'cancelled';
    }
  }

  static OrderStatus fromString(String value) {
    return OrderStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => OrderStatus.pending,
    );
  }
}

enum RiderStatus {
  none,
  accepted,
  onWayToPickup,
  pickedUp,
  onWayToDelivery,
  onWayToMeasurement,
  measurementTaken,
  delivered;

  String get value {
    switch (this) {
      case RiderStatus.none:
        return 'none';
      case RiderStatus.accepted:
        return 'accepted';
      case RiderStatus.onWayToPickup:
        return 'on_way_to_pickup';
      case RiderStatus.pickedUp:
        return 'picked_up';
      case RiderStatus.onWayToDelivery:
        return 'on_way_to_delivery';
      case RiderStatus.onWayToMeasurement:
        return 'on_way_to_measurement';
      case RiderStatus.measurementTaken:
        return 'measurement_taken';
      case RiderStatus.delivered:
        return 'delivered';
    }
  }

  static RiderStatus fromString(String value) {
    return RiderStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => RiderStatus.none,
    );
  }
}

enum TailorStatus {
  none,
  accepted,
  stitchingStarted,
  stitched;

  String get value {
    switch (this) {
      case TailorStatus.none:
        return 'none';
      case TailorStatus.accepted:
        return 'accepted';
      case TailorStatus.stitchingStarted:
        return 'stitching_started';
      case TailorStatus.stitched:
        return 'stitched';
    }
  }

  static TailorStatus fromString(String value) {
    return TailorStatus.values.firstWhere(
      (e) => e.value == value,
      orElse: () => TailorStatus.none,
    );
  }
}

enum OrderType {
  fabricOnly,
  fabricWithStitching;

  String get value {
    switch (this) {
      case OrderType.fabricOnly:
        return 'fabric_only';
      case OrderType.fabricWithStitching:
        return 'fabric_with_stitching';
    }
  }

  static OrderType fromString(String value) {
    return OrderType.values.firstWhere(
      (e) => e.value == value,
      orElse: () => OrderType.fabricOnly,
    );
  }
}
```

### Order Model

```dart
// lib/models/order.dart

class Order {
  final int id;
  final String orderNumber;
  final OrderType orderType;
  final OrderStatus status;
  final RiderStatus riderStatus;
  final TailorStatus tailorStatus;
  final String? notes;
  final DateTime createdAt;
  final DateTime? actualDeliveryDate;

  Order({
    required this.id,
    required this.orderNumber,
    required this.orderType,
    required this.status,
    required this.riderStatus,
    required this.tailorStatus,
    this.notes,
    required this.createdAt,
    this.actualDeliveryDate,
  });

  factory Order.fromJson(Map<String, dynamic> json) {
    return Order(
      id: json['id'],
      orderNumber: json['order_number'] ?? '',
      orderType: OrderType.fromString(json['order_type'] ?? 'fabric_only'),
      status: OrderStatus.fromString(json['status'] ?? 'pending'),
      riderStatus: RiderStatus.fromString(json['rider_status'] ?? 'none'),
      tailorStatus: TailorStatus.fromString(json['tailor_status'] ?? 'none'),
      notes: json['notes'],
      createdAt: DateTime.parse(json['created_at']),
      actualDeliveryDate: json['actual_delivery_date'] != null
          ? DateTime.parse(json['actual_delivery_date'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'order_number': orderNumber,
      'order_type': orderType.value,
      'status': status.value,
      'rider_status': riderStatus.value,
      'tailor_status': tailorStatus.value,
      'notes': notes,
      'created_at': createdAt.toIso8601String(),
      'actual_delivery_date': actualDeliveryDate?.toIso8601String(),
    };
  }
}
```

---

## 2. Status Transition Service (Client-Side)

### Create Status Transition Validator

```dart
// lib/services/order_status_service.dart

import 'package:flutter/foundation.dart';
import '../models/order_status.dart';
import '../models/order.dart';

class OrderStatusService {
  /// Get next allowed statuses based on current order state and user role
  static Map<String, List<String>> getNextAllowedStatuses(
    Order order,
    String userRole, // 'TAILOR', 'RIDER', 'USER', 'ADMIN'
  ) {
    // Check if order is in final state
    if (order.status == OrderStatus.delivered ||
        order.status == OrderStatus.cancelled) {
      return {
        'status': [],
        'rider_status': [],
        'tailor_status': [],
      };
    }

    if (order.orderType == OrderType.fabricOnly) {
      return _getFabricOnlyTransitions(order, userRole);
    } else {
      return _getFabricWithStitchingTransitions(order, userRole);
    }
  }

  /// Get transitions for fabric_only orders
  static Map<String, List<String>> _getFabricOnlyTransitions(
    Order order,
    String userRole,
  ) {
    final transitions = <String, List<String>>{
      'status': [],
      'rider_status': [],
      'tailor_status': [],
    };

    if (userRole == 'ADMIN') {
      transitions['status'] = [
        'confirmed',
        'in_progress',
        'ready_for_delivery',
        'delivered',
        'cancelled'
      ];
      transitions['rider_status'] = [
        'accepted',
        'on_way_to_pickup',
        'picked_up',
        'on_way_to_delivery',
        'delivered'
      ];
      transitions['tailor_status'] = ['accepted'];
    } else if (userRole == 'TAILOR') {
      if (order.status == OrderStatus.pending) {
        transitions['status'] = ['confirmed'];
        transitions['tailor_status'] = ['accepted'];
      } else if (order.status == OrderStatus.confirmed) {
        transitions['status'] = ['in_progress'];
      } else if (order.status == OrderStatus.inProgress) {
        transitions['status'] = ['ready_for_delivery'];
      }
    } else if (userRole == 'RIDER') {
      if (order.status == OrderStatus.confirmed &&
          order.riderStatus == RiderStatus.none) {
        transitions['rider_status'] = ['accepted'];
      } else if (order.riderStatus == RiderStatus.accepted) {
        transitions['rider_status'] = ['on_way_to_pickup'];
      } else if (order.riderStatus == RiderStatus.onWayToPickup) {
        transitions['rider_status'] = ['picked_up'];
      } else if (order.riderStatus == RiderStatus.pickedUp) {
        transitions['rider_status'] = ['on_way_to_delivery'];
      } else if (order.riderStatus == RiderStatus.onWayToDelivery) {
        transitions['rider_status'] = ['delivered'];
        transitions['status'] = ['delivered'];
      }
    } else if (userRole == 'USER') {
      if (order.status == OrderStatus.pending) {
        transitions['status'] = ['cancelled'];
      }
    }

    return transitions;
  }

  /// Get transitions for fabric_with_stitching orders
  static Map<String, List<String>> _getFabricWithStitchingTransitions(
    Order order,
    String userRole,
  ) {
    final transitions = <String, List<String>>{
      'status': [],
      'rider_status': [],
      'tailor_status': [],
    };

    if (userRole == 'ADMIN') {
      transitions['status'] = [
        'confirmed',
        'in_progress',
        'ready_for_delivery',
        'delivered',
        'cancelled'
      ];
      transitions['rider_status'] = [
        'accepted',
        'on_way_to_measurement',
        'measurement_taken',
        'on_way_to_pickup',
        'picked_up',
        'on_way_to_delivery',
        'delivered'
      ];
      transitions['tailor_status'] = [
        'accepted',
        'stitching_started',
        'stitched'
      ];
    } else if (userRole == 'TAILOR') {
      if (order.status == OrderStatus.pending) {
        transitions['status'] = ['confirmed'];
        transitions['tailor_status'] = ['accepted'];
      } else if (order.status == OrderStatus.confirmed) {
        transitions['status'] = ['in_progress'];
      } else if (order.status == OrderStatus.inProgress) {
        if (order.riderStatus == RiderStatus.measurementTaken &&
            order.tailorStatus == TailorStatus.accepted) {
          transitions['tailor_status'] = ['stitching_started'];
        } else if (order.tailorStatus == TailorStatus.stitchingStarted) {
          transitions['tailor_status'] = ['stitched'];
        } else if (order.tailorStatus == TailorStatus.stitched) {
          transitions['status'] = ['ready_for_delivery'];
        }
      }
    } else if (userRole == 'RIDER') {
      if (order.status == OrderStatus.confirmed &&
          order.riderStatus == RiderStatus.none) {
        transitions['rider_status'] = ['accepted'];
      } else if (order.riderStatus == RiderStatus.accepted) {
        transitions['rider_status'] = ['on_way_to_measurement'];
      } else if (order.riderStatus == RiderStatus.onWayToMeasurement) {
        transitions['rider_status'] = ['measurement_taken'];
      } else if (order.riderStatus == RiderStatus.measurementTaken) {
        // Wait for tailor to stitch
        if (order.tailorStatus == TailorStatus.stitched) {
          transitions['rider_status'] = ['on_way_to_pickup'];
        }
      } else if (order.riderStatus == RiderStatus.onWayToPickup) {
        transitions['rider_status'] = ['picked_up'];
      } else if (order.riderStatus == RiderStatus.pickedUp) {
        transitions['rider_status'] = ['on_way_to_delivery'];
      } else if (order.riderStatus == RiderStatus.onWayToDelivery) {
        transitions['rider_status'] = ['delivered'];
        transitions['status'] = ['delivered'];
      }
    } else if (userRole == 'USER') {
      if (order.status == OrderStatus.pending) {
        transitions['status'] = ['cancelled'];
      }
    }

    return transitions;
  }

  /// Check if a status transition is allowed
  static bool canTransitionTo({
    required Order order,
    required String userRole,
    String? newStatus,
    String? newRiderStatus,
    String? newTailorStatus,
  }) {
    final allowed = getNextAllowedStatuses(order, userRole);

    if (newStatus != null && newStatus != order.status.value) {
      if (!allowed['status']!.contains(newStatus)) {
        return false;
      }
    }

    if (newRiderStatus != null && newRiderStatus != order.riderStatus.value) {
      if (!allowed['rider_status']!.contains(newRiderStatus)) {
        return false;
      }
    }

    if (newTailorStatus != null && newTailorStatus != order.tailorStatus.value) {
      if (!allowed['tailor_status']!.contains(newTailorStatus)) {
        return false;
      }
    }

    return true;
  }

  /// Get human-readable next actions
  static List<StatusAction> getNextActions(Order order, String userRole) {
    final allowed = getNextAllowedStatuses(order, userRole);
    final actions = <StatusAction>[];

    // Add status actions
    for (final status in allowed['status']!) {
      actions.add(StatusAction(
        type: 'status',
        value: status,
        label: _getStatusLabel(status),
        icon: _getStatusIcon(status),
      ));
    }

    // Add rider status actions
    for (final status in allowed['rider_status']!) {
      actions.add(StatusAction(
        type: 'rider_status',
        value: status,
        label: _getRiderStatusLabel(status),
        icon: _getRiderStatusIcon(status),
      ));
    }

    // Add tailor status actions
    for (final status in allowed['tailor_status']!) {
      actions.add(StatusAction(
        type: 'tailor_status',
        value: status,
        label: _getTailorStatusLabel(status),
        icon: _getTailorStatusIcon(status),
      ));
    }

    return actions;
  }

  static String _getStatusLabel(String status) {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'confirmed':
        return 'Confirm Order';
      case 'in_progress':
        return 'Mark In Progress';
      case 'ready_for_delivery':
        return 'Mark Ready for Delivery';
      case 'delivered':
        return 'Mark Delivered';
      case 'cancelled':
        return 'Cancel Order';
      default:
        return status;
    }
  }

  static String _getRiderStatusLabel(String status) {
    switch (status) {
      case 'accepted':
        return 'Accept Order';
      case 'on_way_to_pickup':
        return 'Start Pickup';
      case 'picked_up':
        return 'Mark Picked Up';
      case 'on_way_to_delivery':
        return 'Start Delivery';
      case 'on_way_to_measurement':
        return 'Start Measurement';
      case 'measurement_taken':
        return 'Complete Measurement';
      case 'delivered':
        return 'Mark Delivered';
      default:
        return status;
    }
  }

  static String _getTailorStatusLabel(String status) {
    switch (status) {
      case 'accepted':
        return 'Accept Order';
      case 'stitching_started':
        return 'Start Stitching';
      case 'stitched':
        return 'Finish Stitching';
      default:
        return status;
    }
  }

  static String _getStatusIcon(String status) {
    // Return icon names or emoji
    switch (status) {
      case 'confirmed':
        return '✓';
      case 'in_progress':
        return '⚙️';
      case 'ready_for_delivery':
        return '📦';
      case 'delivered':
        return '✅';
      case 'cancelled':
        return '❌';
      default:
        return '📋';
    }
  }

  static String _getRiderStatusIcon(String status) {
    switch (status) {
      case 'accepted':
        return '🤝';
      case 'on_way_to_pickup':
        return '🚗';
      case 'picked_up':
        return '📦';
      case 'on_way_to_delivery':
        return '🚚';
      case 'on_way_to_measurement':
        return '📏';
      case 'measurement_taken':
        return '✓';
      case 'delivered':
        return '✅';
      default:
        return '📋';
    }
  }

  static String _getTailorStatusIcon(String status) {
    switch (status) {
      case 'accepted':
        return '✓';
      case 'stitching_started':
        return '✂️';
      case 'stitched':
        return '✅';
      default:
        return '📋';
    }
  }
}

class StatusAction {
  final String type; // 'status', 'rider_status', 'tailor_status'
  final String value;
  final String label;
  final String icon;

  StatusAction({
    required this.type,
    required this.value,
    required this.label,
    required this.icon,
  });
}
```

---

## 3. API Service

```dart
// lib/services/api_service.dart

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/order.dart';

class ApiService {
  final String baseUrl;
  final String? token;

  ApiService({required this.baseUrl, this.token});

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  /// Update order status
  Future<Order> updateOrderStatus({
    required int orderId,
    String? status,
    String? riderStatus,
    String? tailorStatus,
    String? notes,
  }) async {
    final body = <String, dynamic>{};
    if (status != null) body['status'] = status;
    if (riderStatus != null) body['rider_status'] = riderStatus;
    if (tailorStatus != null) body['tailor_status'] = tailorStatus;
    if (notes != null) body['notes'] = notes;

    final response = await http.patch(
      Uri.parse('$baseUrl/api/orders/$orderId/status/'),
      headers: _headers,
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return Order.fromJson(data['data']);
    } else {
      final error = jsonDecode(response.body);
      throw Exception(error['message'] ?? 'Failed to update order status');
    }
  }

  /// Get order details
  Future<Order> getOrder(int orderId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/orders/$orderId/'),
      headers: _headers,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return Order.fromJson(data['data']);
    } else {
      throw Exception('Failed to load order');
    }
  }
}
```

---

## 4. UI Implementation

### Order Status Widget

```dart
// lib/widgets/order_status_widget.dart

import 'package:flutter/material.dart';
import '../models/order.dart';
import '../services/order_status_service.dart';

class OrderStatusWidget extends StatelessWidget {
  final Order order;
  final String userRole;
  final Function(String type, String value) onStatusUpdate;

  const OrderStatusWidget({
    Key? key,
    required this.order,
    required this.userRole,
    required this.onStatusUpdate,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final nextActions = OrderStatusService.getNextActions(order, userRole);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Current Status Display
        _buildCurrentStatus(),
        const SizedBox(height: 16),
        
        // Next Actions
        if (nextActions.isNotEmpty) ...[
          Text(
            'Next Actions',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: nextActions.map((action) {
              return ActionChip(
                avatar: Text(action.icon),
                label: Text(action.label),
                onPressed: () => _handleAction(context, action),
              );
            }).toList(),
          ),
        ] else
          Text(
            'No actions available',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.grey,
                ),
          ),
      ],
    );
  }

  Widget _buildCurrentStatus() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Current Status',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 4),
            Text(
              _getStatusDisplay(order),
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (order.riderStatus != RiderStatus.none) ...[
              const SizedBox(height: 8),
              Text(
                'Rider: ${_getRiderStatusDisplay(order.riderStatus)}',
                style: TextStyle(fontSize: 14, color: Colors.grey[700]),
              ),
            ],
            if (order.tailorStatus != TailorStatus.none) ...[
              const SizedBox(height: 4),
              Text(
                'Tailor: ${_getTailorStatusDisplay(order.tailorStatus)}',
                style: TextStyle(fontSize: 14, color: Colors.grey[700]),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _handleAction(BuildContext context, StatusAction action) {
    // Show confirmation dialog
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Confirm Action'),
        content: Text('Do you want to ${action.label.toLowerCase()}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              onStatusUpdate(action.type, action.value);
            },
            child: const Text('Confirm'),
          ),
        ],
      ),
    );
  }

  String _getStatusDisplay(Order order) {
    switch (order.status) {
      case OrderStatus.pending:
        return 'Pending';
      case OrderStatus.confirmed:
        return 'Confirmed';
      case OrderStatus.inProgress:
        return 'In Progress';
      case OrderStatus.readyForDelivery:
        return 'Ready for Delivery';
      case OrderStatus.delivered:
        return 'Delivered';
      case OrderStatus.cancelled:
        return 'Cancelled';
    }
  }

  String _getRiderStatusDisplay(RiderStatus status) {
    switch (status) {
      case RiderStatus.none:
        return 'Not Assigned';
      case RiderStatus.accepted:
        return 'Accepted';
      case RiderStatus.onWayToPickup:
        return 'On Way to Pickup';
      case RiderStatus.pickedUp:
        return 'Picked Up';
      case RiderStatus.onWayToDelivery:
        return 'On Way to Delivery';
      case RiderStatus.onWayToMeasurement:
        return 'On Way to Measurement';
      case RiderStatus.measurementTaken:
        return 'Measurement Taken';
      case RiderStatus.delivered:
        return 'Delivered';
    }
  }

  String _getTailorStatusDisplay(TailorStatus status) {
    switch (status) {
      case TailorStatus.none:
        return 'None';
      case TailorStatus.accepted:
        return 'Accepted';
      case TailorStatus.stitchingStarted:
        return 'Started Stitching';
      case TailorStatus.stitched:
        return 'Finished Stitching';
    }
  }
}
```

### Usage Example

```dart
// lib/screens/order_detail_screen.dart

import 'package:flutter/material.dart';
import '../models/order.dart';
import '../services/api_service.dart';
import '../services/order_status_service.dart';
import '../widgets/order_status_widget.dart';

class OrderDetailScreen extends StatefulWidget {
  final int orderId;
  final String userRole;
  final String token;

  const OrderDetailScreen({
    Key? key,
    required this.orderId,
    required this.userRole,
    required this.token,
  }) : super(key: key);

  @override
  State<OrderDetailScreen> createState() => _OrderDetailScreenState();
}

class _OrderDetailScreenState extends State<OrderDetailScreen> {
  late ApiService _apiService;
  Order? _order;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _apiService = ApiService(
      baseUrl: 'http://your-api-url.com',
      token: widget.token,
    );
    _loadOrder();
  }

  Future<void> _loadOrder() async {
    try {
      final order = await _apiService.getOrder(widget.orderId);
      setState(() {
        _order = order;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<void> _updateStatus(String type, String value) async {
    try {
      // Validate transition before API call
      if (!OrderStatusService.canTransitionTo(
        order: _order!,
        userRole: widget.userRole,
        newStatus: type == 'status' ? value : null,
        newRiderStatus: type == 'rider_status' ? value : null,
        newTailorStatus: type == 'tailor_status' ? value : null,
      )) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('This status transition is not allowed'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      // Show loading
      showDialog(
        context: context,
        barrierDismissible: false,
        builder: (context) => const Center(child: CircularProgressIndicator()),
      );

      // Update status
      final updatedOrder = await _apiService.updateOrderStatus(
        orderId: widget.orderId,
        status: type == 'status' ? value : null,
        riderStatus: type == 'rider_status' ? value : null,
        tailorStatus: type == 'tailor_status' ? value : null,
      );

      Navigator.pop(context); // Close loading dialog

      setState(() {
        _order = updatedOrder;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Status updated successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      Navigator.pop(context); // Close loading dialog
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_order == null) {
      return const Scaffold(
        body: Center(child: Text('Order not found')),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('Order #${_order!.orderNumber}'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            OrderStatusWidget(
              order: _order!,
              userRole: widget.userRole,
              onStatusUpdate: _updateStatus,
            ),
            // ... other order details
          ],
        ),
      ),
    );
  }
}
```

---

## 5. Key Points

### ✅ **Client-Side Validation**
- Always validate transitions before making API calls
- Show appropriate error messages if transition is invalid
- Prevent invalid actions from being displayed

### ✅ **User Experience**
- Show only available actions based on current status
- Display clear labels and icons for each action
- Provide confirmation dialogs for important actions
- Show loading states during API calls

### ✅ **Error Handling**
- Handle API errors gracefully
- Show user-friendly error messages
- Validate transitions on both client and server

### ✅ **Status Display**
- Show current status clearly
- Display rider and tailor activity statuses
- Use visual indicators (icons, colors) for better UX

---

## 6. Testing Status Transitions

```dart
// test/order_status_service_test.dart

import 'package:flutter_test/flutter_test.dart';
import 'package:your_app/models/order.dart';
import 'package:your_app/services/order_status_service.dart';

void main() {
  group('OrderStatusService', () {
    test('should allow tailor to accept pending order', () {
      final order = Order(
        id: 1,
        orderNumber: 'ORD-123',
        orderType: OrderType.fabricOnly,
        status: OrderStatus.pending,
        riderStatus: RiderStatus.none,
        tailorStatus: TailorStatus.none,
        createdAt: DateTime.now(),
      );

      final canTransition = OrderStatusService.canTransitionTo(
        order: order,
        userRole: 'TAILOR',
        newStatus: 'confirmed',
        newTailorStatus: 'accepted',
      );

      expect(canTransition, true);
    });

    test('should not allow rider to skip steps', () {
      final order = Order(
        id: 1,
        orderNumber: 'ORD-123',
        orderType: OrderType.fabricOnly,
        status: OrderStatus.confirmed,
        riderStatus: RiderStatus.accepted,
        tailorStatus: TailorStatus.none,
        createdAt: DateTime.now(),
      );

      // Try to skip to delivered
      final canTransition = OrderStatusService.canTransitionTo(
        order: order,
        userRole: 'RIDER',
        newRiderStatus: 'delivered',
      );

      expect(canTransition, false);
    });
  });
}
```

---

This implementation ensures proper order status management on the Flutter frontend with validation, clear UI, and proper error handling.



