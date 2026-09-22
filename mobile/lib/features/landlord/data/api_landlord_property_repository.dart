import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class LandlordPropertySummary {
  const LandlordPropertySummary({
    required this.id,
    required this.title,
    required this.status,
    required this.town,
    required this.totalRooms,
  });

  factory LandlordPropertySummary.fromJson(Map<String, dynamic> json) {
    return LandlordPropertySummary(
      id: json['id'].toString(),
      title: json['title'].toString(),
      status: json['status'].toString(),
      town: json['town'].toString(),
      totalRooms: (json['total_rooms'] as num).toInt(),
    );
  }

  final String id;
  final String title;
  final String status;
  final String town;
  final int totalRooms;
}

class LandlordPropertyException implements Exception {
  const LandlordPropertyException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiLandlordPropertyRepository {
  ApiLandlordPropertyRepository(this._dio, this._tokenStore);

  factory ApiLandlordPropertyRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiLandlordPropertyRepository(
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

  Future<List<LandlordPropertySummary>> listMine() async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/properties/mine',
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => LandlordPropertySummary.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw LandlordPropertyException(_message(error));
    }
  }

  Future<String> createProperty({
    required String title,
    required String description,
    required String propertyType,
    required String physicalAddress,
    required String district,
    required String town,
    String? area,
    required double latitude,
    required double longitude,
    required int totalRooms,
    required String securityLevel,
    required Map<String, Object> securityFeatures,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/properties',
        options: await _authorizedOptions(),
        data: {
          'title': title.trim(),
          'description': description.trim(),
          'property_type': propertyType,
          'physical_address': physicalAddress.trim(),
          'district': district.trim(),
          'town': town.trim(),
          if (area?.trim().isNotEmpty == true) 'area': area!.trim(),
          'latitude': latitude,
          'longitude': longitude,
          'total_rooms': totalRooms,
          'security_level': securityLevel,
          'security_features': securityFeatures,
        },
      );
      return response.data!['id'].toString();
    } on DioException catch (error) {
      throw LandlordPropertyException(_message(error));
    }
  }

  Future<void> createUnit({
    required String propertyId,
    required String name,
    required double monthlyRent,
    required double deposit,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/properties/$propertyId/units',
        options: await _authorizedOptions(),
        data: {
          'name': name.trim(),
          'monthly_rent': monthlyRent,
          'deposit': deposit,
        },
      );
    } on DioException catch (error) {
      throw LandlordPropertyException(_message(error));
    }
  }

  Future<void> submitProperty(String propertyId) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/properties/$propertyId/submit',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw LandlordPropertyException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const LandlordPropertyException('Please sign in again to manage properties.');
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
    return 'Could not save the property. Please try again.';
  }
}
