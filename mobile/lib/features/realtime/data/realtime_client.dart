import 'dart:async';
import 'dart:convert';

import 'package:rental_property/features/auth/data/token_store.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class RealtimeEvent {
  const RealtimeEvent({required this.type, required this.data});

  factory RealtimeEvent.fromJson(Map<String, dynamic> json) => RealtimeEvent(
        type: json['type']?.toString() ?? 'unknown',
        data: json,
      );

  final String type;
  final Map<String, dynamic> data;

  Map<String, dynamic>? get notification {
    final value = data['notification'];
    return value is Map ? Map<String, dynamic>.from(value) : null;
  }
}

Uri realtimeUriFromApiBase(String apiBaseUrl) {
  final base = Uri.parse(apiBaseUrl);
  if (base.scheme != 'http' && base.scheme != 'https') {
    throw ArgumentError.value(apiBaseUrl, 'apiBaseUrl', 'Expected an HTTP(S) API base URL');
  }
  final normalizedPath = base.path.endsWith('/')
      ? base.path.substring(0, base.path.length - 1)
      : base.path;
  return base.replace(
    scheme: base.scheme == 'https' ? 'wss' : 'ws',
    path: '$normalizedPath/realtime',
    query: null,
    fragment: null,
  );
}

class RealtimeClient {
  RealtimeClient(this._uri, this._tokenStore);

  factory RealtimeClient.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return RealtimeClient(realtimeUriFromApiBase(baseUrl), SecureTokenStore());
  }

  final Uri _uri;
  final TokenStore _tokenStore;
  final StreamController<RealtimeEvent> _events = StreamController.broadcast();
  final Set<String> _seenNotificationIds = <String>{};

  WebSocketChannel? _channel;
  StreamSubscription<dynamic>? _subscription;
  Timer? _reconnectTimer;
  bool _shouldRun = false;
  bool _connecting = false;
  int _reconnectAttempt = 0;

  Stream<RealtimeEvent> get events => _events.stream;

  Future<void> start() async {
    _shouldRun = true;
    await _connect();
  }

  Future<void> _connect() async {
    if (!_shouldRun || _connecting || _subscription != null) return;
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) return;

    _connecting = true;
    try {
      final channel = WebSocketChannel.connect(_uri);
      _channel = channel;
      await channel.ready.timeout(const Duration(seconds: 10));
      if (!_shouldRun) {
        await channel.sink.close();
        return;
      }
      channel.sink.add(jsonEncode({'type': 'authenticate', 'token': token}));
      _subscription = channel.stream.listen(
        _onMessage,
        onDone: _handleDisconnect,
        onError: (_) => _handleDisconnect(),
        cancelOnError: true,
      );
    } catch (_) {
      await _closeTransport();
      _scheduleReconnect();
    } finally {
      _connecting = false;
    }
  }

  void _onMessage(dynamic raw) {
    if (raw is! String) return;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) return;
      final event = RealtimeEvent.fromJson(Map<String, dynamic>.from(decoded));
      if (event.type == 'ready') {
        _reconnectAttempt = 0;
      }
      if (event.type == 'notification.created' && !_acceptNotification(event)) {
        return;
      }
      if (event.type != 'ping' && !_events.isClosed) {
        _events.add(event);
      }
    } catch (_) {
      // Ignore malformed server frames; the durable HTTP notification list remains authoritative.
    }
  }

  bool _acceptNotification(RealtimeEvent event) {
    final id = event.notification?['id']?.toString();
    if (id == null || id.isEmpty) return true;
    if (!_seenNotificationIds.add(id)) return false;
    if (_seenNotificationIds.length > 200) {
      _seenNotificationIds.remove(_seenNotificationIds.first);
    }
    return true;
  }

  void _handleDisconnect() {
    unawaited(_closeTransport().whenComplete(_scheduleReconnect));
  }

  void _scheduleReconnect() {
    if (!_shouldRun || _reconnectTimer != null) return;
    final seconds = switch (_reconnectAttempt) {
      0 => 1,
      1 => 2,
      2 => 4,
      3 => 8,
      4 => 16,
      _ => 30,
    };
    _reconnectAttempt += 1;
    _reconnectTimer = Timer(Duration(seconds: seconds), () {
      _reconnectTimer = null;
      unawaited(_connect());
    });
  }

  Future<void> _closeTransport() async {
    final subscription = _subscription;
    _subscription = null;
    if (subscription != null) {
      await subscription.cancel();
    }
    final channel = _channel;
    _channel = null;
    if (channel != null) {
      await channel.sink.close();
    }
  }

  Future<void> stop() async {
    _shouldRun = false;
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
    _reconnectAttempt = 0;
    await _closeTransport();
  }

  Future<void> dispose() async {
    await stop();
    await _events.close();
  }
}
