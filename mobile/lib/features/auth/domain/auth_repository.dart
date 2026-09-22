import 'package:rental_property/features/auth/domain/app_user.dart';

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract interface class AuthRepository {
  Future<AppUser?> restoreSession();

  Future<AppUser> login({required String identifier, required String password});

  Future<AppUser> register({
    required String displayName,
    required String phone,
    String? email,
    required String password,
    required String role,
  });

  Future<void> logout();
  Future<void> logoutAll();
}
