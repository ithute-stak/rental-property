import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class AppNotification {
  const AppNotification({
    required this.id,
    required this.type,
    required this.title,
    required this.body,
    required this.isRead,
    required this.createdAt,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) => AppNotification(
        id: json['id'].toString(),
        type: json['notification_type'].toString(),
        title: json['title'].toString(),
        body: json['body'].toString(),
        isRead: json['read_at'] != null,
        createdAt: DateTime.parse(json['created_at'].toString()),
      );

  final String id;
  final String type;
  final String title;
  final String body;
  final bool isRead;
  final DateTime createdAt;
}

class NotificationException implements Exception {
  const NotificationException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiNotificationRepository {
  ApiNotificationRepository(this._dio, this._tokenStore);

  factory ApiNotificationRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiNotificationRepository(
      Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10))),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<List<AppNotification>> list({bool unreadOnly = false}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/notifications',
        queryParameters: {'unread_only': unreadOnly},
        options: await _options(),
      );
      return (response.data ?? const [])
          .map((item) => AppNotification.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw NotificationException(_message(error));
    }
  }

  Future<void> markRead(String notificationId) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/notifications/$notificationId/read',
        options: await _options(),
      );
    } on DioException catch (error) {
      throw NotificationException(_message(error));
    }
  }

  Future<Options> _options() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const NotificationException('Please sign in to view notifications.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'Could not load notifications. Please try again.';
  }
}
