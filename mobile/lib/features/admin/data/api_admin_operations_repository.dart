import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';
import 'package:rental_property/features/landlord/data/api_landlord_account_repository.dart';

class AdminLandlordReview {
  const AdminLandlordReview({
    required this.userId,
    required this.displayName,
    required this.phone,
    required this.email,
    required this.businessName,
    required this.physicalAddress,
  });

  factory AdminLandlordReview.fromJson(Map<String, dynamic> json) => AdminLandlordReview(
        userId: json['user_id'].toString(),
        displayName: json['display_name'].toString(),
        phone: json['phone'].toString(),
        email: json['email'] as String?,
        businessName: json['business_name'] as String?,
        physicalAddress: json['physical_address'] as String?,
      );

  final String userId;
  final String displayName;
  final String phone;
  final String? email;
  final String? businessName;
  final String? physicalAddress;
}

class AdminPropertyReview {
  const AdminPropertyReview({
    required this.id,
    required this.ownerId,
    required this.ownerName,
    required this.ownerPhone,
    required this.title,
    required this.propertyType,
    required this.status,
    required this.district,
    required this.town,
    required this.area,
    required this.totalRooms,
    required this.securityLevel,
    required this.advertCharge,
  });

  factory AdminPropertyReview.fromJson(Map<String, dynamic> json) => AdminPropertyReview(
        id: json['id'].toString(),
        ownerId: json['owner_id'].toString(),
        ownerName: json['owner_name'].toString(),
        ownerPhone: json['owner_phone'].toString(),
        title: json['title'].toString(),
        propertyType: json['property_type'].toString(),
        status: json['status'].toString(),
        district: json['district'].toString(),
        town: json['town'].toString(),
        area: json['area'] as String?,
        totalRooms: (json['total_rooms'] as num).toInt(),
        securityLevel: json['security_level'].toString(),
        advertCharge: json['advert_charge'] == null
            ? null
            : AdvertChargeSummary.fromJson(
                Map<String, dynamic>.from(json['advert_charge'] as Map),
              ),
      );

  final String id;
  final String ownerId;
  final String ownerName;
  final String ownerPhone;
  final String title;
  final String propertyType;
  final String status;
  final String district;
  final String town;
  final String? area;
  final int totalRooms;
  final String securityLevel;
  final AdvertChargeSummary? advertCharge;
}

class AdminOperationsException implements Exception {
  const AdminOperationsException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiAdminOperationsRepository {
  ApiAdminOperationsRepository(this._dio, this._tokenStore);

  factory ApiAdminOperationsRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiAdminOperationsRepository(
      Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10))),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<List<AdminLandlordReview>> pendingLandlords() async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/admin/landlords/pending',
        options: await _options(),
      );
      return (response.data ?? const [])
          .map((item) => AdminLandlordReview.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw AdminOperationsException(_message(error));
    }
  }

  Future<void> decideLandlord({
    required String userId,
    required bool approved,
    String? reason,
  }) async {
    try {
      await _dio.patch<Map<String, dynamic>>(
        '/admin/landlords/$userId/verification',
        options: await _options(),
        data: {'approved': approved, 'reason': reason},
      );
    } on DioException catch (error) {
      throw AdminOperationsException(_message(error));
    }
  }

  Future<List<AdminPropertyReview>> properties({String status = 'pending_verification'}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/admin/properties/review',
        queryParameters: {'review_status': status},
        options: await _options(),
      );
      return (response.data ?? const [])
          .map((item) => AdminPropertyReview.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw AdminOperationsException(_message(error));
    }
  }

  Future<void> approveProperty(String propertyId) => _post('/admin/properties/$propertyId/approve');

  Future<void> rejectProperty(String propertyId) => _post('/admin/properties/$propertyId/reject');

  Future<AdvertChargeSummary> quoteCharge({
    required String propertyId,
    required double amount,
    String? note,
    bool waive = false,
  }) async {
    try {
      final response = await _dio.put<Map<String, dynamic>>(
        '/admin/properties/$propertyId/charge',
        options: await _options(),
        data: {'amount': amount, 'note': note, 'waive': waive},
      );
      return AdvertChargeSummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw AdminOperationsException(_message(error));
    }
  }

  Future<void> confirmCharge(String propertyId) =>
      _post('/admin/properties/$propertyId/charge/confirm', data: {'note': 'Payment verified by Mosala admin.'});

  Future<void> rejectCharge(String propertyId) =>
      _post('/admin/properties/$propertyId/charge/reject', data: {'note': 'Payment reference could not be verified.'});

  Future<void> activateProperty(String propertyId) => _post('/admin/properties/$propertyId/activate');

  Future<void> _post(String path, {Map<String, dynamic>? data}) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        path,
        options: await _options(),
        data: data,
      );
    } on DioException catch (error) {
      throw AdminOperationsException(_message(error));
    }
  }

  Future<Options> _options() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const AdminOperationsException('Please sign in again as a Mosala administrator.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'The admin operation could not be completed. Please try again.';
  }
}
