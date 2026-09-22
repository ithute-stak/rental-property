import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/notifications/data/api_notification_repository.dart';
import 'package:rental_property/features/realtime/data/realtime_client.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, required this.repository});

  final ApiNotificationRepository repository;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<List<AppNotification>> _notifications;
  StreamSubscription<RealtimeEvent>? _realtimeSubscription;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _realtimeSubscription ??= context.read<RealtimeClient>().events.listen((event) {
      if (event.type == 'notification.created' && mounted) {
        setState(_reload);
      }
    });
  }

  @override
  void dispose() {
    unawaited(_realtimeSubscription?.cancel());
    super.dispose();
  }

  void _reload() => _notifications = widget.repository.list();

  Future<void> _read(AppNotification notification) async {
    if (notification.isRead) return;
    try {
      await widget.repository.markRead(notification.id);
      if (mounted) setState(_reload);
    } on NotificationException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: FutureBuilder<List<AppNotification>>(
        future: _notifications,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.notifications_off_outlined, size: 52),
                    const SizedBox(height: 12),
                    Text(snapshot.error.toString(), textAlign: TextAlign.center),
                    const SizedBox(height: 12),
                    FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
                  ],
                ),
              ),
            );
          }
          final notifications = snapshot.data ?? const [];
          if (notifications.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.notifications_none_rounded, size: 56),
                    SizedBox(height: 12),
                    Text('No notifications yet'),
                    SizedBox(height: 6),
                    Text(
                      'Booking, payment and property updates will appear here.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _notifications;
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: notifications.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, index) {
                final item = notifications[index];
                return Card(
                  child: ListTile(
                    onTap: () => _read(item),
                    leading: CircleAvatar(
                      child: Icon(item.isRead ? Icons.notifications_none_rounded : Icons.notifications_active_rounded),
                    ),
                    title: Text(
                      item.title,
                      style: TextStyle(fontWeight: item.isRead ? FontWeight.w500 : FontWeight.w800),
                    ),
                    subtitle: Text(
                      '${item.body}\n${DateFormat.yMMMd().add_jm().format(item.createdAt.toLocal())}',
                    ),
                    isThreeLine: true,
                    trailing: item.isRead
                        ? null
                        : Icon(Icons.circle, size: 10, color: Theme.of(context).colorScheme.primary),
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
