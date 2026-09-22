import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/realtime/data/realtime_client.dart';

void main() {
  test('realtime URI follows the API base and upgrades HTTPS to WSS', () {
    final uri = realtimeUriFromApiBase('https://rentals.example.com/api/v1');

    expect(uri.toString(), 'wss://rentals.example.com/api/v1/realtime');
  });

  test('realtime URI keeps local HTTP development on WS', () {
    final uri = realtimeUriFromApiBase('http://10.0.2.2:8000/api/v1/');

    expect(uri.toString(), 'ws://10.0.2.2:8000/api/v1/realtime');
  });

  test('notification event exposes notification payload', () {
    final event = RealtimeEvent.fromJson({
      'type': 'notification.created',
      'notification': {
        'id': 'n-1',
        'title': 'Viewing confirmed',
        'body': 'Your viewing has been accepted.',
      },
    });

    expect(event.type, 'notification.created');
    expect(event.notification?['id'], 'n-1');
    expect(event.notification?['title'], 'Viewing confirmed');
  });
}
