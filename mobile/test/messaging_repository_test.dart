import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/messaging/data/api_messaging_repository.dart';

void main() {
  test('parses conversation unread state', () {
    final conversation = MessagingConversation.fromJson({
      'id': 'conversation-1',
      'property_id': 'property-1',
      'property_title': 'Maseru room',
      'other_party_id': 'user-2',
      'other_party_name': 'Mpho',
      'last_message': 'Is water included?',
      'last_message_at': '2026-09-22T10:00:00Z',
      'unread_count': 2,
    });

    expect(conversation.otherPartyName, 'Mpho');
    expect(conversation.unreadCount, 2);
    expect(conversation.lastMessage, 'Is water included?');
  });

  test('parses message ownership', () {
    final message = ChatMessage.fromJson({
      'id': 'message-1',
      'conversation_id': 'conversation-1',
      'sender_id': 'user-1',
      'sender_name': 'Theko',
      'body': 'Can I view it tomorrow?',
      'created_at': '2026-09-22T10:00:00Z',
      'read_at': null,
      'is_mine': true,
    });

    expect(message.isMine, isTrue);
    expect(message.body, 'Can I view it tomorrow?');
  });
}
