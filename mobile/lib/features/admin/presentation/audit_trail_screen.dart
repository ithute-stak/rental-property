import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:rental_property/features/admin/data/api_audit_repository.dart';

class AuditTrailScreen extends StatefulWidget {
  const AuditTrailScreen({super.key, required this.repository});

  final AdminAuditRepository repository;

  @override
  State<AuditTrailScreen> createState() => _AuditTrailScreenState();
}

class _AuditTrailScreenState extends State<AuditTrailScreen> {
  static const _actions = <String>[
    'landlord.verification.approved',
    'landlord.verification.rejected',
    'property.approved',
    'property.rejected',
    'property.activated',
    'advert_charge.quoted',
    'advert_charge.waived',
    'advert_charge.payment_submitted',
    'advert_charge.payment_confirmed',
    'advert_charge.payment_rejected',
    'booking.created',
    'booking.payment_submitted',
    'booking.payment_confirmed',
    'booking.payment_rejected',
    'booking.cancelled',
    'booking.expired',
    'tenancy.activated',
    'tenancy.notice_given',
    'tenancy.ended',
    'tenancy.inspection_completed',
  ];

  AdminAuditQuery _query = const AdminAuditQuery();
  late Future<List<AdminAuditEvent>> _events;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _events = widget.repository.listEvents(query: _query);

  Future<void> _refresh() async {
    setState(_reload);
    await _events;
  }

