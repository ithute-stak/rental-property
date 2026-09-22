import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';

class FeedScreen extends StatelessWidget {
  const FeedScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Find your next home'),
            Text('Maseru, Lesotho', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w400)),
          ],
        ),
        actions: [
          IconButton(onPressed: () {}, icon: const Icon(Icons.notifications_none_rounded)),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: SearchBar(
              hintText: 'Area, town, landmark or property',
              leading: const Icon(Icons.search_rounded),
              trailing: [IconButton(onPressed: () {}, icon: const Icon(Icons.tune_rounded))],
            ),
          ),
          Expanded(
            child: BlocBuilder<FeedBloc, FeedState>(
              builder: (context, state) => switch (state) {
                FeedLoading() => const Center(child: CircularProgressIndicator()),
                FeedLoaded(:final properties) => RefreshIndicator(
                    onRefresh: () async => context.read<FeedBloc>().add(const FeedRequested()),
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                      itemCount: properties.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 14),
                      itemBuilder: (_, index) => _PropertyCard(property: properties[index]),
                    ),
                  ),
                FeedEmpty() => const Center(child: Text('No available properties yet.')),
                FeedFailure(:final message) => Center(child: Text(message)),
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _PropertyCard extends StatelessWidget {
  const _PropertyCard({required this.property});

  final PropertySummary property;

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'M ', decimalDigits: 0);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {},
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              height: 190,
              width: double.infinity,
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              child: const Center(child: Icon(Icons.home_work_outlined, size: 54)),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(property.title, style: Theme.of(context).textTheme.titleMedium)),
                      const Icon(Icons.favorite_border_rounded),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('${property.area}, ${property.town}'),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _Chip(icon: Icons.meeting_room_outlined, label: '${property.availableRooms} available'),
                      _Chip(icon: Icons.shield_outlined, label: property.securityLevel),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    '${currency.format(property.monthlyRent)} / month',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(avatar: Icon(icon, size: 16), label: Text(label));
  }
}
