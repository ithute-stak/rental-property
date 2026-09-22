import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class AdminAuditEvent {
  const AdminAuditEvent({
    required this.id,
    required this.actorId,
    required this.actorRole,
    required this.action,
    required this.entityType,
    required this.entityId,
    required this.requestId,
    required this.details,
    required this.createdAt,
  });

  factory AdminAuditEvent.fromJson(Map<String, dynamic> json) => AdminAuditEvent(
        id: json['id'].toString(),
        actorId: json['actor_id'] as String?,
        actorRole: json['actor_role'] as String?,
        action: json['action'].toString(),
        entityType: json['entity_type'].toString(),
        entityId: json['entity_id'] as String?,
        requestId: json['request_id'] as String?,
        details: Map<String, dynamic>.from(json['details'] as Map? ?? const {}),
        createdAt: DateTime.parse(json['created_at'].toString()).toLocal(),
      );

  final String id;
  final String? actorId;
  final String? actorRole;
  final String action;
  final String entityType;
  final String? entityId;
  final String? requestId;
  final Map<String, dynamic> details;
  final DateTime createdAt;
}

class AdminAuditQuery {
  const AdminAuditQuery({
    this.action,
    this.entityType,
    this.entityId,
    this.actorId,
    this.requestId,
    this.since,
    this.until,
    this.limit = 100,
  });

  final String? action;
  final String? entityType;
  final String? entityId;
  final String? actorId;
  final String? requestId;
  final DateTime? since;
  final DateTime? until;
  final int limit;

  bool get hasFilters => [action, entityType, entityId, actorId, requestId]
      .any((value) => value != null && value.trim().isNotEmpty) ||
      since != null ||
      until != null;

  Map<String, dynamic> toQueryParameters() {
    final result = <String, dynamic>{'limit': limit};
    void add(String key, String? value) {
      final normalized = value?.trim();
      if (normalized != null && normalized.isNotEmpty) result[key] = normalized;
    }

    add('action', action);
    add('entity_type', entityType);
    add('entity_id', entityId);
    add('actor_id', actorId);
    add('request_id', requestId);
    if (since != null) result['since'] = since!.toUtc().toIso8601String();
    if (until != null) result['until'] = until!.toUtc().toIso8601String();
    return result;
  }
}

class AdminAuditException implements Exception {
  const AdminAuditException(this.message);
  final String message;

  @override
  String toString() => message;
}

abstract class AdminAuditRepository {
  Future<List<AdminAuditEvent>> listEvents({AdminAuditQuery query = const AdminAuditQuery()});
}

class ApiAdminAuditRepository implements AdminAuditRepository {
  ApiAdminAuditRepository(this._dio, this._tokenStore);

  factory ApiAdminAuditRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiAdminAuditRepository(
      Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 10))),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  @override
  Future<List<AdminAuditEvent>> listEvents({AdminAuditQuery query = const AdminAuditQuery()}) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/admin/audit',
        queryParameters: query.toQueryParameters(),
        options: await _options(),
      );
      return (response.data ?? const [])
          .map(
            (item) => AdminAuditEvent.fromJson(
              Map<String, dynamic>.from(item as Map),
            ),
          )
          .toList();
    } on DioException catch (error) {
      throw AdminAuditException(_message(error));
    }
  }

  Future<Options> _options() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const AdminAuditException('Please sign in again as a Mosala administrator.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) return data['detail'] as String;
    return 'The audit trail could not be loaded. Please try again.';
  }
}
