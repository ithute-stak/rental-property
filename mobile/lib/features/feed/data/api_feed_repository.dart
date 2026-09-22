import 'package:dio/dio.dart';
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
  Future<List<PropertySummary>> fetchProperties({String query = ''}) async {
    final trimmedQuery = query.trim();
    final response = await _dio.get<List<dynamic>>(
      '/properties/feed',
      queryParameters: {
        if (trimmedQuery.isNotEmpty) 'q': trimmedQuery,
      },
    );

    final data = response.data ?? const <dynamic>[];
    return data
        .map((item) => PropertySummary.fromJson(Map<String, dynamic>.from(item as Map)))
        .toList(growable: false);
  }
}
