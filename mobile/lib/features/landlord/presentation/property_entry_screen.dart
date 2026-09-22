import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:rental_property/features/landlord/data/api_landlord_property_repository.dart';

class PropertyEntryScreen extends StatefulWidget {
  const PropertyEntryScreen({super.key, required this.repository});

  final ApiLandlordPropertyRepository repository;

  @override
  State<PropertyEntryScreen> createState() => _PropertyEntryScreenState();
}

class _PropertyEntryScreenState extends State<PropertyEntryScreen> {
  static const _maseru = LatLng(-29.3158, 27.4869);

  final _formKey = GlobalKey<FormState>();
  final _title = TextEditingController();
  final _description = TextEditingController();
  final _address = TextEditingController();
  final _district = TextEditingController(text: 'Maseru');
  final _town = TextEditingController(text: 'Maseru');
  final _area = TextEditingController();
  final _rooms = TextEditingController(text: '1');
  final _unitName = TextEditingController(text: 'Room 1');
  final _rent = TextEditingController();
  final _deposit = TextEditingController(text: '0');

  String _propertyType = 'rooms';
  String _securityLevel = 'standard';
  LatLng _pin = _maseru;
  bool _saving = false;
  bool _submitForVerification = true;
  bool _perimeterWall = false;
  bool _securityGate = false;
  bool _burglarBars = false;
  bool _cctv = false;
  bool _outdoorLighting = false;

  @override
  void dispose() {
    for (final controller in [
      _title,
      _description,
      _address,
      _district,
      _town,
      _area,
      _rooms,
      _unitName,
      _rent,
      _deposit,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Add rental property')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Property details', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            TextFormField(
              controller: _title,
              decoration: const InputDecoration(labelText: 'Property title', border: OutlineInputBorder()),
              validator: _required,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Description', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _propertyType,
              decoration: const InputDecoration(labelText: 'Property type', border: OutlineInputBorder()),
              items: const [
                DropdownMenuItem(value: 'rooms', child: Text('Rooms / compound')),
                DropdownMenuItem(value: 'house', child: Text('House')),
                DropdownMenuItem(value: 'apartment', child: Text('Apartment')),
                DropdownMenuItem(value: 'student_accommodation', child: Text('Student accommodation')),
              ],
              onChanged: (value) => setState(() => _propertyType = value ?? 'rooms'),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _address,
              decoration: const InputDecoration(labelText: 'Physical address', border: OutlineInputBorder()),
              validator: _required,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _district,
                    decoration: const InputDecoration(labelText: 'District', border: OutlineInputBorder()),
                    validator: _required,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _town,
                    decoration: const InputDecoration(labelText: 'Town', border: OutlineInputBorder()),
                    validator: _required,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _area,
              decoration: const InputDecoration(labelText: 'Area / suburb', border: OutlineInputBorder()),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _rooms,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Total rooms / units', border: OutlineInputBorder()),
              validator: (value) {
                final parsed = int.tryParse(value ?? '');
                return parsed == null || parsed < 1 ? 'Enter at least 1 room' : null;
              },
            ),
            const SizedBox(height: 20),
            Text('Pin the property location', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            SizedBox(
              height: 260,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(16),
                child: GoogleMap(
                  initialCameraPosition: const CameraPosition(target: _maseru, zoom: 13),
                  markers: {
                    Marker(markerId: const MarkerId('property'), position: _pin),
                  },
                  onTap: (position) => setState(() => _pin = position),
                  myLocationButtonEnabled: false,
                  zoomControlsEnabled: false,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Selected: ${_pin.latitude.toStringAsFixed(6)}, ${_pin.longitude.toStringAsFixed(6)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 20),
            Text('Security', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _securityLevel,
              decoration: const InputDecoration(labelText: 'Security level', border: OutlineInputBorder()),
              items: const [
                DropdownMenuItem(value: 'basic', child: Text('Basic')),
                DropdownMenuItem(value: 'standard', child: Text('Standard')),
                DropdownMenuItem(value: 'high', child: Text('High')),
              ],
              onChanged: (value) => setState(() => _securityLevel = value ?? 'standard'),
            ),
            CheckboxListTile(
              value: _perimeterWall,
              onChanged: (value) => setState(() => _perimeterWall = value ?? false),
              title: const Text('Perimeter wall / fence'),
              contentPadding: EdgeInsets.zero,
            ),
            CheckboxListTile(
              value: _securityGate,
              onChanged: (value) => setState(() => _securityGate = value ?? false),
              title: const Text('Security gate'),
              contentPadding: EdgeInsets.zero,
            ),
            CheckboxListTile(
              value: _burglarBars,
              onChanged: (value) => setState(() => _burglarBars = value ?? false),
              title: const Text('Burglar bars'),
              contentPadding: EdgeInsets.zero,
            ),
            CheckboxListTile(
              value: _cctv,
              onChanged: (value) => setState(() => _cctv = value ?? false),
              title: const Text('CCTV'),
              contentPadding: EdgeInsets.zero,
            ),
            CheckboxListTile(
              value: _outdoorLighting,
              onChanged: (value) => setState(() => _outdoorLighting = value ?? false),
              title: const Text('Outdoor lighting'),
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 20),
            Text('First rental unit', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              'Create at least one room/unit now. More units can be added from the property workspace later.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _unitName,
              decoration: const InputDecoration(labelText: 'Unit name', border: OutlineInputBorder()),
              validator: _required,
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _rent,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Monthly rent (M)', border: OutlineInputBorder()),
                    validator: _money,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _deposit,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Deposit (M)', border: OutlineInputBorder()),
                    validator: _money,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              value: _submitForVerification,
              onChanged: (value) => setState(() => _submitForVerification = value),
              title: const Text('Submit for admin verification after saving'),
              subtitle: const Text('This requires an approved landlord verification profile.'),
              contentPadding: EdgeInsets.zero,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_outlined),
              label: Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: Text(_saving ? 'Saving…' : 'Save property'),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  String? _required(String? value) => (value?.trim().isEmpty ?? true) ? 'Required' : null;

  String? _money(String? value) {
    final parsed = double.tryParse(value ?? '');
    return parsed == null || parsed < 0 ? 'Enter a valid amount' : null;
  }

  Future<void> _save() async {
    if (_saving || !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _saving = true);
    try {
      final propertyId = await widget.repository.createProperty(
        title: _title.text,
        description: _description.text,
        propertyType: _propertyType,
        physicalAddress: _address.text,
        district: _district.text,
        town: _town.text,
        area: _area.text,
        latitude: _pin.latitude,
        longitude: _pin.longitude,
        totalRooms: int.parse(_rooms.text),
        securityLevel: _securityLevel,
        securityFeatures: {
          'perimeter_wall': _perimeterWall,
          'security_gate': _securityGate,
          'burglar_bars': _burglarBars,
          'cctv': _cctv,
          'outdoor_lighting': _outdoorLighting,
        },
      );
      await widget.repository.createUnit(
        propertyId: propertyId,
        name: _unitName.text,
        monthlyRent: double.parse(_rent.text),
        deposit: double.parse(_deposit.text),
      );
      if (_submitForVerification) {
        await widget.repository.submitProperty(propertyId);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _submitForVerification
                ? 'Property saved and submitted for verification.'
                : 'Property saved as a draft.',
          ),
        ),
      );
      Navigator.of(context).pop(true);
    } on LandlordPropertyException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
