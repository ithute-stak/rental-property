import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/main.dart';

void main() {
  testWidgets('feed loads initial property cards', (tester) async {
    await tester.pumpWidget(const RentalPropertyApp());

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();

    expect(find.text('Find your next home'), findsOneWidget);
    expect(find.text('Modern room in Maseru'), findsOneWidget);
  });
}
