import 'package:dio/dio.dart';
import 'package:rental_property/features/auth/data/token_store.dart';
import 'package:rental_property/features/auth/domain/app_user.dart';
import 'package:rental_property/features/auth/domain/auth_repository.dart';

class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository(this._dio, this._tokenStore);

  factory ApiAuthRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiAuthRepository(
      Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        ),
      ),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  @override
  Future<AppUser?> restoreSession() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      return null;
    }

    try {
      final response = await _dio.get<Map<String, dynamic>>(
        '/auth/me',
        options: Options(headers: {'Authorization': 'Bearer $token'}),
      );
      return AppUser.fromJson(response.data!);
    } on DioException catch (error) {
      if (error.response?.statusCode == 401) {
        await _tokenStore.clear();
        return null;
      }
      throw AuthException(_message(error));
    }
  }

  @override
  Future<AppUser> login({required String identifier, required String password}) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'identifier': identifier.trim(), 'password': password},
      );
      final data = response.data!;
      await _tokenStore.write(data['access_token'].toString());
      return AppUser.fromJson(Map<String, dynamic>.from(data['user'] as Map));
    } on DioException catch (error) {
      throw AuthException(_message(error));
    }
  }

  @override
  Future<AppUser> register({
    required String displayName,
    required String phone,
    String? email,
    required String password,
    required String role,
  }) async {
    try {
      await _dio.post<Map<String, dynamic>>(
        '/auth/register',
        data: {
          'display_name': displayName.trim(),
          'phone': phone.trim(),
          if (email?.trim().isNotEmpty == true) 'email': email!.trim(),
          'password': password,
          'role': role,
        },
      );
      return await login(identifier: phone, password: password);
    } on DioException catch (error) {
      throw AuthException(_message(error));
    }
  }

  @override
  Future<void> logout() => _tokenStore.clear();

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) {
      return data['detail'] as String;
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return 'Could not connect to Mosala Rentals. Check your internet connection.';
    }
    return 'Something went wrong. Please try again.';
  }
}
