import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:rental_property/features/auth/presentation/session_cubit.dart';

class AccountScreen extends StatelessWidget {
  const AccountScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SessionCubit, SessionState>(
      builder: (context, state) => switch (state) {
        SessionChecking() => const Scaffold(
            appBar: _AccountAppBar(),
            body: Center(child: CircularProgressIndicator()),
          ),
        SessionGuest(:final message) => _GuestAccountView(message: message),
        SessionAuthenticated(:final user) => Scaffold(
            appBar: const _AccountAppBar(),
            body: ListView(
              padding: const EdgeInsets.all(24),
              children: [
                const CircleAvatar(
                  radius: 42,
                  child: Icon(Icons.person_rounded, size: 42),
                ),
                const SizedBox(height: 16),
                Text(
                  user.displayName,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                Text(user.phone, textAlign: TextAlign.center),
                if (user.email != null) Text(user.email!, textAlign: TextAlign.center),
                const SizedBox(height: 20),
                Card(
                  child: ListTile(
                    leading: Icon(user.isLandlord ? Icons.apartment_rounded : Icons.home_search_rounded),
                    title: Text(user.isLandlord ? 'Landlord account' : 'House seeker account'),
                    subtitle: Text(
                      user.isLandlord
                          ? 'Manage verification and rental properties from your landlord workspace.'
                          : 'Save homes, request viewings and book available rooms.',
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () async {
                    await context.read<SessionCubit>().logout();
                  },
                  icon: const Icon(Icons.logout_rounded),
                  label: const Text('Sign out'),
                ),
              ],
            ),
          ),
      },
    );
  }
}

class _AccountAppBar extends StatelessWidget implements PreferredSizeWidget {
  const _AccountAppBar();

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) => AppBar(title: const Text('Account'));
}

class _GuestAccountView extends StatefulWidget {
  const _GuestAccountView({this.message});

  final String? message;

  @override
  State<_GuestAccountView> createState() => _GuestAccountViewState();
}

class _GuestAccountViewState extends State<_GuestAccountView> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _identifierController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _registering = false;
  bool _submitting = false;
  String _role = 'house_seeker';

  @override
  void dispose() {
    _displayNameController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _identifierController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const _AccountAppBar(),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Image.asset('assets/branding/mosala_logo.webp', height: 110),
                const SizedBox(height: 12),
                Text(
                  _registering ? 'Create your Mosala Rentals account' : 'Welcome back',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                Text(
                  _registering
                      ? 'Register as a house seeker or landlord.'
                      : 'Sign in to manage bookings, properties and your account.',
                  textAlign: TextAlign.center,
                ),
                if (widget.message != null) ...[
                  const SizedBox(height: 16),
                  MaterialBanner(
                    content: Text(widget.message!),
                    actions: const [SizedBox.shrink()],
                  ),
                ],
                const SizedBox(height: 20),
                if (_registering) ...[
                  TextFormField(
                    controller: _displayNameController,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Full name',
                      prefixIcon: Icon(Icons.person_outline_rounded),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => (value?.trim().length ?? 0) < 2 ? 'Enter your full name' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Phone number',
                      prefixIcon: Icon(Icons.phone_outlined),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => (value?.trim().length ?? 0) < 7 ? 'Enter a valid phone number' : null,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Email (optional)',
                      prefixIcon: Icon(Icons.email_outlined),
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _role,
                    decoration: const InputDecoration(
                      labelText: 'Account type',
                      prefixIcon: Icon(Icons.badge_outlined),
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'house_seeker', child: Text('House seeker')),
                      DropdownMenuItem(value: 'landlord', child: Text('Landlord / property owner')),
                    ],
                    onChanged: (value) => setState(() => _role = value ?? 'house_seeker'),
                  ),
                ] else ...[
                  TextFormField(
                    controller: _identifierController,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Phone or email',
                      prefixIcon: Icon(Icons.person_outline_rounded),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => (value?.trim().length ?? 0) < 3 ? 'Enter your phone or email' : null,
                  ),
                ],
                const SizedBox(height: 12),
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  onFieldSubmitted: (_) => _submit(),
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    prefixIcon: Icon(Icons.lock_outline_rounded),
                    border: OutlineInputBorder(),
                  ),
                  validator: (value) => (value?.length ?? 0) < 8 ? 'Password must be at least 8 characters' : null,
                ),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    child: _submitting
                        ? const SizedBox.square(
                            dimension: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(_registering ? 'Create account' : 'Sign in'),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: _submitting
                      ? null
                      : () {
                          setState(() {
                            _registering = !_registering;
                            _passwordController.clear();
                          });
                        },
                  child: Text(
                    _registering
                        ? 'Already have an account? Sign in'
                        : 'New to Mosala Rentals? Create an account',
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'You can browse rental listings without signing in.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _submit() async {
    if (_submitting || !(_formKey.currentState?.validate() ?? false)) {
      return;
    }

    setState(() => _submitting = true);
    final session = context.read<SessionCubit>();
    final success = _registering
        ? await session.register(
            displayName: _displayNameController.text,
            phone: _phoneController.text,
            email: _emailController.text,
            password: _passwordController.text,
            role: _role,
          )
        : await session.login(
            identifier: _identifierController.text,
            password: _passwordController.text,
          );

    if (!mounted) return;
    setState(() => _submitting = false);
    if (success && Navigator.of(context).canPop()) {
      Navigator.of(context).pop();
    }
  }
}
