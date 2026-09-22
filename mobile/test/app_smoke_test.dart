import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/auth/domain/app_user.dart';
import 'package:rental_property/features/auth/domain/auth_repository.dart';
import 'package:rental_property/features/feed/domain/feed_filters.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';
import 'package:rental_property/main.dart';

class _FakeFeedRepository implements FeedRepository {
  @override
  Future<List<PropertySummary>> fetchProperties({
    String query = '',
    FeedFilters filters = const FeedFilters(),
  }) async {
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

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<AppUser?> restoreSession() async => null;

  @override
  Future<AppUser> login({required String identifier, required String password}) {
    throw const AuthException('Not used by this test');
  }

  @override
  Future<AppUser> register({
    required String displayName,
    required String phone,
    String? email,
    required String password,
    required String role,
  }) {
    throw const AuthException('Not used by this test');
  }

  @override
  Future<void> logout() async {}
}

void main() {
  testWidgets('feed loads Mosala branding and API-backed property state', (tester) async {
    await tester.pumpWidget(
      RentalPropertyApp(
        feedRepository: _FakeFeedRepository(),
        authRepository: _FakeAuthRepository(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Rental Property Marketplace'), findsOneWidget);
    expect(find.text('Built by Ithute Digital Solutions'), findsOneWidget);
    expect(find.text('Modern room in Maseru'), findsOneWidget);
    expect(find.text('2 available'), findsOneWidget);
    expect(find.byTooltip('Sign in'), findsOneWidget);
    expect(find.byTooltip('Search filters'), findsOneWidget);
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

  test('feed filters identify active PostGIS radius search', () {
    const filters = FeedFilters(
      town: 'Maseru',
      minRent: 1000,
      maxRent: 3000,
      latitude: -29.3151,
      longitude: 27.4869,
      radiusKm: 8,
    );

    expect(filters.isEmpty, isFalse);
    expect(filters.hasLocation, isTrue);
    expect(filters.radiusKm, 8);
  });
}
