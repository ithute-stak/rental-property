import 'package:equatable/equatable.dart';

class FeedFilters extends Equatable {
  const FeedFilters({
    this.district = '',
    this.town = '',
    this.area = '',
    this.minRent,
    this.maxRent,
    this.latitude,
    this.longitude,
    this.radiusKm = 10,
  });

  final String district;
  final String town;
  final String area;
  final double? minRent;
  final double? maxRent;
  final double? latitude;
  final double? longitude;
  final double radiusKm;

  bool get hasLocation => latitude != null && longitude != null;

  bool get isEmpty =>
      district.trim().isEmpty &&
      town.trim().isEmpty &&
      area.trim().isEmpty &&
      minRent == null &&
      maxRent == null &&
      !hasLocation;

  FeedFilters copyWith({
    String? district,
    String? town,
    String? area,
    double? minRent,
    bool clearMinRent = false,
    double? maxRent,
    bool clearMaxRent = false,
    double? latitude,
    bool clearLocation = false,
    double? longitude,
    double? radiusKm,
  }) {
    return FeedFilters(
      district: district ?? this.district,
      town: town ?? this.town,
      area: area ?? this.area,
      minRent: clearMinRent ? null : (minRent ?? this.minRent),
      maxRent: clearMaxRent ? null : (maxRent ?? this.maxRent),
      latitude: clearLocation ? null : (latitude ?? this.latitude),
      longitude: clearLocation ? null : (longitude ?? this.longitude),
      radiusKm: radiusKm ?? this.radiusKm,
    );
  }

  @override
  List<Object?> get props => [
        district,
        town,
        area,
        minRent,
        maxRent,
        latitude,
        longitude,
        radiusKm,
      ];
}
