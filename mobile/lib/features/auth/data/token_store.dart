import 'dart:async';
import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class TokenStore {
  Future<String?> read();
  Future<String?> readRefresh();
  Future<void> write(String token);
  Future<void> writeTokens({required String accessToken, required String refreshToken});
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage, Dio? refreshDio})
      : _storage = storage ?? const FlutterSecureStorage(),
        _refreshDio = refreshDio ?? _defaultRefreshDio();

  static const _accessKey = 'mosala_rental_access_token';
  static const _refreshKey = 'mosala_rental_refresh_token';
  static Future<String?>? _refreshInFlight;

  final FlutterSecureStorage _storage;
  final Dio _refreshDio;

  static Dio _defaultRefreshDio() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return Dio(
      BaseOptions(
        baseUrl: baseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
      ),
    );
  }

  @override
  Future<String?> read() async {
    final accessToken = await _storage.read(key: _accessKey);
    final refreshToken = await _storage.read(key: _refreshKey);
    if (refreshToken == null || refreshToken.isEmpty) return accessToken;
    if (accessToken != null && accessToken.isNotEmpty && !_needsRefresh(accessToken)) {
      return accessToken;
    }
    return _rotate(refreshToken, fallbackAccessToken: accessToken);
  }

  bool _needsRefresh(String token) {
    try {
      final parts = token.split('.');
      if (parts.length != 3) return true;
      final payload = jsonDecode(
        utf8.decode(base64Url.decode(base64Url.normalize(parts[1]))),
      );
      if (payload is! Map || payload['exp'] is! num) return true;
      final expiresAt = DateTime.fromMillisecondsSinceEpoch(
        (payload['exp'] as num).toInt() * 1000,
        isUtc: true,
      );
      return expiresAt.isBefore(DateTime.now().toUtc().add(const Duration(seconds: 60)));
    } catch (_) {
      return true;
    }
  }

  Future<String?> _rotate(
    String refreshToken, {
    required String? fallbackAccessToken,
  }) async {
    final inFlight = _refreshInFlight;
    if (inFlight != null) return inFlight;

    final future = _performRotation(
      refreshToken,
      fallbackAccessToken: fallbackAccessToken,
    );
    _refreshInFlight = future;
    try {
      return await future;
    } finally {
      if (identical(_refreshInFlight, future)) {
        _refreshInFlight = null;
      }
    }
  }

  Future<String?> _performRotation(
    String refreshToken, {
    required String? fallbackAccessToken,
  }) async {
    try {
      final response = await _refreshDio.post<Map<String, dynamic>>(
        '/auth/refresh',
        data: {'refresh_token': refreshToken},
      );
      final data = response.data;
      if (data == null) return fallbackAccessToken;
      final access = data['access_token']?.toString();
      final refresh = data['refresh_token']?.toString();
      if (access == null || access.isEmpty || refresh == null || refresh.isEmpty) {
        return fallbackAccessToken;
      }
      await writeTokens(accessToken: access, refreshToken: refresh);
      return access;
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        await clear();
        return null;
      }
      return fallbackAccessToken;
    } catch (_) {
      return fallbackAccessToken;
    }
  }

  @override
  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  @override
  Future<void> write(String token) => _storage.write(key: _accessKey, value: token);

  @override
  Future<void> writeTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _accessKey, value: accessToken);
    await _storage.write(key: _refreshKey, value: refreshToken);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}
