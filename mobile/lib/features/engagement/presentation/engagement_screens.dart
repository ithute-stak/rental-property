import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/engagement/data/api_engagement_repository.dart';

class SavedHomesScreen extends StatefulWidget {
  const SavedHomesScreen({super.key, required this.repository});

  final ApiEngagementRepository repository;

  @override
  State<SavedHomesScreen> createState() => _SavedHomesScreenState();
}

class _SavedHomesScreenState extends State<SavedHomesScreen> {
  late Future<List<SavedHome>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _future = widget.repository.listSavedHomes();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Saved homes')),
      body: FutureBuilder<List<SavedHome>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _MessageState(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load saved homes',
              message: snapshot.error.toString(),
              actionLabel: 'Try again',
              onAction: () => setState(_reload),
            );
          }
          final homes = snapshot.data ?? const [];
          if (homes.isEmpty) {
            return const _MessageState(
              icon: Icons.favorite_border_rounded,
              title: 'No saved homes yet',
              message: 'Tap the heart on a rental listing to keep it here for later.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _future;
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: homes.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (_, index) {
                final home = homes[index];
                return Card(
                  clipBehavior: Clip.antiAlias,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        height: 160,
                        width: double.infinity,
                        child: home.imageUrl == null || home.imageUrl!.isEmpty
                            ? const Center(child: Icon(Icons.home_work_outlined, size: 48))
                            : CachedNetworkImage(
                                imageUrl: home.imageUrl!,
                                fit: BoxFit.cover,
                                errorWidget: (_, _, _) =>
                                    const Center(child: Icon(Icons.broken_image_outlined)),
                              ),
                      ),
                      ListTile(
                        title: Text(home.title),
                        subtitle: Text(
                          '${home.area ?? home.town}, ${home.town}\n'
                          '${home.availableRooms} available'
                          '${home.monthlyRent == null ? '' : ' • From M ${home.monthlyRent!.toStringAsFixed(0)}'}',
                        ),
                        isThreeLine: true,
                        trailing: IconButton(
                          tooltip: 'Remove from saved homes',
                          onPressed: () async {
                            await widget.repository.unsaveProperty(home.propertyId);
                            if (mounted) setState(_reload);
                          },
                          icon: const Icon(Icons.favorite_rounded),
                        ),
                      ),
                    ],
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

class RequestViewingScreen extends StatefulWidget {
  const RequestViewingScreen({
    super.key,
    required this.repository,
    required this.propertyId,
    required this.propertyTitle,
  });

  final ApiEngagementRepository repository;
  final String propertyId;
  final String propertyTitle;

  @override
  State<RequestViewingScreen> createState() => _RequestViewingScreenState();
}

class _RequestViewingScreenState extends State<RequestViewingScreen> {
  final _messageController = TextEditingController();
  DateTime? _when;
  bool _saving = false;

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _pickDateTime() async {
    final now = DateTime.now();
    final day = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 180)),
      initialDate: now.add(const Duration(days: 1)),
    );
    if (day == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: const TimeOfDay(hour: 10, minute: 0),
    );
    if (time == null) return;
    setState(() {
      _when = DateTime(day.year, day.month, day.day, time.hour, time.minute);
    });
  }

  Future<void> _submit() async {
    final when = _when;
    if (when == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Choose a preferred viewing date and time.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.repository.requestViewing(
        propertyId: widget.propertyId,
        preferredAt: when,
        message: _messageController.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Viewing request sent to the landlord.')),
      );
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final format = DateFormat('EEE, d MMM yyyy • HH:mm');
    return Scaffold(
      appBar: AppBar(title: const Text('Request viewing')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(widget.propertyTitle, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.event_outlined),
              title: Text(_when == null ? 'Choose preferred date and time' : format.format(_when!)),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: _pickDateTime,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _messageController,
            maxLines: 4,
            maxLength: 1000,
            decoration: const InputDecoration(
              labelText: 'Message to landlord (optional)',
              hintText: 'For example: I would like to see the room after work.',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: _saving ? null : _submit,
            icon: _saving
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send_outlined),
            label: const Text('Send viewing request'),
          ),
        ],
      ),
    );
  }
}

class MyViewingsScreen extends StatefulWidget {
  const MyViewingsScreen({super.key, required this.repository});

  final ApiEngagementRepository repository;

  @override
  State<MyViewingsScreen> createState() => _MyViewingsScreenState();
}

