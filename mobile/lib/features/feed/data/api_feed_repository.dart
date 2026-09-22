import 'package:dio/dio.dart';
import 'package:rental_property/features/feed/domain/feed_filters.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';

class ApiFeedRepository implements FeedRepository {
  ApiFeedRepository(this._dio);

  factory ApiFeedRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );

    return ApiFeedRepository(
      Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 15),
        ),
      ),
    );
  }

  final Dio _dio;

  @override
  Future<List<PropertySummary>> fetchProperties({
    String query = '',
    FeedFilters filters = const FeedFilters(),
  }) async {
    final searchParts = <String>[
      if (query.trim().isNotEmpty) query.trim(),
      if (filters.area.trim().isNotEmpty) filters.area.trim(),
    ];
    final searchText = searchParts.join(' ').trim();

    final response = await _dio.get<List<dynamic>>(
      '/properties/feed',
      queryParameters: {
        if (searchText.isNotEmpty) 'q': searchText,
        if (filters.district.trim().isNotEmpty) 'district': filters.district.trim(),
        if (filters.town.trim().isNotEmpty) 'town': filters.town.trim(),
        if (filters.minRent != null) 'min_rent': filters.minRent,
        if (filters.maxRent != null) 'max_rent': filters.maxRent,
        if (filters.hasLocation) 'latitude': filters.latitude,
        if (filters.hasLocation) 'longitude': filters.longitude,
        if (filters.hasLocation) 'radius_km': filters.radiusKm,
      },
    );

    final data = response.data ?? const <dynamic>[];
    return data
        .map((item) => PropertySummary.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(growable: false);
  }
}
