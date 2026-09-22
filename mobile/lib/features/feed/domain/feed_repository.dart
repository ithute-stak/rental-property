import 'package:rental_property/features/feed/domain/property_summary.dart';

abstract interface class FeedRepository {
  Future<List<PropertySummary>> fetchProperties({String query = ''});
}
