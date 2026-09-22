import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:rental_property/features/admin/data/api_audit_repository.dart';
import 'package:rental_property/features/admin/presentation/audit_trail_screen.dart';

class _FakeAuditRepository implements AdminAuditRepository {
  AdminAuditQuery? lastQuery;

  @override
  Future<List<AdminAuditEvent>> listEvents({AdminAuditQuery query = const AdminAuditQuery()}) async {
    lastQuery = query;
    return [
      AdminAuditEvent(
        id: '11111111-2222-3333-4444-555555555555',
        actorId: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
        actorRole: 'admin',
        action: 'landlord.verification.approved',
        entityType: 'landlord_profile',
        entityId: '99999999-8888-7777-6666-555555555555',
        requestId: 'audit-request-123',
        details: const {
          'from_status': 'pending',
          'to_status': 'approved',
          'user_id': '12345678-abcd-abcd-abcd-123456789012',
        },
        createdAt: DateTime(2026, 9, 22, 15, 30),
      ),
    ];
  }
}

void main() {
  testWidgets('admin audit trail renders request and expanded business state', (tester) async {
    final repository = _FakeAuditRepository();

    await tester.pumpWidget(
      MaterialApp(
        home: AuditTrailScreen(repository: repository),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Audit trail'), findsOneWidget);
    expect(find.text('Immutable business history'), findsOneWidget);
    expect(find.text('Landlord verification approved'), findsOneWidget);
    expect(find.text('Request: audit-request-123'), findsOneWidget);
    expect(repository.lastQuery, isNotNull);

    await tester.tap(find.text('Landlord verification approved'));
    await tester.pumpAndSettle();

    expect(find.text('Business state'), findsOneWidget);
    expect(find.text('From status'), findsOneWidget);
    expect(find.text('pending'), findsOneWidget);
    expect(find.text('To status'), findsOneWidget);
    expect(find.text('approved'), findsOneWidget);
    expect(find.text('Request ID'), findsOneWidget);
    expect(find.text('audit-request-123'), findsOneWidget);
  });
}
