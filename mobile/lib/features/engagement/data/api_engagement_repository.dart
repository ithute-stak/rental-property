import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class SavedHome {
  const SavedHome({
    required this.propertyId,
    required this.title,
    required this.town,
    required this.area,
    required this.monthlyRent,
    required this.availableRooms,
    required this.imageUrl,
  });

  factory SavedHome.fromJson(Map<String, dynamic> json) => SavedHome(
        propertyId: json['property_id'].toString(),
        title: json['title'].toString(),
        town: json['town'].toString(),
        area: json['area']?.toString(),
        monthlyRent: json['monthly_rent'] == null
            ? null
            : double.tryParse(json['monthly_rent'].toString()),
        availableRooms: (json['available_rooms'] as num?)?.toInt() ?? 0,
        imageUrl: json['image_url']?.toString(),
      );

  final String propertyId;
  final String title;
  final String town;
  final String? area;
  final double? monthlyRent;
  final int availableRooms;
  final String? imageUrl;
}

class ViewingItem {
  const ViewingItem({
    required this.id,
    required this.propertyId,
    required this.propertyTitle,
    required this.requesterName,
    required this.status,
    required this.preferredAt,
    required this.scheduledAt,
    required this.message,
    required this.responseNote,
  });

  factory ViewingItem.fromJson(Map<String, dynamic> json) => ViewingItem(
        id: json['id'].toString(),
        propertyId: json['property_id'].toString(),
        propertyTitle: json['property_title'].toString(),
        requesterName: json['requester_name'].toString(),
        status: json['status'].toString(),
        preferredAt: DateTime.parse(json['preferred_at'].toString()),
        scheduledAt: json['scheduled_at'] == null
            ? null
            : DateTime.parse(json['scheduled_at'].toString()),
        message: json['message']?.toString(),
        responseNote: json['response_note']?.toString(),
      );

  final String id;
  final String propertyId;
  final String propertyTitle;
  final String requesterName;
  final String status;
  final DateTime preferredAt;
  final DateTime? scheduledAt;
  final String? message;
  final String? responseNote;
}

class EngagementException implements Exception {
  const EngagementException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiEngagementRepository {
  ApiEngagementRepository(this._dio, this._tokenStore);

  factory ApiEngagementRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiEngagementRepository(
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

  Future<void> saveProperty(String propertyId) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/engagement/favourites/$propertyId',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<void> unsaveProperty(String propertyId) async {
    try {
      await _dio.delete<void>(
        '/engagement/favourites/$propertyId',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<List<SavedHome>> listSavedHomes() async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/engagement/favourites',
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => SavedHome.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<ViewingItem> requestViewing({
    required String propertyId,
    required DateTime preferredAt,
    String? message,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/engagement/viewings',
        options: await _authorizedOptions(),
        data: {
          'property_id': propertyId,
          'preferred_at': preferredAt.toUtc().toIso8601String(),
          if (message?.trim().isNotEmpty == true) 'message': message!.trim(),
        },
      );
      return ViewingItem.fromJson(response.data!);
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<List<ViewingItem>> listMyViewings() => _list('/engagement/viewings/mine');

  Future<List<ViewingItem>> listLandlordViewings() =>
      _list('/engagement/viewings/landlord');

  Future<ViewingItem> decideViewing({
    required String viewingId,
    required String status,
    DateTime? scheduledAt,
    String? note,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/engagement/viewings/$viewingId/decision',
        options: await _authorizedOptions(),
        data: {
          'status': status,
          if (scheduledAt != null) 'scheduled_at': scheduledAt.toUtc().toIso8601String(),
          if (note?.trim().isNotEmpty == true) 'note': note!.trim(),
        },
      );
      return ViewingItem.fromJson(response.data!);
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<void> cancelViewing(String viewingId) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/engagement/viewings/$viewingId/cancel',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<List<ViewingItem>> _list(String path) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        path,
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => ViewingItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw EngagementException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const EngagementException('Please sign in to use saved homes and viewings.');
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
    return 'Could not complete this action. Please try again.';
  }
}
