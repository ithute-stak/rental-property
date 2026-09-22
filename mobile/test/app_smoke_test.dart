import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/main.dart';

void main() {
  testWidgets('feed loads Mosala branding and initial property cards', (tester) async {
    await tester.pumpWidget(const RentalPropertyApp());

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();

    expect(find.text('Find your next home'), findsOneWidget);
    expect(find.text('Rental Property Marketplace'), findsOneWidget);
    expect(find.text('Built by Ithute Digital Solutions'), findsOneWidget);
    expect(find.byType(Image), findsAtLeastNWidgets(1));
    expect(find.text('Modern room in Maseru'), findsOneWidget);
  });
}
