import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class AdminAnalyticsOverview {
  const AdminAnalyticsOverview({
    required this.activeProperties,
    required this.availableUnits,
    required this.occupiedUnits,
    required this.vacatingSoonUnits,
    required this.activeTenancies,
    required this.pendingLandlordVerifications,
    required this.pendingPropertyReviews,
    required this.pendingBookingPaymentReviews,
    required this.pendingAdvertPaymentReviews,
    required this.openViewingRequests,
    required this.confirmedBookingsThisMonth,
    required this.bookingFundsConfirmed,
    required this.advertRevenueConfirmed,
    required this.savedHomes,
    required this.conversations,
    required this.messages,
  });

  factory AdminAnalyticsOverview.fromJson(Map<String, dynamic> json) => AdminAnalyticsOverview(
        activeProperties: (json['active_properties'] as num?)?.toInt() ?? 0,
        availableUnits: (json['available_units'] as num?)?.toInt() ?? 0,
        occupiedUnits: (json['occupied_units'] as num?)?.toInt() ?? 0,
        vacatingSoonUnits: (json['vacating_soon_units'] as num?)?.toInt() ?? 0,
        activeTenancies: (json['active_tenancies'] as num?)?.toInt() ?? 0,
        pendingLandlordVerifications:
            (json['pending_landlord_verifications'] as num?)?.toInt() ?? 0,
        pendingPropertyReviews: (json['pending_property_reviews'] as num?)?.toInt() ?? 0,
        pendingBookingPaymentReviews:
            (json['pending_booking_payment_reviews'] as num?)?.toInt() ?? 0,
        pendingAdvertPaymentReviews:
            (json['pending_advert_payment_reviews'] as num?)?.toInt() ?? 0,
        openViewingRequests: (json['open_viewing_requests'] as num?)?.toInt() ?? 0,
        confirmedBookingsThisMonth:
            (json['confirmed_bookings_this_month'] as num?)?.toInt() ?? 0,
        bookingFundsConfirmed:
            double.tryParse(json['booking_funds_confirmed'].toString()) ?? 0,
        advertRevenueConfirmed:
            double.tryParse(json['advert_revenue_confirmed'].toString()) ?? 0,
        savedHomes: (json['saved_homes'] as num?)?.toInt() ?? 0,
        conversations: (json['conversations'] as num?)?.toInt() ?? 0,
        messages: (json['messages'] as num?)?.toInt() ?? 0,
      );

  final int activeProperties;
  final int availableUnits;
  final int occupiedUnits;
  final int vacatingSoonUnits;
  final int activeTenancies;
  final int pendingLandlordVerifications;
  final int pendingPropertyReviews;
  final int pendingBookingPaymentReviews;
  final int pendingAdvertPaymentReviews;
  final int openViewingRequests;
  final int confirmedBookingsThisMonth;
  final double bookingFundsConfirmed;
  final double advertRevenueConfirmed;
  final int savedHomes;
  final int conversations;
  final int messages;
}

class LandlordAnalyticsOverview {
  const LandlordAnalyticsOverview({
    required this.properties,
    required this.activeProperties,
    required this.totalUnits,
    required this.availableUnits,
    required this.occupiedUnits,
    required this.vacatingSoonUnits,
    required this.activeTenancies,
    required this.pendingViewings,
    required this.confirmedBookings,
    required this.savedHomes,
    required this.conversations,
    required this.unreadMessages,
  });

  factory LandlordAnalyticsOverview.fromJson(Map<String, dynamic> json) =>
      LandlordAnalyticsOverview(
        properties: (json['properties'] as num?)?.toInt() ?? 0,
        activeProperties: (json['active_properties'] as num?)?.toInt() ?? 0,
        totalUnits: (json['total_units'] as num?)?.toInt() ?? 0,
        availableUnits: (json['available_units'] as num?)?.toInt() ?? 0,
        occupiedUnits: (json['occupied_units'] as num?)?.toInt() ?? 0,
        vacatingSoonUnits: (json['vacating_soon_units'] as num?)?.toInt() ?? 0,
        activeTenancies: (json['active_tenancies'] as num?)?.toInt() ?? 0,
        pendingViewings: (json['pending_viewings'] as num?)?.toInt() ?? 0,
        confirmedBookings: (json['confirmed_bookings'] as num?)?.toInt() ?? 0,
        savedHomes: (json['saved_homes'] as num?)?.toInt() ?? 0,
        conversations: (json['conversations'] as num?)?.toInt() ?? 0,
        unreadMessages: (json['unread_messages'] as num?)?.toInt() ?? 0,
      );

  final int properties;
  final int activeProperties;
  final int totalUnits;
  final int availableUnits;
  final int occupiedUnits;
  final int vacatingSoonUnits;
  final int activeTenancies;
  final int pendingViewings;
  final int confirmedBookings;
  final int savedHomes;
  final int conversations;
  final int unreadMessages;
}

class AnalyticsException implements Exception {
  const AnalyticsException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiAnalyticsRepository {
  ApiAnalyticsRepository(this._dio, this._tokenStore);

  factory ApiAnalyticsRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiAnalyticsRepository(
      Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 20),
        ),
      ),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<AdminAnalyticsOverview> adminOverview() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/analytics/admin/overview',
        options: await _authorizedOptions(),
      );
      return AdminAnalyticsOverview.fromJson(response.data!);
    } on DioException catch (error) {
      throw AnalyticsException(_message(error));
    }
  }

  Future<LandlordAnalyticsOverview> landlordOverview() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/analytics/landlord/overview',
        options: await _authorizedOptions(),
      );
      return LandlordAnalyticsOverview.fromJson(response.data!);
    } on DioException catch (error) {
      throw AnalyticsException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const AnalyticsException('Please sign in to view analytics.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'Could not load analytics. Please try again.';
  }
}
