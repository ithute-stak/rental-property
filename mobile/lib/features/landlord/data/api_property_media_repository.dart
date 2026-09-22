import 'package:dio/dio.dart';
import 'package:image_picker/image_picker.dart';
import 'package:rental_property/features/auth/data/token_store.dart';

class PropertyMediaItem {
  const PropertyMediaItem({
    required this.id,
    required this.url,
    required this.isCover,
    required this.sortOrder,
  });

  factory PropertyMediaItem.fromJson(Map<String, dynamic> json) {
    return PropertyMediaItem(
      id: json['id'].toString(),
      url: json['url'].toString(),
      isCover: json['is_cover'] == true,
      sortOrder: (json['sort_order'] as num).toInt(),
    );
  }

  final String id;
  final String url;
  final bool isCover;
  final int sortOrder;
}

class PropertyMediaException implements Exception {
  const PropertyMediaException(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApiPropertyMediaRepository {
  ApiPropertyMediaRepository(this._dio, this._tokenStore);

  factory ApiPropertyMediaRepository.fromEnvironment() {
    const baseUrl = String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://10.0.2.2:8000/api/v1',
    );
    return ApiPropertyMediaRepository(
      Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        ),
      ),
      SecureTokenStore(),
    );
  }

  final Dio _dio;
  final TokenStore _tokenStore;

  Future<List<PropertyMediaItem>> list(String propertyId) async {
    try {
      final response = await _dio.get<List<dynamic>>(
        '/properties/$propertyId/media',
        options: await _authorizedOptions(),
      );
      return (response.data ?? const [])
          .map((item) => PropertyMediaItem.fromJson(Map<String, dynamic>.from(item as Map)))
          .toList();
    } on DioException catch (error) {
      throw PropertyMediaException(_message(error));
    }
  }

  Future<void> uploadImages({
    required String propertyId,
    required List<XFile> files,
    required int startingSortOrder,
  }) async {
    for (var index = 0; index < files.length; index++) {
      final file = files[index];
      final contentType = _contentType(file);
      try {
        final targetResponse = await _dio.post<Map<String, dynamic>>(
          '/properties/$propertyId/media/upload-url',
          options: await _authorizedOptions(),
          data: {'content_type': contentType},
        );
        final target = targetResponse.data!;
        final uploadUrl = target['upload_url'].toString();
        final objectKey = target['object_key'].toString();
        final headers = Map<String, String>.from(
          (target['required_headers'] as Map?) ?? const <String, String>{},
        );
        final bytes = await file.readAsBytes();

        await Dio().put<void>(
          uploadUrl,
          data: bytes,
          options: Options(headers: headers, contentType: contentType),
        );

        await _dio.post<Map<String, dynamic>>(
          '/properties/$propertyId/media',
          options: await _authorizedOptions(),
          data: {
            'object_key': objectKey,
            'content_type': contentType,
            'sort_order': startingSortOrder + index,
            'is_cover': false,
          },
        );
      } on DioException catch (error) {
        throw PropertyMediaException(_message(error));
      }
    }
  }

  Future<void> setCover({required String propertyId, required String mediaId}) async {
    try {
      await _dio.put<Map<String, dynamic>>(
        '/properties/$propertyId/media/$mediaId/cover',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw PropertyMediaException(_message(error));
    }
  }

  Future<void> delete({required String propertyId, required String mediaId}) async {
    try {
      await _dio.delete<void>(
        '/properties/$propertyId/media/$mediaId',
        options: await _authorizedOptions(),
      );
    } on DioException catch (error) {
      throw PropertyMediaException(_message(error));
    }
  }

  Future<Options> _authorizedOptions() async {
    final token = await _tokenStore.read();
    if (token == null || token.isEmpty) {
      throw const PropertyMediaException('Please sign in again to manage property photos.');
    }
    return Options(headers: {'Authorization': 'Bearer $token'});
  }

  String _contentType(XFile file) {
    final mimeType = file.mimeType?.toLowerCase();
    if (mimeType == 'image/jpeg' || mimeType == 'image/png' || mimeType == 'image/webp') {
      return mimeType!;
    }
    final name = file.name.toLowerCase();
    if (name.endsWith('.png')) return 'image/png';
    if (name.endsWith('.webp')) return 'image/webp';
    if (name.endsWith('.jpg') || name.endsWith('.jpeg')) return 'image/jpeg';
    throw const PropertyMediaException('Only JPEG, PNG and WebP photos are supported.');
  }

  String _message(DioException error) {
    final data = error.response?.data;
    if (data is Map && data['detail'] is String) {
      return data['detail'] as String;
    }
    if (error.type == DioExceptionType.connectionError ||
        error.type == DioExceptionType.connectionTimeout) {
      return 'Could not connect to the photo service. Check your internet connection.';
    }
    return 'Could not update the property photos. Please try again.';
  }
}
