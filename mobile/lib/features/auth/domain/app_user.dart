import 'package:equatable/equatable.dart';

class AppUser extends Equatable {
  const AppUser({
    required this.id,
    required this.email,
    required this.phone,
    required this.displayName,
    required this.role,
    required this.isActive,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      id: json['id'].toString(),
      email: json['email'] as String?,
      phone: json['phone'].toString(),
      displayName: json['display_name'].toString(),
      role: json['role'].toString(),
      isActive: json['is_active'] as bool? ?? true,
    );
  }

  final String id;
  final String? email;
  final String phone;
  final String displayName;
  final String role;
  final bool isActive;

  bool get isLandlord => role == 'landlord';
  bool get isAdmin => role == 'admin';

  @override
  List<Object?> get props => [id, email, phone, displayName, role, isActive];
}
