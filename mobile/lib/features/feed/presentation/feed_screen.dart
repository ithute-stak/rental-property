import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/auth/presentation/account_screen.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';
import 'package:rental_property/features/booking/data/api_booking_repository.dart';
import 'package:rental_property/features/booking/presentation/booking_screens.dart';
import 'package:rental_property/features/engagement/data/api_engagement_repository.dart';
import 'package:rental_property/features/engagement/presentation/engagement_screens.dart';
import 'package:rental_property/features/feed/domain/feed_filters.dart';
import 'package:rental_property/features/feed/domain/property_summary.dart';
import 'package:rental_property/features/feed/presentation/bloc/feed_bloc.dart';
import 'package:rental_property/features/feed/presentation/feed_filter_sheet.dart';
import 'package:rental_property/features/messaging/data/api_messaging_repository.dart';
import 'package:rental_property/features/messaging/presentation/messaging_screens.dart';
import 'package:rental_property/features/notifications/data/api_notification_repository.dart';
import 'package:rental_property/features/notifications/presentation/notifications_screen.dart';

class FeedScreen extends StatelessWidget {
  const FeedScreen({super.key});

  Future<void> _openFilters(BuildContext context) async {
    final bloc = context.read<FeedBloc>();
    final filters = await showModalBottomSheet<FeedFilters>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => FeedFilterSheet(initial: bloc.filters),
    );
    if (filters != null && context.mounted) {
      bloc.add(FeedRequested(filters: filters));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: const Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Find your next home'),
            Text('Maseru, Lesotho', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w400)),
          ],
        ),
        actions: [
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) => IconButton(
              tooltip: 'Saved homes',
              onPressed: () {
                if (state is SessionAuthenticated) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) => SavedHomesScreen(
                        repository: ApiEngagementRepository.fromEnvironment(),
                      ),
                    ),
                  );
                } else {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(builder: (_) => const AccountScreen()),
                  );
                }
              },
              icon: const Icon(Icons.favorite_border_rounded),
            ),
          ),
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) => IconButton(
              tooltip: 'My viewing requests',
              onPressed: () {
                if (state is SessionAuthenticated && !state.user.isLandlord && !state.user.isAdmin) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) => MyViewingsScreen(
                        repository: ApiEngagementRepository.fromEnvironment(),
                      ),
                    ),
                  );
                } else if (state is! SessionAuthenticated) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(builder: (_) => const AccountScreen()),
                  );
                }
              },
              icon: const Icon(Icons.visibility_outlined),
            ),
          ),
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) => IconButton(
              tooltip: 'Messages',
              onPressed: () {
                if (state is SessionAuthenticated && !state.user.isAdmin) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) => ConversationsScreen(
                        repository: ApiMessagingRepository.fromEnvironment(),
                      ),
                    ),
                  );
                } else if (state is! SessionAuthenticated) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(builder: (_) => const AccountScreen()),
                  );
                }
              },
              icon: const Icon(Icons.forum_outlined),
            ),
          ),
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) => IconButton(
              tooltip: 'Notifications',
              onPressed: () {
                if (state is SessionAuthenticated) {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(
                      builder: (_) => NotificationsScreen(
                        repository: ApiNotificationRepository.fromEnvironment(),
                      ),
                    ),
                  );
                } else {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute(builder: (_) => const AccountScreen()),
                  );
                }
              },
              icon: const Icon(Icons.notifications_none_rounded),
            ),
          ),
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) => IconButton(
              tooltip: state is SessionAuthenticated ? 'My account' : 'Sign in',
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => const AccountScreen()),
                );
              },
              icon: Icon(
                state is SessionAuthenticated
                    ? Icons.account_circle_rounded
                    : Icons.person_outline_rounded,
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          const _MosalaBrandHeader(),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: SearchBar(
              hintText: 'Area, town, landmark or property',
              leading: const Icon(Icons.search_rounded),
              onSubmitted: (value) {
                context.read<FeedBloc>().add(FeedRequested(query: value));
              },
              trailing: [
                BlocBuilder<FeedBloc, FeedState>(
                  builder: (context, _) {
                    final hasFilters = !context.read<FeedBloc>().filters.isEmpty;
                    return Badge(
                      isLabelVisible: hasFilters,
                      child: IconButton(
                        tooltip: 'Search filters',
                        onPressed: () => _openFilters(context),
                        icon: const Icon(Icons.tune_rounded),
                      ),
                    );
                  },
                ),
              ],
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
                      separatorBuilder: (_, _) => const SizedBox(height: 14),
                      itemBuilder: (_, index) => _PropertyCard(property: properties[index]),
                    ),
                  ),
                FeedEmpty() => RefreshIndicator(
                    onRefresh: () async => context.read<FeedBloc>().add(const FeedRequested()),
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: const [
                        SizedBox(height: 120),
                        Icon(Icons.home_work_outlined, size: 48),
                        SizedBox(height: 12),
                        Center(child: Text('No available properties match your search.')),
                      ],
                    ),
                  ),
                FeedFailure(:final message) => Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.cloud_off_outlined, size: 48),
                          const SizedBox(height: 12),
                          Text(message, textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          FilledButton.icon(
                            onPressed: () => context.read<FeedBloc>().add(const FeedRequested()),
                            icon: const Icon(Icons.refresh_rounded),
                            label: const Text('Try again'),
                          ),
                        ],
                      ),
                    ),
                  ),
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _MosalaBrandHeader extends StatelessWidget {
  const _MosalaBrandHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        children: [
          Semantics(
            label: 'Mosala Advertising and Marketing Agency logo',
            image: true,
            child: Image.asset(
              'assets/branding/mosala_logo.webp',
              height: 122,
              fit: BoxFit.contain,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Rental Property Marketplace',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 2),
          Text(
            'Built by Ithute Digital Solutions',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
          ),
        ],
      ),
    );
  }
}

