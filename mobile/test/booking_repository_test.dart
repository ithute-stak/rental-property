import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/booking/data/api_booking_repository.dart';

void main() {
  test('parses rental unit money and availability', () {
    final unit = RentalUnit.fromJson({
      'id': 'unit-1',
      'name': 'Room 3',
      'monthly_rent': '1800.00',
      'deposit': 900,
      'status': 'available',
      'available_from': '2026-10-01',
    });

    expect(unit.monthlyRent, 1800);
    expect(unit.deposit, 900);
    expect(unit.canBook, isTrue);
    expect(unit.availableFrom, DateTime(2026, 10, 1));
  });

  test('parses persistent booking state returned by API', () {
    final booking = BookingSummary.fromJson({
      'id': 'booking-1',
      'unit_id': 'unit-1',
      'property_id': 'property-1',
      'property_title': 'Mosala Test Property',
      'unit_name': 'Room 3',
      'status': 'payment_review',
      'move_in_date': '2026-10-01',
      'amount_due': '900.00',
      'currency': 'LSL',
      'payment_status': 'submitted',
      'payment_method': 'mobile_money',
      'payment_reference': 'MP-123',
    });

    expect(booking.status, 'payment_review');
    expect(booking.paymentStatus, 'submitted');
    expect(booking.amountDue, 900);
  });
}