  Future<void> _showFilters() async {
    final next = await showModalBottomSheet<AdminAuditQuery>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _AuditFilterSheet(
        initial: _query,
        actions: _actions,
      ),
    );
    if (next == null || !mounted) return;
    setState(() {
      _query = next;
      _reload();
    });
  }

  void _clearFilters() {
    setState(() {
      _query = const AdminAuditQuery();
      _reload();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audit trail'),
        actions: [
          IconButton(
            tooltip: 'Filter audit events',
            onPressed: _showFilters,
            icon: Badge(
              isLabelVisible: _query.hasFilters,
              child: const Icon(Icons.filter_list_rounded),
            ),
          ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: () => setState(_reload),
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Column(
        children: [
          _AuditHeader(query: _query, onClear: _clearFilters),
          Expanded(
            child: FutureBuilder<List<AdminAuditEvent>>(
              future: _events,
              builder: (context, snapshot) {
                if (snapshot.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return _AuditError(
                    message: snapshot.error.toString(),
                    onRetry: () => setState(_reload),
                  );
                }
                final events = snapshot.data ?? const [];
                if (events.isEmpty) {
                  return _AuditEmpty(filtered: _query.hasFilters, onClear: _clearFilters);
                }
                return RefreshIndicator(
                  onRefresh: _refresh,
                  child: ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    itemCount: events.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) => _AuditEventCard(event: events[index]),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _AuditHeader extends StatelessWidget {
  const _AuditHeader({required this.query, required this.onClear});

  final AdminAuditQuery query;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final chips = <Widget>[];
    void add(String label, String? value) {
      if (value != null && value.trim().isNotEmpty) {
        chips.add(Chip(label: Text('$label: ${_pretty(value)}')));
      }
    }

    add('Action', query.action);
    add('Entity', query.entityType);
    add('Entity ID', query.entityId);
    add('Actor', query.actorId);
    add('Request', query.requestId);
    final date = DateFormat('d MMM yyyy');
    if (query.since != null) chips.add(Chip(label: Text('From: ${date.format(query.since!)}')));
    if (query.until != null) chips.add(Chip(label: Text('To: ${date.format(query.until!)}')));

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Immutable business history',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          const Text(
            'Trace Mosala approvals, payments, bookings and tenancy changes back to the actor and HTTP request.',
          ),
          if (chips.isNotEmpty) ...[
            const SizedBox(height: 10),
            Wrap(spacing: 8, runSpacing: 6, children: chips),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: onClear,
                icon: const Icon(Icons.filter_alt_off_outlined),
                label: const Text('Clear filters'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _AuditEventCard extends StatelessWidget {
  const _AuditEventCard({required this.event});

  final AdminAuditEvent event;

  @override
  Widget build(BuildContext context) {
    final timestamp = DateFormat('d MMM yyyy • HH:mm:ss').format(event.createdAt);
    final actor = event.actorRole == null
        ? 'System automation'
        : '${_pretty(event.actorRole!)} • ${_shortId(event.actorId)}';
    final entity = '${_pretty(event.entityType)}${event.entityId == null ? '' : ' • ${_shortId(event.entityId)}'}';

    return Card(
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        leading: CircleAvatar(child: Icon(_iconFor(event.action))),
        title: Text(
          _pretty(event.action),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(timestamp),
              Text('$actor • $entity'),
              if (event.requestId != null)
                Text(
                  'Request: ${event.requestId}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          ),
        ),
        children: [
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _MetadataRow(label: 'Audit ID', value: event.id),
                _MetadataRow(label: 'Actor ID', value: event.actorId ?? 'System'),
                _MetadataRow(label: 'Entity', value: event.entityType),
                _MetadataRow(label: 'Entity ID', value: event.entityId ?? '—'),
                _MetadataRow(label: 'Request ID', value: event.requestId ?? 'Worker / not HTTP'),
                if (event.details.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  Text(
                    'Business state',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 6),
                  ...event.details.entries.map(
                    (entry) => _MetadataRow(
                      label: _pretty(entry.key),
                      value: _displayValue(entry.value),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  IconData _iconFor(String action) {
    if (action.startsWith('booking.')) return Icons.event_available_outlined;
    if (action.startsWith('tenancy.')) return Icons.key_outlined;
    if (action.startsWith('advert_charge.')) return Icons.payments_outlined;
    if (action.startsWith('property.')) return Icons.apartment_outlined;
    if (action.startsWith('landlord.')) return Icons.verified_user_outlined;
    return Icons.history_rounded;
  }
}

class _MetadataRow extends StatelessWidget {
  const _MetadataRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 112,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w700),
            ),
          ),
          Expanded(child: SelectableText(value)),
        ],
      ),
    );
  }
}

class _AuditFilterSheet extends StatefulWidget {
  const _AuditFilterSheet({required this.initial, required this.actions});

  final AdminAuditQuery initial;
  final List<String> actions;

  @override
  State<_AuditFilterSheet> createState() => _AuditFilterSheetState();
}

class _AuditFilterSheetState extends State<_AuditFilterSheet> {
  late String? _action;
  late final TextEditingController _entityType;
  late final TextEditingController _entityId;
  late final TextEditingController _actorId;
  late final TextEditingController _requestId;
  DateTime? _since;
  DateTime? _until;

  @override
  void initState() {
    super.initState();
    _action = widget.initial.action;
    _entityType = TextEditingController(text: widget.initial.entityType);
    _entityId = TextEditingController(text: widget.initial.entityId);
    _actorId = TextEditingController(text: widget.initial.actorId);
    _requestId = TextEditingController(text: widget.initial.requestId);
    _since = widget.initial.since;
    _until = widget.initial.until;
  }

  @override
  void dispose() {
    _entityType.dispose();
    _entityId.dispose();
    _actorId.dispose();
    _requestId.dispose();
    super.dispose();
  }

  String? _text(TextEditingController controller) {
    final value = controller.text.trim();
    return value.isEmpty ? null : value;
  }

  Future<void> _pickDate({required bool since}) async {
    final initial = (since ? _since : _until) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2025),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (picked == null) return;
    setState(() {
      if (since) {
        _since = DateTime(picked.year, picked.month, picked.day);
      } else {
        _until = DateTime(picked.year, picked.month, picked.day, 23, 59, 59, 999);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final date = DateFormat('d MMM yyyy');
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          16,
          20,
          20 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Text('Filter audit trail', style: Theme.of(context).textTheme.titleLarge),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String?>(
                initialValue: _action,
                isExpanded: true,
                decoration: const InputDecoration(labelText: 'Action', border: OutlineInputBorder()),
                items: [
                  const DropdownMenuItem<String?>(value: null, child: Text('All actions')),
                  ...widget.actions.map(
                    (action) => DropdownMenuItem<String?>(value: action, child: Text(_pretty(action))),
                  ),
                ],
                onChanged: (value) => setState(() => _action = value),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _entityType,
                decoration: const InputDecoration(
                  labelText: 'Entity type',
                  hintText: 'booking, property, tenancy…',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _entityId,
                decoration: const InputDecoration(labelText: 'Entity ID', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _actorId,
                decoration: const InputDecoration(labelText: 'Actor UUID', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _requestId,
                decoration: const InputDecoration(
                  labelText: 'Request ID',
                  helperText: 'Use the X-Request-ID from API/Caddy logs to trace one request.',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 10,
                runSpacing: 8,
                children: [
                  OutlinedButton.icon(
                    onPressed: () => _pickDate(since: true),
                    icon: const Icon(Icons.calendar_today_outlined),
                    label: Text(_since == null ? 'From date' : 'From ${date.format(_since!)}'),
                  ),
                  OutlinedButton.icon(
                    onPressed: () => _pickDate(since: false),
                    icon: const Icon(Icons.event_outlined),
                    label: Text(_until == null ? 'To date' : 'To ${date.format(_until!)}'),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context, const AdminAuditQuery()),
                      child: const Text('Reset'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: () {
                        Navigator.pop(
                          context,
                          AdminAuditQuery(
                            action: _action,
                            entityType: _text(_entityType),
                            entityId: _text(_entityId),
                            actorId: _text(_actorId),
                            requestId: _text(_requestId),
                            since: _since,
                            until: _until,
                          ),
                        );
                      },
                      child: const Text('Apply filters'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuditEmpty extends StatelessWidget {
  const _AuditEmpty({required this.filtered, required this.onClear});

  final bool filtered;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.history_toggle_off_rounded, size: 56),
            const SizedBox(height: 12),
            Text(
              filtered ? 'No audit events match these filters.' : 'No audit events have been recorded yet.',
              textAlign: TextAlign.center,
            ),
            if (filtered) ...[
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onClear, child: const Text('Clear filters')),
            ],
          ],
        ),
      ),
    );
  }
}

class _AuditError extends StatelessWidget {
  const _AuditError({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 56),
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

String _pretty(String value) {
  final words = value
      .replaceAll('.', ' ')
      .replaceAll('_', ' ')
      .split(' ')
      .where((part) => part.isNotEmpty)
      .toList();
  if (words.isEmpty) return value;
  final joined = words.join(' ');
  return '${joined[0].toUpperCase()}${joined.substring(1)}';
}

String _shortId(String? value) {
  if (value == null || value.isEmpty) return 'unknown';
  return value.length <= 8 ? value : '${value.substring(0, 8)}…';
}

String _displayValue(dynamic value) {
  if (value == null) return '—';
  if (value is bool) return value ? 'Yes' : 'No';
  if (value is List) return value.map(_displayValue).join(', ');
  if (value is Map) {
    return value.entries.map((entry) => '${_pretty(entry.key.toString())}: ${_displayValue(entry.value)}').join(' • ');
  }
  return value.toString();
}
