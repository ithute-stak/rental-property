import 'package:equatable/equatable.dart';

class PropertySummary extends Equatable {
  const PropertySummary({
    required this.id,
    required this.title,
    required this.area,
    required this.town,
    required this.monthlyRent,
    required this.availableRooms,
    required this.securityLevel,
    required this.imageUrl,
  });

  factory PropertySummary.fromJson(Map<String, dynamic> json) {
    final rawRent = json['monthly_rent'];
    final monthlyRent = rawRent is num
        ? rawRent.toDouble()
        : double.parse(rawRent.toString());

    return PropertySummary(
      id: json['id'].toString(),
      title: json['title'].toString(),
      area: (json['area'] as String?)?.trim().isNotEmpty == true
          ? json['area'] as String
          : json['town'].toString(),
      town: json['town'].toString(),
      monthlyRent: monthlyRent,
      availableRooms: (json['available_rooms'] as num).toInt(),
      securityLevel: json['security_level'].toString(),
      imageUrl: (json['image_url'] as String?) ?? '',
    );
  }

  final String id;
  final String title;
  final String area;
  final String town;
  final double monthlyRent;
  final int availableRooms;
  final String securityLevel;
  final String imageUrl;

  @override
  List<Object?> get props => [
        id,
        title,
        area,
        town,
        monthlyRent,
        availableRooms,
        securityLevel,
        imageUrl,
      ];
}
