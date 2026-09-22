import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/booking/data/api_booking_repository.dart';
import 'package:rental_property/features/tenancy/data/api_tenancy_repository.dart';

class TenantTenanciesScreen extends StatefulWidget {
  const TenantTenanciesScreen({super.key, required this.repository});

  final ApiTenancyRepository repository;

  @override
  State<TenantTenanciesScreen> createState() => _TenantTenanciesScreenState();
}

class _TenantTenanciesScreenState extends State<TenantTenanciesScreen> {
  late Future<List<TenancySummary>> _tenancies;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _tenancies = widget.repository.listMine();

  Future<void> _giveNotice(TenancySummary tenancy) async {
    final tomorrow = DateTime.now().add(const Duration(days: 1));
    final date = await showDatePicker(
      context: context,
      initialDate: tomorrow,
      firstDate: tomorrow,
      lastDate: DateTime.now().add(const Duration(days: 730)),
      helpText: 'Expected move-out date',
    );
    if (date == null || !mounted) return;

    var readvertise = true;
    final proceed = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('Give notice'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Expected move-out: ${DateFormat.yMMMMd().format(date)}'),
              const SizedBox(height: 10),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: readvertise,
                onChanged: (value) => setDialogState(() => readvertise = value ?? true),
                title: const Text('Allow future re-advertising'),
                subtitle: const Text(
                  'The room can appear in search now, but its available-from date will be the day after you move out.',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Submit notice')),
          ],
        ),
      ),
    );
    if (proceed != true || !mounted) return;

    setState(() => _busyId = tenancy.id);
    try {
      await widget.repository.giveNotice(
        tenancyId: tenancy.id,
        expectedMoveOut: date,
        allowReadvertise: readvertise,
      );
      if (mounted) setState(_reload);
    } on TenancyException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My tenancy')),
      body: FutureBuilder<List<TenancySummary>>(
        future: _tenancies,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _Message(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load tenancy',
              message: snapshot.error.toString(),
              action: FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            );
          }
          final rows = snapshot.data ?? const [];
          if (rows.isEmpty) {
            return const _Message(
              icon: Icons.key_outlined,
              title: 'No active tenancy yet',
              message: 'After a confirmed booking is checked in by the landlord, your tenancy will appear here.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _tenancies;
            },
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: rows.length,
              itemBuilder: (context, index) {
                final tenancy = rows[index];
                final active = tenancy.status == 'active';
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${tenancy.propertyTitle} • ${tenancy.unitName}',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        Text('Status: ${tenancy.status.replaceAll('_', ' ')}'),
                        Text('Started: ${DateFormat.yMMMd().format(tenancy.startDate)}'),
                        if (tenancy.expectedMoveOut != null)
                          Text('Move-out: ${DateFormat.yMMMd().format(tenancy.expectedMoveOut!)}'),
                        if (tenancy.status == 'notice_given')
                          Text(
                            tenancy.allowReadvertise
                                ? 'Future re-advertising is enabled.'
                                : 'Future re-advertising is disabled.',
                          ),
                        if (active) ...[
                          const SizedBox(height: 14),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton.icon(
                              onPressed: _busyId == null ? () => _giveNotice(tenancy) : null,
                              icon: _busyId == tenancy.id
                                  ? const SizedBox.square(
                                      dimension: 18,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.event_busy_outlined),
                              label: const Text('Give notice to vacate'),
                            ),
                          ),
                        ],
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
}

class LandlordOccupancyScreen extends StatefulWidget {
  const LandlordOccupancyScreen({
    super.key,
    required this.bookingRepository,
    required this.tenancyRepository,
  });

  final ApiBookingRepository bookingRepository;
  final ApiTenancyRepository tenancyRepository;

  @override
  State<LandlordOccupancyScreen> createState() => _LandlordOccupancyScreenState();
}

class _LandlordOccupancyScreenState extends State<LandlordOccupancyScreen> {
  late Future<_OccupancyData> _data;
  String? _busyId;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _data = _load();

  Future<_OccupancyData> _load() async {
    final bookings = await widget.bookingRepository.listLandlord();
    final tenancies = await widget.tenancyRepository.listLandlord();
    return _OccupancyData(bookings: bookings, tenancies: tenancies);
  }

  Future<void> _activate(BookingSummary booking) async {
    setState(() => _busyId = booking.id);
    try {
      await widget.tenancyRepository.activate(booking.id);
      if (mounted) setState(_reload);
    } on TenancyException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _end(TenancySummary tenancy) async {
    setState(() => _busyId = tenancy.id);
    try {
      await widget.tenancyRepository.end(tenancy.id);
      if (mounted) setState(_reload);
    } on TenancyException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  Future<void> _inspection(TenancySummary tenancy) async {
    setState(() => _busyId = tenancy.id);
    try {
      await widget.tenancyRepository.completeInspection(tenancy.id);
      if (mounted) setState(_reload);
    } on TenancyException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Occupancy & notices')),
      body: FutureBuilder<_OccupancyData>(
        future: _data,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _Message(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load occupancy',
              message: snapshot.error.toString(),
              action: FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            );
          }
          final data = snapshot.data!;
          final activatedBookingIds = data.tenancies.map((item) => item.bookingId).toSet();
          final moveIns = data.bookings
              .where((item) => item.status == 'confirmed' && !activatedBookingIds.contains(item.id))
              .toList();
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _data;
            },
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text('Confirmed move-ins', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                if (moveIns.isEmpty)
                  const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('No confirmed bookings awaiting check-in.'))),
                for (final booking in moveIns)
                  Card(
                    child: ListTile(
                      title: Text('${booking.propertyTitle} • ${booking.unitName}'),
                      subtitle: Text('Move in ${DateFormat.yMMMd().format(booking.moveInDate)}'),
                      trailing: FilledButton(
                        onPressed: _busyId == null ? () => _activate(booking) : null,
                        child: _busyId == booking.id
                            ? const SizedBox.square(dimension: 18, child: CircularProgressIndicator(strokeWidth: 2))
                            : const Text('Check in'),
                      ),
                    ),
                  ),
                const SizedBox(height: 20),
                Text('Tenancies', style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                if (data.tenancies.isEmpty)
                  const Card(child: Padding(padding: EdgeInsets.all(16), child: Text('No tenancy records yet.'))),
                for (final tenancy in data.tenancies)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${tenancy.propertyTitle} • ${tenancy.unitName}',
                            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                          ),
                          Text('Tenant: ${tenancy.tenantName}'),
                          Text('Status: ${tenancy.status.replaceAll('_', ' ')}'),
                          if (tenancy.expectedMoveOut != null)
                            Text('Expected move-out: ${DateFormat.yMMMd().format(tenancy.expectedMoveOut!)}'),
                          const SizedBox(height: 10),
                          if (tenancy.status == 'active' || tenancy.status == 'notice_given')
                            OutlinedButton.icon(
                              onPressed: _busyId == null ? () => _end(tenancy) : null,
                              icon: const Icon(Icons.logout_rounded),
                              label: const Text('Record move-out'),
                            )
                          else if (tenancy.status == 'ended')
                            OutlinedButton.icon(
                              onPressed: _busyId == null ? () => _inspection(tenancy) : null,
                              icon: const Icon(Icons.fact_check_outlined),
                              label: const Text('Complete inspection / release unit'),
                            ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _OccupancyData {
  const _OccupancyData({required this.bookings, required this.tenancies});

  final List<BookingSummary> bookings;
  final List<TenancySummary> tenancies;
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.title, required this.message, this.action});

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
            const SizedBox(height: 12),
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
