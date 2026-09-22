import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/auth/data/api_auth_repository.dart';
import 'package:rental_property/features/auth/domain/auth_repository.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';
import 'package:rental_property/features/feed/data/api_feed_repository.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';
import 'package:rental_property/features/feed/presentation/feed_screen.dart';
import 'package:rental_property/features/realtime/data/realtime_client.dart';

void main() {
  runApp(
    RentalPropertyApp(
      feedRepository: ApiFeedRepository.fromEnvironment(),
      authRepository: ApiAuthRepository.fromEnvironment(),
      realtimeClient: RealtimeClient.fromEnvironment(),
    ),
  );
}

class RentalPropertyApp extends StatelessWidget {
  const RentalPropertyApp({
    super.key,
    required this.feedRepository,
    required this.authRepository,
    required this.realtimeClient,
  });

  final FeedRepository feedRepository;
  final AuthRepository authRepository;
  final RealtimeClient realtimeClient;

  @override
  Widget build(BuildContext context) {
    return RepositoryProvider<RealtimeClient>.value(
      value: realtimeClient,
      child: MultiBlocProvider(
        providers: [
          BlocProvider(create: (_) => FeedBloc(feedRepository)..add(const FeedRequested())),
          BlocProvider(create: (_) => SessionCubit(authRepository)..restore()),
        ],
        child: _AppShell(realtimeClient: realtimeClient),
      ),
    );
  }
}

class _AppShell extends StatefulWidget {
  const _AppShell({required this.realtimeClient});

  final RealtimeClient realtimeClient;

  @override
  State<_AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<_AppShell> {
  final GlobalKey<ScaffoldMessengerState> _messengerKey = GlobalKey<ScaffoldMessengerState>();
  StreamSubscription<RealtimeEvent>? _realtimeSubscription;

  @override
  void initState() {
    super.initState();
    _realtimeSubscription = widget.realtimeClient.events.listen(_onRealtimeEvent);
  }

  void _onRealtimeEvent(RealtimeEvent event) {
    if (event.type != 'notification.created') return;
    final notification = event.notification;
    if (notification == null) return;
    final title = notification['title']?.toString().trim() ?? '';
    final body = notification['body']?.toString().trim() ?? '';
    if (title.isEmpty && body.isEmpty) return;

    final text = title.isEmpty
        ? body
        : body.isEmpty
            ? title
            : '$title\n$body';
    _messengerKey.currentState
      ?..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(text)));
  }

  @override
  void dispose() {
    unawaited(_realtimeSubscription?.cancel());
    unawaited(widget.realtimeClient.dispose());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return BlocListener<SessionCubit, SessionState>(
      listener: (_, state) {
        if (state is SessionAuthenticated) {
          unawaited(widget.realtimeClient.start());
        } else if (state is SessionGuest) {
          unawaited(widget.realtimeClient.stop());
        }
      },
      child: MaterialApp(
        title: 'Mosala Rentals',
        debugShowCheckedModeBanner: false,
        scaffoldMessengerKey: _messengerKey,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: const Color(0xFF11B6C7),
            brightness: Brightness.light,
          ),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xFFF7F8F8),
          appBarTheme: const AppBarTheme(
            backgroundColor: Colors.white,
            foregroundColor: Colors.black,
            surfaceTintColor: Colors.transparent,
          ),
          inputDecorationTheme: const InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
          ),
        ),
        home: const FeedScreen(),
      ),
    );
  }
}
