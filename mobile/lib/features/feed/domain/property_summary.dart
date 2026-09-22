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

  final String id;
  final String title;
  final String area;
  final String town;
  final double monthlyRent;
  final int availableRooms;
  final String securityLevel;
  final String imageUrl;

  @override
  List<Object?> get props => [id, title, area, town, monthlyRent, availableRooms, securityLevel, imageUrl];
}
