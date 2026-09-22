import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/landlord/data/api_landlord_account_repository.dart';
import 'package:rental_property/features/landlord/data/api_landlord_property_repository.dart';

class LandlordVerificationScreen extends StatefulWidget {
  const LandlordVerificationScreen({super.key, required this.repository});

  final ApiLandlordAccountRepository repository;

  @override
  State<LandlordVerificationScreen> createState() => _LandlordVerificationScreenState();
}

class _LandlordVerificationScreenState extends State<LandlordVerificationScreen> {
  final _businessController = TextEditingController();
  final _addressController = TextEditingController();
  late Future<LandlordVerificationProfile> _profile;
  bool _saving = false;
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _profile = widget.repository.getProfile();
  }

  @override
  void dispose() {
    _businessController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _saveAndSubmit(bool submit) async {
    if (_addressController.text.trim().length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter your physical address before continuing.')),
      );
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.repository.updateProfile(
        businessName: _businessController.text,
        physicalAddress: _addressController.text,
      );
      if (submit) await widget.repository.submitVerification();
      if (mounted) {
        setState(() {
          _initialized = false;
          _reload();
        });
      }
    } on LandlordAccountException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Landlord verification')),
      body: FutureBuilder<LandlordVerificationProfile>(
        future: _profile,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _Message(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load landlord profile',
              message: snapshot.error.toString(),
              action: FilledButton(
                onPressed: () => setState(_reload),
                child: const Text('Try again'),
              ),
            );
          }
          final profile = snapshot.data!;
          if (!_initialized) {
            _businessController.text = profile.businessName ?? '';
            _addressController.text = profile.physicalAddress ?? '';
            _initialized = true;
          }
          final locked = profile.status == 'pending' || profile.status == 'approved';
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              _VerificationStatusCard(profile: profile),
              const SizedBox(height: 20),
              TextField(
                controller: _businessController,
                enabled: !locked && !_saving,
                decoration: const InputDecoration(
                  labelText: 'Business / landlord name (optional)',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.business_outlined),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _addressController,
                enabled: !locked && !_saving,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Physical address',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.location_on_outlined),
                ),
              ),
              if (!locked) ...[
                const SizedBox(height: 18),
                OutlinedButton(
                  onPressed: _saving ? null : () => _saveAndSubmit(false),
                  child: const Text('Save profile'),
                ),
                const SizedBox(height: 10),
                FilledButton.icon(
                  onPressed: _saving ? null : () => _saveAndSubmit(true),
                  icon: _saving
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.verified_user_outlined),
                  label: const Text('Submit for Mosala verification'),
                ),
              ],
              if (profile.status == 'pending') ...[
                const SizedBox(height: 18),
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Your profile is locked while Mosala reviews it. You will receive an in-app notification after a decision.',
                    ),
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class AdvertChargeScreen extends StatefulWidget {
  const AdvertChargeScreen({
    super.key,
    required this.property,
    required this.repository,
  });

  final LandlordPropertySummary property;
  final ApiLandlordAccountRepository repository;

  @override
  State<AdvertChargeScreen> createState() => _AdvertChargeScreenState();
}

class _AdvertChargeScreenState extends State<AdvertChargeScreen> {
  final _referenceController = TextEditingController();
  late Future<AdvertChargeSummary?> _charge;
  String _method = 'mobile_money';
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _charge = widget.repository.getAdvertCharge(widget.property.id);

  @override
  void dispose() {
    _referenceController.dispose();
    super.dispose();
  }

  Future<void> _submit(AdvertChargeSummary charge) async {
    if (_referenceController.text.trim().length < 2) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Enter the advertising payment reference.')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await widget.repository.submitAdvertPayment(
        propertyId: widget.property.id,
        method: _method,
        reference: _referenceController.text,
      );
      if (mounted) setState(_reload);
    } on LandlordAccountException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'M ', decimalDigits: 2);
    return Scaffold(
      appBar: AppBar(title: const Text('Advert charge')),
      body: FutureBuilder<AdvertChargeSummary?>(
        future: _charge,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _Message(
              icon: Icons.cloud_off_outlined,
              title: 'Could not load advert charge',
              message: snapshot.error.toString(),
              action: FilledButton(onPressed: () => setState(_reload), child: const Text('Try again')),
            );
          }
          final charge = snapshot.data;
          if (charge == null) {
            return _Message(
              icon: Icons.price_check_outlined,
              title: 'Waiting for Mosala charge',
              message: widget.property.status == 'pending_verification'
                  ? 'Mosala must first approve this property. The advertising charge will be issued after property review.'
                  : 'Mosala has not issued an advertising charge for this property yet.',
            );
          }
          final canPay = charge.status == 'quoted' || charge.status == 'payment_rejected';
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(widget.property.title, style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        money.format(charge.amount),
                        style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 4),
                      Text('Status: ${charge.status.replaceAll('_', ' ')}'),
                      if (charge.note?.isNotEmpty == true) ...[
                        const SizedBox(height: 8),
                        Text(charge.note!),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (canPay) ...[
                DropdownButtonFormField<String>(
                  initialValue: _method,
                  decoration: const InputDecoration(
                    labelText: 'Payment method',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'mobile_money', child: Text('Mobile money')),
                    DropdownMenuItem(value: 'bank_transfer', child: Text('Bank transfer')),
                    DropdownMenuItem(value: 'cash', child: Text('Cash / counter payment')),
                    DropdownMenuItem(value: 'card', child: Text('Card')),
                  ],
                  onChanged: _submitting ? null : (value) => setState(() => _method = value ?? 'mobile_money'),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _referenceController,
                  decoration: const InputDecoration(
                    labelText: 'Transaction / payment reference',
                    border: OutlineInputBorder(),
                    prefixIcon: Icon(Icons.receipt_long_outlined),
                  ),
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _submitting ? null : () => _submit(charge),
                  icon: _submitting
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.send_rounded),
                  label: const Text('Submit advert payment for verification'),
                ),
              ] else if (charge.status == 'payment_submitted')
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('Your payment reference is waiting for Mosala verification.'),
                  ),
                )
              else if (charge.status == 'paid' || charge.status == 'waived')
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text('The advertising charge is cleared. Mosala can activate the advert.'),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _VerificationStatusCard extends StatelessWidget {
  const _VerificationStatusCard({required this.profile});

  final LandlordVerificationProfile profile;

  @override
  Widget build(BuildContext context) {
    final status = profile.status.replaceAll('_', ' ');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.verified_user_outlined),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Verification: $status',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            if (profile.rejectionReason?.isNotEmpty == true) ...[
              const SizedBox(height: 10),
              Text(profile.rejectionReason!),
            ],
          ],
        ),
      ),
    );
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.title, required this.message, this.action});

  final IconData icon;
  final String title;
  final String message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 56),
            const SizedBox(height: 12),
            Text(title, style: Theme.of(context).textTheme.titleLarge, textAlign: TextAlign.center),
            const SizedBox(height: 8),
            Text(message, textAlign: TextAlign.center),
            if (action != null) ...[const SizedBox(height: 16), action!],
          ],
        ),
      ),
    );
  }
}