class _MyViewingsScreenState extends State<MyViewingsScreen> {
  late Future<List<ViewingItem>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _future = widget.repository.listMyViewings();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My viewing requests')),
      body: _ViewingList(
        future: _future,
        emptyMessage: 'You have not requested any property viewings yet.',
        onRefresh: () async {
          setState(_reload);
          await _future;
        },
        itemBuilder: (viewing) => _ViewingCard(
          viewing: viewing,
          trailing: viewing.status == 'pending' || viewing.status == 'rescheduled'
              ? TextButton(
                  onPressed: () async {
                    await widget.repository.cancelViewing(viewing.id);
                    if (mounted) setState(_reload);
                  },
                  child: const Text('Cancel'),
                )
              : null,
        ),
      ),
    );
  }
}

class LandlordViewingsScreen extends StatefulWidget {
  const LandlordViewingsScreen({super.key, required this.repository});

  final ApiEngagementRepository repository;

  @override
  State<LandlordViewingsScreen> createState() => _LandlordViewingsScreenState();
}

class _LandlordViewingsScreenState extends State<LandlordViewingsScreen> {
  late Future<List<ViewingItem>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _future = widget.repository.listLandlordViewings();

  Future<DateTime?> _schedulePicker(DateTime initial) async {
    final now = DateTime.now();
    final day = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 180)),
      initialDate: initial.isAfter(now) ? initial : now.add(const Duration(days: 1)),
    );
    if (day == null || !mounted) return null;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (time == null) return null;
    return DateTime(day.year, day.month, day.day, time.hour, time.minute);
  }

  Future<void> _decide(ViewingItem item, String decision) async {
    DateTime? scheduledAt;
    if (decision == 'accepted' || decision == 'rescheduled') {
      scheduledAt = await _schedulePicker(item.scheduledAt ?? item.preferredAt.toLocal());
      if (scheduledAt == null) return;
    }
    try {
      await widget.repository.decideViewing(
        viewingId: item.id,
        status: decision,
        scheduledAt: scheduledAt,
      );
      if (mounted) setState(_reload);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Viewing requests')),
      body: _ViewingList(
        future: _future,
        emptyMessage: 'There are no viewing requests for your properties.',
        onRefresh: () async {
          setState(_reload);
          await _future;
        },
        itemBuilder: (viewing) => _ViewingCard(
          viewing: viewing,
          trailing: viewing.status == 'pending' || viewing.status == 'rescheduled'
              ? PopupMenuButton<String>(
                  onSelected: (value) => _decide(viewing, value),
                  itemBuilder: (_) => const [
                    PopupMenuItem(value: 'accepted', child: Text('Accept')),
                    PopupMenuItem(value: 'rescheduled', child: Text('Propose new time')),
                    PopupMenuItem(value: 'declined', child: Text('Decline')),
                  ],
                )
              : null,
        ),
      ),
    );
  }
}

class _ViewingList extends StatelessWidget {
  const _ViewingList({
    required this.future,
    required this.emptyMessage,
    required this.onRefresh,
    required this.itemBuilder,
  });

  final Future<List<ViewingItem>> future;
  final String emptyMessage;
  final Future<void> Function() onRefresh;
  final Widget Function(ViewingItem) itemBuilder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<ViewingItem>>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return _MessageState(
            icon: Icons.cloud_off_outlined,
            title: 'Could not load viewing requests',
            message: snapshot.error.toString(),
          );
        }
        final items = snapshot.data ?? const [];
        if (items.isEmpty) {
          return _MessageState(
            icon: Icons.visibility_outlined,
            title: 'No viewing requests',
            message: emptyMessage,
          );
        }
        return RefreshIndicator(
          onRefresh: onRefresh,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (_, _) => const SizedBox(height: 10),
            itemBuilder: (_, index) => itemBuilder(items[index]),
          ),
        );
      },
    );
  }
}

class _ViewingCard extends StatelessWidget {
  const _ViewingCard({required this.viewing, this.trailing});

  final ViewingItem viewing;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final format = DateFormat('EEE, d MMM yyyy • HH:mm');
    final when = viewing.scheduledAt ?? viewing.preferredAt;
    return Card(
      child: ListTile(
        leading: const CircleAvatar(child: Icon(Icons.visibility_outlined)),
        title: Text(viewing.propertyTitle),
        subtitle: Text(
          '${viewing.requesterName}\n${format.format(when.toLocal())}\n${viewing.status.replaceAll('_', ' ')}'
          '${viewing.message == null ? '' : '\n${viewing.message}'}'
          '${viewing.responseNote == null ? '' : '\n${viewing.responseNote}'}',
        ),
        isThreeLine: true,
        trailing: trailing,
      ),
    );
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.icon,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 52),
            const SizedBox(height: 14),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 18),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