class _PropertyCard extends StatefulWidget {
  const _PropertyCard({required this.property});

  final PropertySummary property;

  @override
  State<_PropertyCard> createState() => _PropertyCardState();
}

class _PropertyCardState extends State<_PropertyCard> {
  bool _saved = false;
  bool _saving = false;
  bool _openingMessage = false;

  PropertySummary get property => widget.property;

  Future<bool> _requireSeekerSession() async {
    final session = context.read<SessionCubit>().state;
    if (session is SessionAuthenticated && !session.user.isLandlord && !session.user.isAdmin) {
      return true;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute(builder: (_) => const AccountScreen()),
    );
    if (!mounted) return false;
    final restored = context.read<SessionCubit>().state;
    return restored is SessionAuthenticated && !restored.user.isLandlord && !restored.user.isAdmin;
  }

  Future<void> _toggleSaved() async {
    if (_saving || !await _requireSeekerSession()) return;
    setState(() => _saving = true);
    try {
      final repository = ApiEngagementRepository.fromEnvironment();
      if (_saved) {
        await repository.unsaveProperty(property.id);
      } else {
        await repository.saveProperty(property.id);
      }
      if (!mounted) return;
      setState(() => _saved = !_saved);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_saved ? 'Home saved.' : 'Home removed from saved homes.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _requestViewing() async {
    if (!await _requireSeekerSession() || !mounted) return;
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => RequestViewingScreen(
          repository: ApiEngagementRepository.fromEnvironment(),
          propertyId: property.id,
          propertyTitle: property.title,
        ),
      ),
    );
  }

  Future<void> _messageLandlord() async {
    if (_openingMessage || !await _requireSeekerSession()) return;
    setState(() => _openingMessage = true);
    final repository = ApiMessagingRepository.fromEnvironment();
    try {
      final conversation = await repository.startConversation(property.id);
      if (!mounted) return;
      await Navigator.of(context).push<void>(
        MaterialPageRoute(
          builder: (_) => ChatScreen(
            conversation: conversation,
            repository: repository,
          ),
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
    } finally {
      if (mounted) setState(() => _openingMessage = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currency = NumberFormat.currency(symbol: 'M ', decimalDigits: 0);

    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.of(context).push<void>(
            MaterialPageRoute(
              builder: (_) => PropertyBookingScreen(
                property: property,
                repository: ApiBookingRepository.fromEnvironment(),
              ),
            ),
          );
        },
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              height: 190,
              width: double.infinity,
              child: property.imageUrl.isEmpty
                  ? ColoredBox(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      child: const Center(child: Icon(Icons.home_work_outlined, size: 54)),
                    )
                  : CachedNetworkImage(
                      imageUrl: property.imageUrl,
                      fit: BoxFit.cover,
                      placeholder: (_, _) => const Center(child: CircularProgressIndicator()),
                      errorWidget: (_, _, _) => const Center(child: Icon(Icons.broken_image_outlined)),
                    ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(child: Text(property.title, style: Theme.of(context).textTheme.titleMedium)),
                      IconButton(
                        tooltip: _saved ? 'Remove saved home' : 'Save home',
                        onPressed: _saving ? null : _toggleSaved,
                        icon: Icon(_saved ? Icons.favorite_rounded : Icons.favorite_border_rounded),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Icon(Icons.location_on_outlined, size: 18),
                      const SizedBox(width: 4),
                      Expanded(child: Text('${property.area}, ${property.town}')),
                    ],
                  ),
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
                    'From ${currency.format(property.monthlyRent)} / month',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _openingMessage ? null : _messageLandlord,
                          icon: const Icon(Icons.chat_bubble_outline_rounded),
                          label: const Text('Message'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _requestViewing,
                          icon: const Icon(Icons.visibility_outlined),
                          label: const Text('View'),
                        ),
                      ),
                    ],
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
