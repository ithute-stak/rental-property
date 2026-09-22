import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/auth/data/api_auth_repository.dart';
import 'package:rental_property/features/auth/domain/auth_repository.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';
import 'package:rental_property/features/feed/data/api_feed_repository.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';
import 'package:rental_property/features/feed/presentation/feed_screen.dart';

void main() {
  runApp(
    RentalPropertyApp(
      feedRepository: ApiFeedRepository.fromEnvironment(),
      authRepository: ApiAuthRepository.fromEnvironment(),
    ),
  );
}

class RentalPropertyApp extends StatelessWidget {
  const RentalPropertyApp({
    super.key,
    required this.feedRepository,
    required this.authRepository,
  });

  final FeedRepository feedRepository;
  final AuthRepository authRepository;

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [
        BlocProvider(create: (_) => FeedBloc(feedRepository)..add(const FeedRequested())),
        BlocProvider(create: (_) => SessionCubit(authRepository)..restore()),
      ],
      child: MaterialApp(
        title: 'Mosala Rentals',
        debugShowCheckedModeBanner: false,
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
