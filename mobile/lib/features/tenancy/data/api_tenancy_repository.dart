import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class TenancySummary {
  const TenancySummary({
    required this.id,
    required this.bookingId,
    required this.unitId,
    required this.propertyId,
    required this.propertyTitle,
    required this.unitName,
    required this.tenantId,
    required this.tenantName,
    required this.status,
    required this.startDate,
    required this.expectedMoveOut,
    required this.allowReadvertise,
  });

  factory TenancySummary.fromJson(Map<String, dynamic> json) => TenancySummary(
        id: json['id'].toString(),
        bookingId: json['booking_id'].toString(),
        unitId: json['unit_id'].toString(),
        propertyId: json['property_id'].toString(),
        propertyTitle: json['property_title'].toString(),
        unitName: json['unit_name'].toString(),
        tenantId: json['tenant_id'].toString(),
        tenantName: json['tenant_name'].toString(),
        status: json['status'].toString(),
        startDate: DateTime.parse(json['start_date'].toString()),
        expectedMoveOut: json['expected_move_out'] == null
            ? null
            : DateTime.parse(json['expected_move_out'].toString()),
        allowReadvertise: json['allow_readvertise'] as bool? ?? true,
      );

  final String id;
  final String bookingId;
  final String unitId;
  final String propertyId;
  final String propertyTitle;
  final String unitName;
  final String tenantId;
  final String tenantName;
  final String status;
  final DateTime startDate;
  final DateTime? expectedMoveOut;
  final bool allowReadvertise;
}

class TenancyException implements Exception {
  const TenancyException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiTenancyRepository {
  ApiTenancyRepository(this._dio, this._tokenStore);

  factory ApiTenancyRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiTenancyRepository(
      Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10))),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<List<TenancySummary>> listMine() => _list('/tenancies/mine');

  Future<List<TenancySummary>> listLandlord() => _list('/tenancies/landlord');

  Future<TenancySummary> activate(String bookingId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/tenancies/activate',
        data: {'booking_id': bookingId},
        options: await _options(),
      );
      return TenancySummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw TenancyException(_message(error));
    }
  }

  Future<TenancySummary> giveNotice({
    required String tenancyId,
    required DateTime expectedMoveOut,
    required bool allowReadvertise,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/tenancies/$tenancyId/notice',
        options: await _options(),
        data: {
          'expected_move_out': _date(expectedMoveOut),
          'allow_readvertise': allowReadvertise,
        },
      );
      return TenancySummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw TenancyException(_message(error));
    }
  }

  Future<TenancySummary> end(String tenancyId) => _post('/tenancies/$tenancyId/end');

  Future<TenancySummary> completeInspection(String tenancyId) =>
      _post('/tenancies/$tenancyId/inspection-complete');

  Future<List<TenancySummary>> _list(String path) async {
    try {
      final response = await _dio.get<List<dynamic>>(path, options: await _options());
      return (response.data ?? const [])
          .map((item) => TenancySummary.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw TenancyException(_message(error));
    }
  }

  Future<TenancySummary> _post(String path) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(path, options: await _options());
      return TenancySummary.fromJson(response.data!);
    } on DioException catch (error) {
      throw TenancyException(_message(error));
    }
  }

  Future<Options> _options() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const TenancyException('Please sign in to manage the tenancy.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'The tenancy request could not be completed. Please try again.';
  }
}

String _date(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
