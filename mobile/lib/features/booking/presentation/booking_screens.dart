import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/auth/presentation/account_screen.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';
import 'package:rental_property/features/booking/data/api_booking_repository.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';

class PropertyBookingScreen extends StatefulWidget {
  const PropertyBookingScreen({
    super.key,
    required this.property,
    required this.repository,
  });

  final PropertySummary property;
  final ApiBookingRepository repository;

  @override
  State<PropertyBookingScreen> createState() => _PropertyBookingScreenState();
}

class _PropertyBookingScreenState extends State<PropertyBookingScreen> {
  late Future<List<RentalUnit>> _units;
  String? _busyUnitId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _units = widget.repository.listUnits(widget.property.id);
  }

  Future<void> _book(RentalUnit unit) async {
    var session = context.read<SessionCubit>().state;
    if (session is! SessionAuthenticated) {
      await Navigator.of(context).push<void>(
        MaterialPageRoute(builder: (_) => const AccountScreen()),
      );
      if (!mounted) return;
      session = context.read<SessionCubit>().state;
    }
    if (session is! SessionAuthenticated) return;
    if (session.user.role != 'house_seeker' && session.user.role != 'tenant') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Use a house seeker or tenant account to book a room.')),
      );
      return;
    }

    final earliest = unit.availableFrom != null && unit.availableFrom!.isAfter(DateTime.now())
        ? unit.availableFrom!
        : DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: DateTime(earliest.year, earliest.month, earliest.day),
      firstDate: DateTime(earliest.year, earliest.month, earliest.day),
      lastDate: DateTime.now().add(const Duration(days: 730)),
      helpText: 'Choose your move-in date',
    );
    if (selected == null || !mounted) return;

    setState(() => _busyUnitId = unit.id);
    try {
      await widget.repository.acquireHold(unit.id);
      final booking = await widget.repository.createBooking(
        unitId: unit.id,
        moveInDate: selected,
      );
      if (!mounted) return;
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => PaymentSubmissionScreen(
            booking: booking,
            repository: widget.repository,
          ),
        ),
      );
      if (mounted) setState(_reload);
    } on BookingException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyUnitId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 0);
    return Scaffold(
      appBar: AppBar(title: Text(widget.property.title)),
      body: FutureBuilder<List<RentalUnit>>(
        future: _units,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _CenteredMessage(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load rental units',
              message: snapshot.error.toString(),
              action: FilledButton(
                onPressed: () => setState(_reload),
                child: const Text('Try again'),
              ),
            );
          }
          final units = snapshot.data ?? const [];
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (widget.property.imageUrl.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.network(
                    widget.property.imageUrl,
                    height: 210,
                    width: double.infinity,
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) => const SizedBox.shrink(),
                  ),
                ),
              const SizedBox(height: 16),
              Text(
                widget.property.title,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text('${widget.property.area}, ${widget.property.town}'),
              const SizedBox(height: 18),
              Text('Available rooms', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 10),
              if (units.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(24),
                    child: Text('There are no rental units to show right now.'),
                  ),
                ),
              for (final unit in units)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                unit.name,
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                              ),
                            ),
                            Chip(label: Text(unit.status.replaceAll('_', ' '))),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text('${money.format(unit.monthlyRent)} / month'),
                        Text('Deposit: ${money.format(unit.deposit)}'),
                        if (unit.availableFrom != null)
                          Text('Available from ${DateFormat.yMMMd().format(unit.availableFrom!)}'),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: !unit.canBook || _busyUnitId != null ? null : () => _book(unit),
                            icon: _busyUnitId == unit.id
                                ? const SizedBox.square(
                                    dimension: 18,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.event_available_rounded),
                            label: Text(unit.canBook ? 'Book this room' : 'Not available'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class PaymentSubmissionScreen extends StatefulWidget {
  const PaymentSubmissionScreen({
    super.key,
    required this.booking,
    required this.repository,
  });

  final BookingSummary booking;
  final ApiBookingRepository repository;

  @override
  State<PaymentSubmissionScreen> createState() => _PaymentSubmissionScreenState();
}

class _PaymentSubmissionScreenState extends State<PaymentSubmissionScreen> {
  final _referenceController = TextEditingController();
  String _method = 'mobile_money';
  bool _submitting = false;
  bool _submitted = false;

  @override
  void dispose() {
    _referenceController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_referenceController.text.trim().length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter the payment transaction/reference number.')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await widget.repository.submitPayment(
        bookingId: widget.booking.id,
        method: _method,
        reference: _referenceController.text,
      );
      if (mounted) setState(() => _submitted = true);
    } on BookingException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 2);
    return Scaffold(
      appBar: AppBar(title: const Text('Booking payment')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Icon(
            _submitted ? Icons.verified_outlined : Icons.account_balance_wallet_outlined,
            size: 64,
          ),
          const SizedBox(height: 16),
          Text(
            _submitted ? 'Payment sent for verification' : 'Secure your booking',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          Text(
            '${widget.booking.propertyTitle} • ${widget.booking.unitName}',
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 8),
          Text(
            money.format(widget.booking.amountDue),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 24),
          if (_submitted) ...[
            const Card(
              child: Padding(
                padding: EdgeInsets.all(18),
                child: Text(
                  'Mosala Rentals has received your payment reference. The system administrator will verify it before the room is marked booked. You and the landlord will be notified after confirmation.',
                  textAlign: TextAlign.center,
                ),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Done'),
            ),
          ] else ...[
            DropdownButtonFormField<String>(
              initialValue: _method,
              decoration: const InputDecoration(
                labelText: 'Payment method',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'mobile_money', child: Text('Mobile money')),
                DropdownMenuItem(value: 'bank_transfer', child: Text('Bank transfer')),
                DropdownMenuItem(value: 'cash', child: Text('Cash / counter payment')),
                DropdownMenuItem(value: 'card', child: Text('Card')),
              ],
              onChanged: _submitting ? null : (value) => setState(() => _method = value ?? 'mobile_money'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _referenceController,
              decoration: const InputDecoration(
                labelText: 'Transaction / payment reference',
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.receipt_long_outlined),
              ),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send_rounded),
              label: const Text('Submit payment for verification'),
            ),
          ],
        ],
      ),
    );
  }
}

