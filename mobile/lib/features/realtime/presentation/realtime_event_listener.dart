import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';
import 'package:rental_property/features/realtime/data/realtime_event_service.dart';

class RealtimeEventListener extends StatefulWidget {
  const RealtimeEventListener({super.key, required this.child});

  final Widget child;

  @override
  State<RealtimeEventListener> createState() => _RealtimeEventListenerState();
}

class _RealtimeEventListenerState extends State<RealtimeEventListener> {
  late final RealtimeEventService _service;
  StreamSubscription<RealtimeNotificationEvent>? _subscription;

  @override
  void initState() {
    super.initState();
    _service = RealtimeEventService();
    _subscription = _service.events.listen(_showNotification);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final state = context.read<SessionCubit>().state;
      if (state is SessionAuthenticated) {
        _service.start();
      }
    });
  }

  void _showNotification(RealtimeNotificationEvent event) {
    if (!mounted) return;
    final messenger = ScaffoldMessenger.maybeOf(context);
    messenger?.hideCurrentSnackBar();
    messenger?.showSnackBar(
      SnackBar(
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(event.title, style: const TextStyle(fontWeight: FontWeight.w700)),
            if (event.body.isNotEmpty) Text(event.body),
          ],
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _onSessionState(SessionState state) async {
    if (state is SessionAuthenticated) {
      await _service.start();
    } else if (state is SessionGuest) {
      await _service.stop();
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<SessionCubit, SessionState>(
      listener: (_, state) => _onSessionState(state),
      child: widget.child,
    );
  }
}
