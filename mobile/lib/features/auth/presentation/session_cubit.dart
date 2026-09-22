import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/auth/domain/app_user.dart';
import 'package:rental_property/features/auth/domain/auth_repository.dart';

sealed class SessionState extends Equatable {
  const SessionState();

  @override
  List<Object?> get props => [];
}

final class SessionChecking extends SessionState {
  const SessionChecking();
}

final class SessionGuest extends SessionState {
  const SessionGuest({this.message});

  final String? message;

  @override
  List<Object?> get props => [message];
}

final class SessionAuthenticated extends SessionState {
  const SessionAuthenticated(this.user);

  final AppUser user;

  @override
  List<Object?> get props => [user];
}

class SessionCubit extends Cubit<SessionState> {
  SessionCubit(this._repository) : super(const SessionChecking());

  final AuthRepository _repository;

  Future<void> restore() async {
    emit(const SessionChecking());
    try {
      final user = await _repository.restoreSession();
      emit(user == null ? const SessionGuest() : SessionAuthenticated(user));
    } on AuthException catch (error) {
      emit(SessionGuest(message: error.message));
    } catch (_) {
      emit(const SessionGuest(message: 'Could not restore your session.'));
    }
  }

  Future<bool> login({required String identifier, required String password}) async {
    try {
      final user = await _repository.login(identifier: identifier, password: password);
      emit(SessionAuthenticated(user));
      return true;
    } on AuthException catch (error) {
      emit(SessionGuest(message: error.message));
      return false;
    } catch (_) {
      emit(const SessionGuest(message: 'Could not sign in. Please try again.'));
      return false;
    }
  }

  Future<bool> register({
    required String displayName,
    required String phone,
    String? email,
    required String password,
    required String role,
  }) async {
    try {
      final user = await _repository.register(
        displayName: displayName,
        phone: phone,
        email: email,
        password: password,
        role: role,
      );
      emit(SessionAuthenticated(user));
      return true;
    } on AuthException catch (error) {
      emit(SessionGuest(message: error.message));
      return false;
    } catch (_) {
      emit(const SessionGuest(message: 'Could not create your account. Please try again.'));
      return false;
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    emit(const SessionGuest());
  }
}
