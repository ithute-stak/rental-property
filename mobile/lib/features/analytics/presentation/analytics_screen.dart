import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/analytics/data/api_analytics_repository.dart';

class AnalyticsScreen extends StatefulWidget {
  const AnalyticsScreen({
    super.key,
    required this.repository,
    required this.isAdmin,
  });

  final ApiAnalyticsRepository repository;
  final bool isAdmin;

  @override
  State<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends State<AnalyticsScreen> {
  late Future<Object> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = widget.isAdmin
        ? widget.repository.adminOverview()
        : widget.repository.landlordOverview();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isAdmin ? 'Mosala analytics' : 'Portfolio analytics'),
      ),
      body: FutureBuilder<Object>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _ErrorState(
              message: snapshot.error.toString(),
              onRetry: () => setState(_reload),
            );
          }
          final data = snapshot.data;
          if (data is AdminAnalyticsOverview) {
            return _AdminAnalyticsBody(data: data, onRefresh: _refresh);
          }
          if (data is LandlordAnalyticsOverview) {
            return _LandlordAnalyticsBody(data: data, onRefresh: _refresh);
          }
          return const Center(child: Text('Analytics are unavailable.'));
        },
      ),
    );
  }

  Future<void> _refresh() async {
    setState(_reload);
    await _future;
  }
}

class _AdminAnalyticsBody extends StatelessWidget {
  const _AdminAnalyticsBody({required this.data, required this.onRefresh});

  final AdminAnalyticsOverview data;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 2);
    final cards = <_Metric>[
      _Metric('Active properties', '${data.activeProperties}', Icons.apartment_outlined),
      _Metric('Available units', '${data.availableUnits}', Icons.meeting_room_outlined),
      _Metric('Occupied units', '${data.occupiedUnits}', Icons.key_outlined),
      _Metric('Vacating soon', '${data.vacatingSoonUnits}', Icons.event_busy_outlined),
      _Metric('Active tenancies', '${data.activeTenancies}', Icons.people_outline),
      _Metric('Bookings this month', '${data.confirmedBookingsThisMonth}', Icons.event_available_outlined),
      _Metric('Booking funds confirmed', money.format(data.bookingFundsConfirmed), Icons.account_balance_wallet_outlined),
      _Metric('Advert revenue confirmed', money.format(data.advertRevenueConfirmed), Icons.payments_outlined),
      _Metric('Landlords to verify', '${data.pendingLandlordVerifications}', Icons.verified_user_outlined),
      _Metric('Properties to review', '${data.pendingPropertyReviews}', Icons.fact_check_outlined),
      _Metric('Booking payments to review', '${data.pendingBookingPaymentReviews}', Icons.receipt_long_outlined),
      _Metric('Advert payments to review', '${data.pendingAdvertPaymentReviews}', Icons.price_check_outlined),
      _Metric('Open viewings', '${data.openViewingRequests}', Icons.visibility_outlined),
      _Metric('Saved homes', '${data.savedHomes}', Icons.favorite_outline),
      _Metric('Conversations', '${data.conversations}', Icons.forum_outlined),
      _Metric('Messages', '${data.messages}', Icons.chat_bubble_outline_rounded),
    ];
    return _MetricGrid(
      header: 'Marketplace overview',
      subtitle: 'Live operational totals across Mosala Rentals.',
      metrics: cards,
      onRefresh: onRefresh,
    );
  }
}

class _LandlordAnalyticsBody extends StatelessWidget {
  const _LandlordAnalyticsBody({required this.data, required this.onRefresh});

  final LandlordAnalyticsOverview data;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final cards = <_Metric>[
      _Metric('Properties', '${data.properties}', Icons.apartment_outlined),
      _Metric('Active adverts', '${data.activeProperties}', Icons.campaign_outlined),
      _Metric('Total units', '${data.totalUnits}', Icons.grid_view_outlined),
      _Metric('Available', '${data.availableUnits}', Icons.meeting_room_outlined),
      _Metric('Occupied', '${data.occupiedUnits}', Icons.key_outlined),
      _Metric('Vacating soon', '${data.vacatingSoonUnits}', Icons.event_busy_outlined),
      _Metric('Active tenancies', '${data.activeTenancies}', Icons.people_outline),
      _Metric('Viewing requests', '${data.pendingViewings}', Icons.visibility_outlined),
      _Metric('Confirmed bookings', '${data.confirmedBookings}', Icons.event_available_outlined),
      _Metric('Saved by seekers', '${data.savedHomes}', Icons.favorite_outline),
      _Metric('Conversations', '${data.conversations}', Icons.forum_outlined),
      _Metric('Unread messages', '${data.unreadMessages}', Icons.mark_chat_unread_outlined),
    ];
    return _MetricGrid(
      header: 'Your rental portfolio',
      subtitle: 'Vacancy, occupancy, bookings and engagement across your properties.',
      metrics: cards,
      onRefresh: onRefresh,
    );
  }
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid({
    required this.header,
    required this.subtitle,
    required this.metrics,
    required this.onRefresh,
  });

  final String header;
  final String subtitle;
  final List<_Metric> metrics;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: CustomScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Image.asset('assets/branding/mosala_logo.webp', height: 82),
                  const SizedBox(height: 12),
                  Text(header, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(subtitle),
                ],
              ),
            ),
          ),
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverGrid(
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 260,
                mainAxisExtent: 142,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              delegate: SliverChildBuilderDelegate(
                (context, index) => _MetricCard(metric: metrics[index]),
                childCount: metrics.length,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric {
  const _Metric(this.label, this.value, this.icon);
  final String label;
  final String value;
  final IconData icon;
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.metric});
  final _Metric metric;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(metric.icon),
            const Spacer(),
            Text(
              metric.value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            Text(metric.label, maxLines: 2, overflow: TextOverflow.ellipsis),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 52),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: onRetry, child: const Text('Try again')),
          ],
        ),
      ),
    );
  }
}
