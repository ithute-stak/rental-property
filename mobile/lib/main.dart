import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';
import 'package:rental_property/features/feed/presentation/feed_screen.dart';

void main() {
  runApp(const RentalPropertyApp());
}

class RentalPropertyApp extends StatelessWidget {
  const RentalPropertyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Rental Property',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1F6F5F)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF6F7F5),
      ),
      home: BlocProvider(
        create: (_) => FeedBloc()..add(const FeedRequested()),
        child: const FeedScreen(),
      ),
    );
  }
}
