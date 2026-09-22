import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class LandlordVerificationProfile {
  const LandlordVerificationProfile({
    required this.userId,
    required this.businessName,
    required this.physicalAddress,
    required this.status,
    required this.rejectionReason,
  });

  factory LandlordVerificationProfile.fromJson(Map<String, dynamic> json) =>
      LandlordVerificationProfile(
        userId: json['user_id'].toString(),
        businessName: json['business_name'] as String?,
        physicalAddress: json['physical_address'] as String?,
        status: json['verification_status'].toString(),
        rejectionReason: json['rejection_reason'] as String?,
      );

  final String userId;
  final String? businessName;
  final String? physicalAddress;
  final String status;
  final String? rejectionReason;
}

class AdvertChargeSummary {
  const AdvertChargeSummary({
    required this.id,
    required this.propertyId,
    required this.amount,
    required this.currency,
    required this.status,
    required this.note,
    required this.paymentMethod,
    required this.paymentReference,
  });

  factory AdvertChargeSummary.fromJson(Map<String, dynamic> json) => AdvertChargeSummary(
        id: json['id'].toString(),
        propertyId: json['property_id'].toString(),
        amount: _money(json['amount']),
        currency: json['currency'].toString(),
        status: json['status'].toString(),
        note: json['note'] as String?,
        paymentMethod: json['payment_method'] as String?,
        paymentReference: json['payment_reference'] as String?,
      );

  final String id;
  final String propertyId;
  final double amount;
  final String currency;
  final String status;
  final String? note;
  final String? paymentMethod;
  final String? paymentReference;
}

class LandlordAccountException implements Exception {
  const LandlordAccountException(this.message, {this.notFound = false});

  final String message;
  final bool notFound;

  @override
  String toString() => message;
}

class ApiLandlordAccountRepository {
  ApiLandlordAccountRepository(this._dio, this._tokenStore);

  factory ApiLandlordAccountRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiLandlordAccountRepository(
      Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10))),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<LandlordVerificationProfile> getProfile() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/landlords/me',
        options: await _options(),
      );
      return LandlordVerificationProfile.fromJson(response.data!);
    } on DioException catch (error) {
      throw LandlordAccountException(_message(error));
    }
  }

  Future<LandlordVerificationProfile> updateProfile({
    String? businessName,
    required String physicalAddress,
  }) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/landlords/me',
        options: await _options(),
        data: {
          if (businessName?.trim().isNotEmpty == true) 'business_name': businessName!.trim(),
          'physical_address': physicalAddress.trim(),
        },
      );
      return LandlordVerificationProfile.fromJson(response.data!);
    } on DioException catch (error) {
      throw LandlordAccountException(_message(error));
    }
  }

  Future<LandlordVerificationProfile> submitVerification() async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/landlords/me/submit',
        options: await _options(),
      );
      return LandlordVerificationProfile.fromJson(response.data!);
    } on DioException catch (error) {
      throw LandlordAccountException(_message(error));
    }
  }

  Future<AdvertChargeSummary?> getAdvertCharge(String propertyId) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/advertising/properties/$propertyId/charge',
        options: await _options(),
      );
      return AdvertChargeSummary.fromJson(response.data!);
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) return null;
      throw LandlordAccountException(_message(error));
    }
  }

  Future<AdvertChargeSummary> submitAdvertPayment({
    required String propertyId,
    required String method,
    required String reference,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/advertising/properties/$propertyId/charge/payment',
        options: await _options(),
        data: {'method': method, 'reference': reference.trim()},
      );
      return AdvertChargeSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw LandlordAccountException(_message(error));
    }
  }

  Future<Options> _options() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const LandlordAccountException('Please sign in again to manage your landlord account.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'Could not update the landlord account. Please try again.';
  }
}

double _money(Object? value) {
  if (value is num) return value.toDouble();
  return double.parse(value.toString());
}
