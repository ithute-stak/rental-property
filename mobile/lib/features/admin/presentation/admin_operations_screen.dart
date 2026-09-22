import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/admin/data/api_admin_operations_repository.dart';
import 'package:rental_property/features/booking/data/api_booking_repository.dart';
import 'package:rental_property/features/booking/presentation/booking_screens.dart';

class AdminOperationsScreen extends StatelessWidget {
  const AdminOperationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mosala administration')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Image.asset('assets/branding/mosala_logo.webp', height: 100),
          const SizedBox(height: 16),
          _AdminTile(
            icon: Icons.verified_user_outlined,
            title: 'Landlord verification',
            subtitle: 'Review landlord profiles before they can submit adverts.',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => LandlordVerificationQueueScreen(
                  repository: ApiAdminOperationsRepository.fromEnvironment(),
                ),
              ),
            ),
          ),
          _AdminTile(
            icon: Icons.fact_check_outlined,
            title: 'Property advert review',
            subtitle: 'Approve properties, issue advert charges and activate paid adverts.',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => PropertyReviewQueueScreen(
                  repository: ApiAdminOperationsRepository.fromEnvironment(),
                ),
              ),
            ),
          ),
          _AdminTile(
            icon: Icons.payments_outlined,
            title: 'Booking payment review',
            subtitle: 'Verify tenant booking payments before rooms become booked.',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => AdminBookingReviewScreen(
                  repository: ApiBookingRepository.fromEnvironment(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class LandlordVerificationQueueScreen extends StatefulWidget {
  const LandlordVerificationQueueScreen({super.key, required this.repository});

  final ApiAdminOperationsRepository repository;

  @override
  State<LandlordVerificationQueueScreen> createState() => _LandlordVerificationQueueScreenState();
}

class _LandlordVerificationQueueScreenState extends State<LandlordVerificationQueueScreen> {
  late Future<List<AdminLandlordReview>> _items;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _items = widget.repository.pendingLandlords();

  Future<void> _decide(AdminLandlordReview item, bool approved) async {
    String? reason;
    if (!approved) {
      reason = await _reasonDialog('Why is verification being returned?');
      if (reason == null || !mounted) return;
    }
    setState(() => _busyId = item.userId);
    try {
      await widget.repository.decideLandlord(
        userId: item.userId,
        approved: approved,
        reason: reason,
      );
      if (mounted) setState(_reload);
    } on AdminOperationsException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<String?> _reasonDialog(String title) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: 'Reason / changes required',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text.trim()),
            child: const Text('Continue'),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Landlord verification')),
      body: FutureBuilder<List<AdminLandlordReview>>(
        future: _items,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) return _error(snapshot.error.toString());
          final items = snapshot.data ?? const [];
          if (items.isEmpty) return const _EmptyState(message: 'No landlord profiles are waiting for review.');
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _items;
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: items.length,
              itemBuilder: (context, index) {
                final item = items[index];
                final busy = _busyId == item.userId;
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(item.displayName, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
                        if (item.businessName?.isNotEmpty == true) Text(item.businessName!),
                        Text(item.phone),
                        if (item.email != null) Text(item.email!),
                        const SizedBox(height: 6),
                        Text(item.physicalAddress ?? 'No address supplied'),
                        const SizedBox(height: 14),
                        Row(
                          children: [
                            Expanded(
                              child: OutlinedButton(
                                onPressed: _busyId == null ? () => _decide(item, false) : null,
                                child: const Text('Return / reject'),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: FilledButton(
                                onPressed: _busyId == null ? () => _decide(item, true) : null,
                                child: busy
                                    ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                                    : const Text('Approve'),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }

  Widget _error(String message) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, size: 52),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            ],
          ),
        ),
      );
}

class PropertyReviewQueueScreen extends StatefulWidget {
  const PropertyReviewQueueScreen({super.key, required this.repository});

  final ApiAdminOperationsRepository repository;

  @override
  State<PropertyReviewQueueScreen> createState() => _PropertyReviewQueueScreenState();
}

class _PropertyReviewQueueScreenState extends State<PropertyReviewQueueScreen> {
  String _status = 'pending_verification';
  late Future<List<AdminPropertyReview>> _items;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _items = widget.repository.properties(status: _status);

  void _changeStatus(String value) {
    setState(() {
      _status = value;
      _reload();
    });
  }

  Future<void> _run(String id, Future<void> Function() action) async {
    setState(() => _busyId = id);
    try {
      await action();
      if (mounted) setState(_reload);
    } on AdminOperationsException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _quote(AdminPropertyReview item) async {
    final controller = TextEditingController();
    var waive = false;
    final result = await showDialog<_ChargeInput>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: Text('Advert charge • ${item.title}'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: controller,
                enabled: !waive,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Charge (Maloti)', border: OutlineInputBorder()),
              ),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: waive,
                onChanged: (value) => setDialogState(() => waive = value ?? false),
                title: const Text('Waive advertising charge'),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
            FilledButton(
              onPressed: () {
                final amount = waive ? 0.0 : double.tryParse(controller.text.trim());
                if (amount == null || (!waive && amount <= 0)) return;
                Navigator.pop(context, _ChargeInput(amount: amount, waive: waive));
              },
              child: const Text('Save charge'),
            ),
          ],
        ),
      ),
    );
    controller.dispose();
    if (result == null || !mounted) return;
    await _run(
      item.id,
      () async {
        await widget.repository.quoteCharge(
          propertyId: item.id,
          amount: result.amount,
          waive: result.waive,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Property advert review')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'pending_verification', label: Text('Pending')),
                ButtonSegment(value: 'approved', label: Text('Approved')),
              ],
              selected: {_status},
              onSelectionChanged: (selection) => _changeStatus(selection.first),
            ),
          ),
          Expanded(
            child: FutureBuilder<List<AdminPropertyReview>>(
              future: _items,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text(snapshot.error.toString(), textAlign: TextAlign.center));
                }
                final items = snapshot.data ?? const [];
                if (items.isEmpty) return const _EmptyState(message: 'No properties in this queue.');
                return RefreshIndicator(
                  onRefresh: () async {
                    setState(_reload);
                    await _items;
                  },
                  child: ListView.builder(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                    itemCount: items.length,
                    itemBuilder: (context, index) => _PropertyReviewCard(
                      item: items[index],
                      busy: _busyId == items[index].id,
                      anyBusy: _busyId != null,
                      onApprove: () => _run(items[index].id, () => widget.repository.approveProperty(items[index].id)),
                      onReject: () => _run(items[index].id, () => widget.repository.rejectProperty(items[index].id)),
                      onQuote: () => _quote(items[index]),
                      onConfirmPayment: () => _run(items[index].id, () => widget.repository.confirmCharge(items[index].id)),
                      onRejectPayment: () => _run(items[index].id, () => widget.repository.rejectCharge(items[index].id)),
                      onActivate: () => _run(items[index].id, () => widget.repository.activateProperty(items[index].id)),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _PropertyReviewCard extends StatelessWidget {
  const _PropertyReviewCard({
    required this.item,
    required this.busy,
    required this.anyBusy,
    required this.onApprove,
    required this.onReject,
    required this.onQuote,
    required this.onConfirmPayment,
    required this.onRejectPayment,
    required this.onActivate,
  });

  final AdminPropertyReview item;
  final bool busy;
  final bool anyBusy;
  final VoidCallback onApprove;
  final VoidCallback onReject;
  final VoidCallback onQuote;
  final VoidCallback onConfirmPayment;
  final VoidCallback onRejectPayment;
  final VoidCallback onActivate;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 2);
    final charge = item.advertCharge;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(item.title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
            Text('${item.area ?? item.town}, ${item.district} • ${item.totalRooms} rooms'),
            Text('Owner: ${item.ownerName} • ${item.ownerPhone}'),
            Text('Security: ${item.securityLevel}'),
            if (charge != null) ...[
              const SizedBox(height: 8),
              Text('Advert charge: ${money.format(charge.amount)} • ${charge.status.replaceAll('_', ' ')}'),
              if (charge.paymentReference?.isNotEmpty == true) Text('Reference: ${charge.paymentReference}'),
            ],
            const SizedBox(height: 14),
            if (busy) const Center(child: CircularProgressIndicator()) else _actions(),
          ],
        ),
      ),
    );
  }

  Widget _actions() {
    if (item.status == 'pending_verification') {
      return Row(
        children: [
          Expanded(child: OutlinedButton(onPressed: anyBusy ? null : onReject, child: const Text('Reject'))),
          const SizedBox(width: 10),
          Expanded(child: FilledButton(onPressed: anyBusy ? null : onApprove, child: const Text('Approve'))),
        ],
      );
    }
    if (item.status == 'approved') {
      if (item.advertCharge == null || item.advertCharge!.status == 'payment_rejected') {
        return FilledButton.icon(
          onPressed: anyBusy ? null : onQuote,
          icon: const Icon(Icons.price_change_outlined),
          label: Text(item.advertCharge == null ? 'Set advert charge' : 'Revise charge'),
        );
      }
      if (item.advertCharge!.status == 'quoted') {
        return const Text('Waiting for landlord to submit the advertising payment reference.');
      }
      if (item.advertCharge!.status == 'payment_submitted') {
        return Row(
          children: [
            Expanded(child: OutlinedButton(onPressed: anyBusy ? null : onRejectPayment, child: const Text('Reject payment'))),
            const SizedBox(width: 10),
            Expanded(child: FilledButton(onPressed: anyBusy ? null : onConfirmPayment, child: const Text('Confirm payment'))),
          ],
        );
      }
      if (item.advertCharge!.status == 'paid' || item.advertCharge!.status == 'waived') {
        return FilledButton.icon(
          onPressed: anyBusy ? null : onActivate,
          icon: const Icon(Icons.campaign_outlined),
          label: const Text('Activate advert'),
        );
      }
    }
    return Text('Status: ${item.status.replaceAll('_', ' ')}');
  }
}

class _AdminTile extends StatelessWidget {
  const _AdminTile({required this.icon, required this.title, required this.subtitle, required this.onTap});

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Card(
        child: ListTile(
          contentPadding: const EdgeInsets.all(16),
          leading: CircleAvatar(child: Icon(icon)),
          title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
          subtitle: Text(subtitle),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: onTap,
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.task_alt_rounded, size: 56),
              const SizedBox(height: 12),
              Text(message, textAlign: TextAlign.center),
            ],
          ),
        ),
      );
}

class _ChargeInput {
  const _ChargeInput({required this.amount, required this.waive});
  final double amount;
  final bool waive;
}
