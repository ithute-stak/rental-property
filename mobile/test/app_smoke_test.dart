import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';
import 'package:rental_property/main.dart';

class _FakeFeedRepository implements FeedRepository {
  @override
  Future<List<PropertySummary>> fetchProperties({String query = ''}) async {
    return const [
      PropertySummary(
        id: 'property-1',
        title: 'Modern room in Maseru',
        area: 'Khubetsoana',
        town: 'Maseru',
        monthlyRent: 1800,
        availableRooms: 2,
        securityLevel: 'Enhanced',
        imageUrl: '',
      ),
    ];
  }
}

void main() {
  testWidgets('feed loads Mosala branding and API-backed property state', (tester) async {
    await tester.pumpWidget(
      RentalPropertyApp(feedRepository: _FakeFeedRepository()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Rental Property Marketplace'), findsOneWidget);
    expect(find.text('Built by Ithute Digital Solutions'), findsOneWidget);
    expect(find.text('Modern room in Maseru'), findsOneWidget);
    expect(find.text('2 available'), findsOneWidget);
  });

  test('property summary accepts decimal rent encoded as a string', () {
    final property = PropertySummary.fromJson(const {
      'id': 'property-2',
      'title': 'Room near town',
      'area': null,
      'town': 'Maseru',
      'monthly_rent': '2150.00',
      'available_rooms': 3,
      'security_level': 'Standard',
      'image_url': null,
    });

    expect(property.monthlyRent, 2150);
    expect(property.area, 'Maseru');
    expect(property.availableRooms, 3);
  });
}
