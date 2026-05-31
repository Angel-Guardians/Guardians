import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';

class LocationScreen extends StatefulWidget {
  const LocationScreen({super.key});

  @override
  State<LocationScreen> createState() => _LocationScreenState();
}

class _LocationScreenState extends State<LocationScreen> {
  List<LocationPoint> _points = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final state = context.read<AppState>();
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final pts = await state.api.getLocations(patientId: state.activePatientId);
      if (!mounted) return;
      setState(() {
        _points = pts;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Couldn\'t load location history.';
        _loading = false;
      });
    }
  }

  Future<void> _openMap(LocationPoint p) async {
    final uri = Uri.parse(
        'https://www.google.com/maps/search/?api=1&query=${p.lat},${p.lng}');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Couldn\'t open maps')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final latest = _points.isNotEmpty ? _points.first : null;
    return Scaffold(
      appBar: AppBar(title: const Text('Location')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? InfoState(
                  icon: Icons.location_off,
                  title: 'No location data',
                  message: _error,
                  onRetry: _load,
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                    children: [
                      if (latest != null) _latestCard(context, latest),
                      const SizedBox(height: 18),
                      Text('History (last 24 h)',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w700)),
                      const SizedBox(height: 4),
                      Text('${_points.length} points · newest first',
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant)),
                      const SizedBox(height: 12),
                      if (_points.isEmpty)
                        _emptyHint(context)
                      else
                        for (final p in _points) _historyRow(context, p),
                    ],
                  ),
                ),
    );
  }

  Widget _latestCard(BuildContext context, LocationPoint p) {
    return SectionCard(
      icon: Icons.my_location_rounded,
      iconColor: AppTheme.seed,
      title: 'Latest position',
      subtitle: DateFormat('EEE, MMM d · h:mm a').format(p.ts.toLocal()),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: MetricTile(
                    label: 'Latitude',
                    value: p.lat.toStringAsFixed(5),
                    color: AppTheme.seed),
              ),
              Expanded(
                child: MetricTile(
                    label: 'Longitude',
                    value: p.lng.toStringAsFixed(5),
                    color: AppTheme.seed),
              ),
              if (p.accuracy != null)
                Expanded(
                  child: MetricTile(
                      label: 'Accuracy',
                      value: '±${p.accuracy!.toStringAsFixed(0)}',
                      unit: 'm',
                      color: AppTheme.good),
                ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: () => _openMap(p),
              icon: const Icon(Icons.map_rounded),
              label: const Text('Open in Google Maps'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _historyRow(BuildContext context, LocationPoint p) {
    final theme = Theme.of(context);
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 4),
      leading: const Icon(Icons.place_outlined),
      title: Text(
        '${p.lat.toStringAsFixed(5)}, ${p.lng.toStringAsFixed(5)}',
        style: const TextStyle(
            fontFeatures: [FontFeature.tabularFigures()], fontSize: 14),
      ),
      subtitle: Text(DateFormat('h:mm a').format(p.ts.toLocal())),
      trailing: p.accuracy == null
          ? null
          : StatusPill(
              label: '±${p.accuracy!.toStringAsFixed(0)} m',
              color: theme.colorScheme.onSurfaceVariant),
      onTap: () => _openMap(p),
    );
  }

  Widget _emptyHint(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Center(
          child: Text('No location points in the last 24 hours.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant)),
        ),
      );
}
