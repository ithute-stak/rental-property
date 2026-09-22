import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/feed/data/api_feed_repository.dart';
import 'package:rental_property/features/feed/domain/feed_repository.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';
import 'package:rental_property/features/feed/presentation/feed_screen.dart';

void main() {
  runApp(RentalPropertyApp(feedRepository: ApiFeedRepository.fromEnvironment()));
}

class RentalPropertyApp extends StatelessWidget {
  const RentalPropertyApp({super.key, required this.feedRepository});

  final FeedRepository feedRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
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
      ),
      home: BlocProvider(
        create: (_) => FeedBloc(feedRepository)..add(const FeedRequested()),
        child: const FeedScreen(),
      ),
    );
  }
}