class MyBookingsScreen extends StatefulWidget {
  const MyBookingsScreen({super.key, required this.repository});

  final ApiBookingRepository repository;

  @override
  State<MyBookingsScreen> createState() => _MyBookingsScreenState();
}

class _MyBookingsScreenState extends State<MyBookingsScreen> {
  late Future<List<BookingSummary>> _bookings;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _bookings = widget.repository.listMine();

  Future<void> _cancel(BookingSummary booking) async {
    try {
      await widget.repository.cancel(booking.id);
      if (mounted) setState(_reload);
    } on BookingException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My bookings')),
      body: FutureBuilder<List<BookingSummary>>(
        future: _bookings,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _CenteredMessage(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load bookings',
              message: snapshot.error.toString(),
              action: FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            );
          }
          final bookings = snapshot.data ?? const [];
          if (bookings.isEmpty) {
            return const _CenteredMessage(
              icon: Icons.event_busy_outlined,
              title: 'No bookings yet',
              message: 'Rooms you book will appear here.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _bookings;
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: bookings.length,
              itemBuilder: (context, index) {
                final booking = bookings[index];
                final canCancel = booking.status == 'pending_payment' || booking.status == 'payment_review';
                return Card(
                  child: ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.meeting_room_outlined)),
                    title: Text('${booking.propertyTitle} • ${booking.unitName}'),
                    subtitle: Text(
                      'Move in ${DateFormat.yMMMd().format(booking.moveInDate)}\nBooking: ${booking.status.replaceAll('_', ' ')} • Payment: ${booking.paymentStatus.replaceAll('_', ' ')}',
                    ),
                    isThreeLine: true,
                    trailing: canCancel
                        ? IconButton(
                            tooltip: 'Cancel booking',
                            onPressed: () => _cancel(booking),
                            icon: const Icon(Icons.close_rounded),
                          )
                        : const Icon(Icons.chevron_right_rounded),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

class AdminBookingReviewScreen extends StatefulWidget {
  const AdminBookingReviewScreen({super.key, required this.repository});

  final ApiBookingRepository repository;

  @override
  State<AdminBookingReviewScreen> createState() => _AdminBookingReviewScreenState();
}

class _AdminBookingReviewScreenState extends State<AdminBookingReviewScreen> {
  late Future<List<BookingSummary>> _bookings;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _bookings = widget.repository.listAdminReview();

  Future<void> _decide(BookingSummary booking, bool approve) async {
    setState(() => _busyId = booking.id);
    try {
      if (approve) {
        await widget.repository.confirm(booking.id, note: 'Payment verified in Mosala admin review.');
      } else {
        await widget.repository.reject(booking.id, note: 'Payment could not be verified by Mosala admin.');
      }
      if (mounted) setState(_reload);
    } on BookingException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 2);
    return Scaffold(
      appBar: AppBar(title: const Text('Booking payment review')),
      body: FutureBuilder<List<BookingSummary>>(
        future: _bookings,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _CenteredMessage(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load review queue',
              message: snapshot.error.toString(),
              action: FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            );
          }
          final bookings = snapshot.data ?? const [];
          if (bookings.isEmpty) {
            return const _CenteredMessage(
              icon: Icons.verified_outlined,
              title: 'Review queue is clear',
              message: 'Submitted booking payments will appear here for verification.',
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: bookings.length,
            itemBuilder: (context, index) {
              final booking = bookings[index];
              final busy = _busyId == booking.id;
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${booking.propertyTitle} • ${booking.unitName}',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 6),
                      Text('Amount: ${money.format(booking.amountDue)}'),
                      Text('Method: ${booking.paymentMethod ?? '-'}'),
                      Text('Reference: ${booking.paymentReference ?? '-'}'),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(
                            child: OutlinedButton(
                              onPressed: _busyId != null ? null : () => _decide(booking, false),
                              child: const Text('Reject'),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: FilledButton(
                              onPressed: _busyId != null ? null : () => _decide(booking, true),
                              child: busy
                                  ? const SizedBox.square(
                                      dimension: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Text('Confirm booking'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class _CenteredMessage extends StatelessWidget {
  const _CenteredMessage({
    required this.icon,
    required this.title,
    required this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 56),
            const SizedBox(height: 14),
            Text(title, style: Theme.of(context).textTheme.titleLarge, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      ),
    );
  }
}
