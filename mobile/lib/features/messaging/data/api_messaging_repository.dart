import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class MessagingConversation {
  const MessagingConversation({
    required this.id,
    required this.propertyId,
    required this.propertyTitle,
    required this.otherPartyId,
    required this.otherPartyName,
    required this.lastMessage,
    required this.lastMessageAt,
    required this.unreadCount,
  });

  factory MessagingConversation.fromJson(Map<String, dynamic> json) => MessagingConversation(
        id: json['id'].toString(),
        propertyId: json['property_id'].toString(),
        propertyTitle: json['property_title'].toString(),
        otherPartyId: json['other_party_id'].toString(),
        otherPartyName: json['other_party_name'].toString(),
        lastMessage: json['last_message']?.toString(),
        lastMessageAt: json['last_message_at'] == null
            ? null
            : DateTime.parse(json['last_message_at'].toString()),
        unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
      );

  final String id;
  final String propertyId;
  final String propertyTitle;
  final String otherPartyId;
  final String otherPartyName;
  final String? lastMessage;
  final DateTime? lastMessageAt;
  final int unreadCount;
}

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.conversationId,
    required this.senderId,
    required this.senderName,
    required this.body,
    required this.createdAt,
    required this.readAt,
    required this.isMine,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        id: json['id'].toString(),
        conversationId: json['conversation_id'].toString(),
        senderId: json['sender_id'].toString(),
        senderName: json['sender_name'].toString(),
        body: json['body'].toString(),
        createdAt: DateTime.parse(json['created_at'].toString()),
        readAt: json['read_at'] == null ? null : DateTime.parse(json['read_at'].toString()),
        isMine: json['is_mine'] == true,
      );

  final String id;
  final String conversationId;
  final String senderId;
  final String senderName;
  final String body;
  final DateTime createdAt;
  final DateTime? readAt;
  final bool isMine;
}

class MessagingException implements Exception {
  const MessagingException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiMessagingRepository {
  ApiMessagingRepository(this._dio, this._tokenStore);

  factory ApiMessagingRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiMessagingRepository(
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

  Future<MessagingConversation> startConversation(String propertyId) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/messaging/conversations',
        data: {'property_id': propertyId},
        options: await _authorizedOptions(),
      );
      return MessagingConversation.fromJson(response.data!);
    } on DioException catch (error) {
      throw MessagingException(_message(error));
    }
  }

  Future<List<MessagingConversation>> listConversations() async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/messaging/conversations',
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => MessagingConversation.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw MessagingException(_message(error));
    }
  }

  Future<List<ChatMessage>> listMessages(String conversationId) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/messaging/conversations/$conversationId/messages',
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw MessagingException(_message(error));
    }
  }

  Future<ChatMessage> sendMessage(String conversationId, String body) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/messaging/conversations/$conversationId/messages',
        data: {'body': body.trim()},
        options: await _authorizedOptions(),
      );
      return ChatMessage.fromJson(response.data!);
    } on DioException catch (error) {
      throw MessagingException(_message(error));
    }
  }

  Future<void> markRead(String conversationId) async {
    try {
      await _dio.post<void>(
        '/messaging/conversations/$conversationId/read',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw MessagingException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const MessagingException('Please sign in to use Mosala messages.');
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
    return 'Could not complete the messaging action. Please try again.';
  }
}
