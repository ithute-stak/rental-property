import 'package:flutter/material.dart';
import 'package:rental_property/features/landlord/data/api_landlord_property_repository.dart';
import 'package:rental_property/features/landlord/data/api_property_media_repository.dart';
import 'package:rental_property/features/landlord/presentation/property_entry_screen.dart';
import 'package:rental_property/features/landlord/presentation/property_media_screen.dart';

class LandlordWorkspaceScreen extends StatefulWidget {
  const LandlordWorkspaceScreen({super.key, required this.repository});

  final ApiLandlordPropertyRepository repository;

  @override
  State<LandlordWorkspaceScreen> createState() => _LandlordWorkspaceScreenState();
}

class _LandlordWorkspaceScreenState extends State<LandlordWorkspaceScreen> {
  late Future<List<LandlordPropertySummary>> _properties;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _properties = widget.repository.listMine();
  }

  Future<void> _openCreate() async {
    final created = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => PropertyEntryScreen(repository: widget.repository),
      ),
    );
    if (created == true && mounted) {
      setState(_reload);
    }
  }

  Future<void> _openMedia(LandlordPropertySummary property) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => PropertyMediaScreen(
          property: property,
          repository: ApiPropertyMediaRepository.fromEnvironment(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Landlord workspace')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openCreate,
        icon: const Icon(Icons.add_home_work_outlined),
        label: const Text('Add property'),
      ),
      body: FutureBuilder<List<LandlordPropertySummary>>(
        future: _properties,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _MessageState(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load your properties',
              message: snapshot.error.toString(),
              actionLabel: 'Try again',
              onAction: () => setState(_reload),
            );
          }
          final properties = snapshot.data ?? const [];
          if (properties.isEmpty) {
            return _MessageState(
              icon: Icons.home_work_outlined,
              title: 'No properties yet',
              message: 'Add your first rental property, pin its location and create at least one rental unit.',
              actionLabel: 'Add property',
              onAction: _openCreate,
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _properties;
            },
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              itemCount: properties.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final property = properties[index];
                return Card(
                  child: ListTile(
                    onTap: () => _openMedia(property),
                    leading: const CircleAvatar(child: Icon(Icons.apartment_rounded)),
                    title: Text(property.title),
                    subtitle: Text(
                      '${property.town} • ${property.totalRooms} rooms\nTap to view or manage property photos',
                    ),
                    isThreeLine: true,
                    trailing: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _StatusBadge(status: property.status),
                        const SizedBox(width: 4),
                        const Icon(Icons.chevron_right_rounded),
                      ],
                    ),
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

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final label = status.replaceAll('_', ' ');
    return Chip(label: Text(label));
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.icon,
    required this.title,
    required this.message,
    required this.actionLabel,
    required this.onAction,
  });

  final IconData icon;
  final String title;
  final String message;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 54),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 18),
            FilledButton(onPressed: onAction, child: Text(actionLabel)),
          ],
        ),
      ),
    );
  }
}
