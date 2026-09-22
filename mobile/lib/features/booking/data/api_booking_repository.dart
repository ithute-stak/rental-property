import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class RentalUnit {
  const RentalUnit({
    required this.id,
    required this.name,
    required this.monthlyRent,
    required this.deposit,
    required this.status,
    required this.availableFrom,
  });

  factory RentalUnit.fromJson(Map<String, dynamic> json) => RentalUnit(
        id: json['id'].toString(),
        name: json['name'].toString(),
        monthlyRent: _money(json['monthly_rent']),
        deposit: _money(json['deposit']),
        status: json['status'].toString(),
        availableFrom: json['available_from'] == null
            ? null
            : DateTime.tryParse(json['available_from'].toString()),
      );

  final String id;
  final String name;
  final double monthlyRent;
  final double deposit;
  final String status;
  final DateTime? availableFrom;

  bool get canBook => status == 'available' || status == 'vacating_soon';
}

class BookingSummary {
  const BookingSummary({
    required this.id,
    required this.unitId,
    required this.propertyId,
    required this.propertyTitle,
    required this.unitName,
    required this.status,
    required this.moveInDate,
    required this.amountDue,
    required this.currency,
    required this.paymentStatus,
    required this.paymentMethod,
    required this.paymentReference,
  });

  factory BookingSummary.fromJson(Map<String, dynamic> json) => BookingSummary(
        id: json['id'].toString(),
        unitId: json['unit_id'].toString(),
        propertyId: json['property_id'].toString(),
        propertyTitle: json['property_title'].toString(),
        unitName: json['unit_name'].toString(),
        status: json['status'].toString(),
        moveInDate: DateTime.parse(json['move_in_date'].toString()),
        amountDue: _money(json['amount_due']),
        currency: json['currency'].toString(),
        paymentStatus: json['payment_status'].toString(),
        paymentMethod: json['payment_method'] as String?,
        paymentReference: json['payment_reference'] as String?,
      );

  final String id;
  final String unitId;
  final String propertyId;
  final String propertyTitle;
  final String unitName;
  final String status;
  final DateTime moveInDate;
  final double amountDue;
  final String currency;
  final String paymentStatus;
  final String? paymentMethod;
  final String? paymentReference;
}

class BookingException implements Exception {
  const BookingException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiBookingRepository {
  ApiBookingRepository(this._dio, this._tokenStore);

  factory ApiBookingRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiBookingRepository(
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

  Future<List<RentalUnit>> listUnits(String propertyId) async {
    try {
      final response = await _dio.get<List<dynamic>>('/properties/$propertyId/units');
      return (response.data ?? const [])
          .map((item) => RentalUnit.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<void> acquireHold(String unitId) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/bookings/holds/$unitId',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<BookingSummary> createBooking({
    required String unitId,
    required DateTime moveInDate,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/bookings',
        options: await _authorizedOptions(),
        data: {
          'unit_id': unitId,
          'move_in_date': _date(moveInDate),
        },
      );
      return BookingSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<BookingSummary> submitPayment({
    required String bookingId,
    required String method,
    required String reference,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/bookings/$bookingId/payment',
        options: await _authorizedOptions(),
        data: {'method': method, 'reference': reference.trim()},
      );
      return BookingSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<List<BookingSummary>> listMine() => _list('/bookings/mine');

  Future<List<BookingSummary>> listLandlord() => _list('/bookings/landlord');

  Future<List<BookingSummary>> listAdminReview() => _list('/bookings/admin/review');

  Future<BookingSummary> confirm(String bookingId, {String? note}) async {
    return _decision('/bookings/$bookingId/confirm', note);
  }

  Future<BookingSummary> reject(String bookingId, {String? note}) async {
    return _decision('/bookings/$bookingId/reject', note);
  }

  Future<BookingSummary> cancel(String bookingId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/bookings/$bookingId/cancel',
        options: await _authorizedOptions(),
      );
      return BookingSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<List<BookingSummary>> _list(String path) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        path,
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => BookingSummary.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<BookingSummary> _decision(String path, String? note) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        path,
        options: await _authorizedOptions(),
        data: {'note': note?.trim().isEmpty == true ? null : note?.trim()},
      );
      return BookingSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw BookingException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const BookingException('Please sign in to continue with this booking.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) {
      return data['detail'] as String;
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return 'Could not connect to Mosala Rentals. Check your internet connection.';
    }
    return 'The booking request could not be completed. Please try again.';
  }
}

double _money(Object? value) {
  if (value is num) return value.toDouble();
  return double.parse(value.toString());
}

String _date(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
