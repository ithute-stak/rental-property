import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:rental_property/features/feed/domain/feed_filters.dart';

class FeedFilterSheet extends StatefulWidget {
  const FeedFilterSheet({super.key, required this.initial});

  final FeedFilters initial;

  @override
  State<FeedFilterSheet> createState() => _FeedFilterSheetState();
}

class _FeedFilterSheetState extends State<FeedFilterSheet> {
  late final TextEditingController _district;
  late final TextEditingController _town;
  late final TextEditingController _area;
  late final TextEditingController _minRent;
  late final TextEditingController _maxRent;
  LatLng? _pin;
  late double _radiusKm;

  static const _maseru = LatLng(-29.3151, 27.4869);

  @override
  void initState() {
    super.initState();
    _district = TextEditingController(text: widget.initial.district);
    _town = TextEditingController(text: widget.initial.town);
    _area = TextEditingController(text: widget.initial.area);
    _minRent = TextEditingController(
      text: widget.initial.minRent?.toStringAsFixed(0) ?? '',
    );
    _maxRent = TextEditingController(
      text: widget.initial.maxRent?.toStringAsFixed(0) ?? '',
    );
    _pin = widget.initial.hasLocation
        ? LatLng(widget.initial.latitude!, widget.initial.longitude!)
        : null;
    _radiusKm = widget.initial.radiusKm;
  }

  @override
  void dispose() {
    _district.dispose();
    _town.dispose();
    _area.dispose();
    _minRent.dispose();
    _maxRent.dispose();
    super.dispose();
  }

  FeedFilters _buildFilters() {
    final minRent = double.tryParse(_minRent.text.trim());
    final maxRent = double.tryParse(_maxRent.text.trim());
    return FeedFilters(
      district: _district.text.trim(),
      town: _town.text.trim(),
      area: _area.text.trim(),
      minRent: minRent,
      maxRent: maxRent,
      latitude: _pin?.latitude,
      longitude: _pin?.longitude,
      radiusKm: _radiusKm,
    );
  }

  void _apply() {
    final filters = _buildFilters();
    if (filters.minRent != null &&
        filters.maxRent != null &&
        filters.minRent! > filters.maxRent!) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Minimum rent cannot be greater than maximum rent.')),
      );
      return;
    }
    Navigator.of(context).pop(filters);
  }

  @override
  Widget build(BuildContext context) {
    final initialTarget = _pin ?? _maseru;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 12,
          bottom: MediaQuery.viewInsetsOf(context).bottom + 20,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Text(
                    'Search filters',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const Spacer(),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(const FeedFilters()),
                    child: const Text('Reset'),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _district,
                decoration: const InputDecoration(
                  labelText: 'District',
                  prefixIcon: Icon(Icons.map_outlined),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _town,
                decoration: const InputDecoration(
                  labelText: 'Town',
                  prefixIcon: Icon(Icons.location_city_outlined),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _area,
                decoration: const InputDecoration(
                  labelText: 'Area / suburb / landmark',
                  prefixIcon: Icon(Icons.place_outlined),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _minRent,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Min rent',
                        prefixText: 'M ',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextField(
                      controller: _maxRent,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Max rent',
                        prefixText: 'M ',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'Search around a map pin',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              const Text(
                'Tap the map to choose a centre point. This does not require your phone\'s precise location.',
              ),
              const SizedBox(height: 10),
              ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: SizedBox(
                  height: 240,
                  child: GoogleMap(
                    initialCameraPosition: CameraPosition(target: initialTarget, zoom: 12),
                    myLocationButtonEnabled: false,
                    myLocationEnabled: false,
                    zoomControlsEnabled: false,
                    onTap: (point) => setState(() => _pin = point),
                    markers: {
                      if (_pin != null)
                        Marker(
                          markerId: const MarkerId('search-centre'),
                          position: _pin!,
                        ),
                    },
                  ),
                ),
              ),
              if (_pin != null) ...[
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: Text('Radius: ${_radiusKm.toStringAsFixed(0)} km'),
                    ),
                    TextButton.icon(
                      onPressed: () => setState(() => _pin = null),
                      icon: const Icon(Icons.location_off_outlined),
                      label: const Text('Clear pin'),
                    ),
                  ],
                ),
                Slider(
                  value: _radiusKm,
                  min: 1,
                  max: 100,
                  divisions: 99,
                  label: '${_radiusKm.toStringAsFixed(0)} km',
                  onChanged: (value) => setState(() => _radiusKm = value),
                ),
              ],
              const SizedBox(height: 18),
              FilledButton.icon(
                onPressed: _apply,
                icon: const Icon(Icons.search_rounded),
                label: const Padding(
                  padding: EdgeInsets.symmetric(vertical: 14),
                  child: Text('Apply filters'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
