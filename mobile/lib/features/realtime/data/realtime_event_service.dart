import 'dart:async';
import 'dart:convert';

import 'package:rental_property/features/auth/data/token_store.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class RealtimeNotificationEvent {
  const RealtimeNotificationEvent({
    required this.id,
    required this.notificationType,
    required this.title,
    required this.body,
    required this.payload,
  });

  factory RealtimeNotificationEvent.fromJson(Map<String, dynamic> json) {
    return RealtimeNotificationEvent(
      id: json['id'].toString(),
      notificationType: json['notification_type'].toString(),
      title: json['title'].toString(),
      body: json['body'].toString(),
      payload: Map<String, dynamic>.from(json['payload'] as Map? ?? const {}),
    );
  }

  final String id;
  final String notificationType;
  final String title;
  final String body;
  final Map<String, dynamic> payload;
}

class RealtimeEventService {
  RealtimeEventService({TokenStore? tokenStore})
      : _tokenStore = tokenStore ?? SecureTokenStore();

  static const _apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );

  final TokenStore _tokenStore;
  final _events = StreamController<RealtimeNotificationEvent>.broadcast();
  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;
  bool _running = false;
  int _generation = 0;

  Stream<RealtimeNotificationEvent> get events => _events.stream;

  Future<void> start() async {
    _running = true;
    _generation += 1;
    final generation = _generation;
    await _disconnect();
    await _connect(generation);
  }

  Future<void> stop() async {
    _running = false;
    _generation += 1;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    await _disconnect();
  }

  Future<void> dispose() async {
    await stop();
    await _events.close();
  }

  Future<void> _connect(int generation) async {
    if (!_running || generation != _generation) return;
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty || !_running || generation != _generation) {
      return;
    }

    final base = Uri.parse(_apiBaseUrl);
    final path = '${base.path.replaceFirst(RegExp(r'/$'), '')}/realtime/events';
    final uri = base.replace(
      scheme: base.scheme == 'https' ? 'wss' : 'ws',
      path: path,
      query: null,
      fragment: null,
    );

    try {
      final channel = WebSocketChannel.connect(uri);
      await channel.ready;
      if (!_running || generation != _generation) {
        await channel.sink.close();
        return;
      }
      _channel = channel;
      channel.sink.add(jsonEncode({'type': 'authenticate', 'token': token}));
      _subscription = channel.stream.listen(
        _handleMessage,
        onDone: () => _scheduleReconnect(generation),
        onError: (_) => _scheduleReconnect(generation),
        cancelOnError: true,
      );
    } catch (_) {
      _scheduleReconnect(generation);
    }
  }

  void _handleMessage(dynamic raw) {
    if (raw is! String) return;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map<String, dynamic> || decoded['type'] != 'notification') {
        return;
      }
      final notification = decoded['notification'];
      if (notification is Map<String, dynamic>) {
        _events.add(RealtimeNotificationEvent.fromJson(notification));
      }
    } catch (_) {
      // Ignore malformed frames. Persisted notifications remain available via REST.
    }
  }

  void _scheduleReconnect(int generation) {
    if (!_running || generation != _generation || _reconnectTimer?.isActive == true) {
      return;
    }
    _reconnectTimer = Timer(const Duration(seconds: 3), () {
      if (_running && generation == _generation) {
        _connect(generation);
      }
    });
  }

  Future<void> _disconnect() async {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    await _subscription?.cancel();
    _subscription = null;
    final channel = _channel;
    _channel = null;
    if (channel != null) {
      await channel.sink.close();
    }
  }
}
