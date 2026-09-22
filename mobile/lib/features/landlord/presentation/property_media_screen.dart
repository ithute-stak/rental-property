import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:rental_property/features/landlord/data/api_landlord_property_repository.dart';
import 'package:rental_property/features/landlord/data/api_property_media_repository.dart';

class PropertyMediaScreen extends StatefulWidget {
  const PropertyMediaScreen({
    super.key,
    required this.property,
    required this.repository,
  });

  final LandlordPropertySummary property;
  final ApiPropertyMediaRepository repository;

  @override
  State<PropertyMediaScreen> createState() => _PropertyMediaScreenState();
}

class _PropertyMediaScreenState extends State<PropertyMediaScreen> {
  final _picker = ImagePicker();
  List<PropertyMediaItem> _items = const [];
  bool _loading = true;
  bool _busy = false;
  String? _error;

  bool get _editable =>
      widget.property.status == 'draft' || widget.property.status == 'rejected';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final items = await widget.repository.list(widget.property.id);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _addPhotos() async {
    if (_busy || !_editable) return;
    final selected = await _picker.pickMultiImage(
      imageQuality: 85,
      maxWidth: 2048,
      maxHeight: 2048,
    );
    if (selected.isEmpty || !mounted) return;

    final remainingSlots = 20 - _items.length;
    if (remainingSlots <= 0) {
      _showMessage('A property can have up to 20 photos in this version.');
      return;
    }
    final files = selected.take(remainingSlots).toList();

    setState(() => _busy = true);
    try {
      await widget.repository.uploadImages(
        propertyId: widget.property.id,
        files: files,
        startingSortOrder: _items.length,
      );
      if (!mounted) return;
      _showMessage('${files.length} photo${files.length == 1 ? '' : 's'} uploaded.');
      await _load();
    } catch (error) {
      if (!mounted) return;
      _showMessage(error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _setCover(PropertyMediaItem item) async {
    if (_busy || item.isCover || !_editable) return;
    setState(() => _busy = true);
    try {
      await widget.repository.setCover(propertyId: widget.property.id, mediaId: item.id);
      await _load();
    } catch (error) {
      if (mounted) _showMessage(error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _delete(PropertyMediaItem item) async {
    if (_busy || !_editable) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Remove photo?'),
        content: Text(
          item.isCover
              ? 'This is the cover photo. Another photo will automatically become the cover.'
              : 'This photo will be permanently removed from the property advert.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _busy = true);
    try {
      await widget.repository.delete(propertyId: widget.property.id, mediaId: item.id);
      await _load();
    } catch (error) {
      if (mounted) _showMessage(error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Property photos'),
        actions: [
          if (_editable)
            IconButton(
              tooltip: 'Add photos',
              onPressed: _busy ? null : _addPhotos,
              icon: const Icon(Icons.add_photo_alternate_outlined),
            ),
        ],
      ),
      body: Stack(
        children: [
          RefreshIndicator(
            onRefresh: _load,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                Text(
                  widget.property.title,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 6),
                Text('${widget.property.town} • ${widget.property.totalRooms} rooms'),
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.photo_library_outlined),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            _editable
                                ? 'Add clear photos of the property and rooms. The cover photo is what house seekers see first on the rental feed.'
                                : 'This advert is ${widget.property.status.replaceAll('_', ' ')}. Photos are locked while the advert is under review or active.',
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.all(40),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (_error != null)
                  _MediaMessage(
                    icon: Icons.cloud_off_outlined,
                    message: _error!,
                    actionLabel: 'Try again',
                    onAction: _load,
                  )
                else if (_items.isEmpty)
                  _MediaMessage(
                    icon: Icons.add_photo_alternate_outlined,
                    message: 'No property photos yet.',
                    actionLabel: _editable ? 'Choose photos' : null,
                    onAction: _editable ? _addPhotos : null,
                  )
                else
                  GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 2,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      childAspectRatio: 1.05,
                    ),
                    itemCount: _items.length,
                    itemBuilder: (context, index) {
                      final item = _items[index];
                      return _PhotoTile(
                        item: item,
                        editable: _editable && !_busy,
                        onSetCover: () => _setCover(item),
                        onDelete: () => _delete(item),
                      );
                    },
                  ),
                if (_editable) ...[
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: _busy ? null : _addPhotos,
                    icon: const Icon(Icons.add_photo_alternate_outlined),
                    label: Text(_items.isEmpty ? 'Choose property photos' : 'Add more photos'),
                  ),
                ],
              ],
            ),
          ),
          if (_busy)
            Positioned.fill(
              child: ColoredBox(
                color: Colors.black26,
                child: Center(
                  child: Card(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: const [
                          SizedBox.square(
                            dimension: 24,
                            child: CircularProgressIndicator(strokeWidth: 2.5),
                          ),
                          SizedBox(width: 14),
                          Text('Updating photos...'),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _PhotoTile extends StatelessWidget {
  const _PhotoTile({
    required this.item,
    required this.editable,
    required this.onSetCover,
    required this.onDelete,
  });

  final PropertyMediaItem item;
  final bool editable;
  final VoidCallback onSetCover;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Stack(
        fit: StackFit.expand,
        children: [
          ColoredBox(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: CachedNetworkImage(
              imageUrl: item.url,
              fit: BoxFit.cover,
              placeholder: (_, _) => const Center(child: CircularProgressIndicator()),
              errorWidget: (_, _, _) => const Center(child: Icon(Icons.broken_image_outlined)),
            ),
          ),
          if (item.isCover)
            const Positioned(
              left: 8,
              bottom: 8,
              child: Chip(
                avatar: Icon(Icons.star_rounded, size: 18),
                label: Text('Cover'),
              ),
            ),
          if (editable)
            Positioned(
              right: 4,
              top: 4,
              child: PopupMenuButton<String>(
                color: Colors.white,
                onSelected: (value) {
                  if (value == 'cover') onSetCover();
                  if (value == 'delete') onDelete();
                },
                itemBuilder: (_) => [
                  if (!item.isCover)
                    const PopupMenuItem(value: 'cover', child: Text('Set as cover')),
                  const PopupMenuItem(value: 'delete', child: Text('Remove photo')),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _MediaMessage extends StatelessWidget {
  const _MediaMessage({
    required this.icon,
    required this.message,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String message;
  final String? actionLabel;
  final Future<void> Function()? onAction;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40),
      child: Column(
        children: [
          Icon(icon, size: 48),
          const SizedBox(height: 12),
          Text(message, textAlign: TextAlign.center),
          if (actionLabel != null && onAction != null) ...[
            const SizedBox(height: 14),
            OutlinedButton(onPressed: onAction, child: Text(actionLabel!)),
          ],
        ],
      ),
    );
  }
}
