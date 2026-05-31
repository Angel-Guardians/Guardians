import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'location_screen.dart';
import 'medical_history_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  VitalSeries? _hr;
  VitalSeries? _spo2;
  VitalSeries? _bp;
  List<Medication> _meds = [];
  List<LocationPoint> _locations = [];
  List<FallEvent> _falls = [];
  RiskSnapshot? _risk;
  bool _loading = true;
  int _loadedForPatient = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final state = Provider.of<AppState>(context);
    if (state.backendOnline && state.activePatientId != _loadedForPatient) {
      _loadedForPatient = state.activePatientId;
      _load(state);
    }
  }

  Future<void> _load(AppState state) async {
    setState(() => _loading = true);
    final api = state.api;
    final pid = state.activePatientId;
    final results = await Future.wait([
      api.getVitals('hr', patientId: pid).then<VitalSeries?>((v) => v).catchError((_) => null),
      api.getVitals('spo2', patientId: pid).then<VitalSeries?>((v) => v).catchError((_) => null),
      api.getVitals('bp', patientId: pid).then<VitalSeries?>((v) => v).catchError((_) => null),
      api.listMedications(pid).then<List<Medication>>((v) => v).catchError((_) => <Medication>[]),
      api.getLocations(patientId: pid).then<List<LocationPoint>>((v) => v).catchError((_) => <LocationPoint>[]),
      api.getFalls(patientId: pid).then<List<FallEvent>>((v) => v).catchError((_) => <FallEvent>[]),
      api.getRiskScore(patientId: pid).then<RiskSnapshot?>((v) => v).catchError((_) => null),
    ]);
    if (!mounted) return;
    setState(() {
      _hr = results[0] as VitalSeries?;
      _spo2 = results[1] as VitalSeries?;
      _bp = results[2] as VitalSeries?;
      _meds = results[3] as List<Medication>;
      _locations = results[4] as List<LocationPoint>;
      _falls = results[5] as List<FallEvent>;
      _risk = results[6] as RiskSnapshot?;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    if (!state.backendOnline) {
      return InfoState(
        icon: Icons.cloud_off,
        title: 'Backend offline',
        message:
            'Can\'t reach ${state.baseUrl}.\nStart the Guardian backend, or set the '
            'address from the settings gear in the header.',
        color: AppTheme.danger,
        onRetry: () => state.refreshAll(),
      );
    }

    final profile = state.profile;

    return RefreshIndicator(
      onRefresh: () async {
        await state.refreshAll();
        await _load(state);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          _greeting(context, profile),
          const SizedBox(height: 16),
          if (_risk != null) ...[
            _riskCard(context, _risk!),
            const SizedBox(height: 16),
          ],
          if (_recentFall != null) ...[
            _FallBanner(fall: _recentFall!),
            const SizedBox(height: 16),
          ],
          if (profile != null) ...[
            _profileCard(context, profile),
            const SizedBox(height: 14),
          ],
          _vitalsCard(context),
          const SizedBox(height: 14),
          _remindersCard(context),
          const SizedBox(height: 14),
          _locationCard(context, state),
          const SizedBox(height: 14),
          _medicalHistoryCard(context),
          if (_loading) ...[
            const SizedBox(height: 20),
            const Center(child: CircularProgressIndicator()),
          ],
        ],
      ),
    );
  }

  FallEvent? get _recentFall {
    final cutoff = DateTime.now().toUtc().subtract(const Duration(minutes: 30));
    for (final f in _falls) {
      if (f.ts.toUtc().isAfter(cutoff) &&
          (f.kind == 'fall_confirmed' || f.kind == 'fall_suspected')) {
        return f;
      }
    }
    return null;
  }

  Widget _greeting(BuildContext context, PatientProfile? profile) {
    final theme = Theme.of(context);
    final hour = DateTime.now().hour;
    final part = hour < 12 ? 'Good morning' : (hour < 18 ? 'Good afternoon' : 'Good evening');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(part,
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
        const SizedBox(height: 2),
        Text(
          profile == null ? 'Welcome' : 'Caring for ${profile.name}',
          style: theme.textTheme.headlineSmall
              ?.copyWith(fontWeight: FontWeight.w800),
        ),
      ],
    );
  }

  Widget _riskCard(BuildContext context, RiskSnapshot risk) {
    Color color;
    switch (risk.level) {
      case 'critical':
        color = AppTheme.danger;
      case 'high':
        color = Colors.orange;
      case 'moderate':
        color = AppTheme.warn;
      default:
        color = AppTheme.good;
    }
    final urgent = risk.level == 'critical' || risk.level == 'high';

    return SectionCard(
      icon: Icons.shield_outlined,
      iconColor: color,
      title: 'Risk monitor',
      subtitle: '${risk.level[0].toUpperCase()}${risk.level.substring(1)} · '
          'updated ${_ago(risk.updatedAt)}',
      trailing: StatusPill(
        label: risk.score.toStringAsFixed(0),
        color: color,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (risk.score / 100).clamp(0.0, 1.0),
              minHeight: 8,
              backgroundColor: color.withOpacity(0.15),
              valueColor: AlwaysStoppedAnimation<Color>(color),
            ),
          ),
          if (urgent) ...[
            const SizedBox(height: 8),
            Text(
              'Elevated risk — Guardian is monitoring closely.',
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ],
          if (risk.factors.isNotEmpty) ...[
            const SizedBox(height: 10),
            for (final f in risk.factors)
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(f.name,
                          style: const TextStyle(fontWeight: FontWeight.w600)),
                    ),
                    Flexible(
                      child: Text(
                        f.detail,
                        textAlign: TextAlign.end,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }

  Widget _profileCard(BuildContext context, PatientProfile p) {
    return SectionCard(
      child: Row(
        children: [
          InitialsAvatar(initials: _initials(p.name), size: 52),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(p.name,
                    style: Theme.of(context)
                        .textTheme
                        .titleLarge
                        ?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 2),
                Text('Age ${p.age} · ${p.conditions.length} conditions · '
                    '${p.medications.length} medications',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color:
                            Theme.of(context).colorScheme.onSurfaceVariant)),
                if (p.allergies.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final a in p.allergies.take(3))
                        StatusPill(
                            label: a,
                            color: AppTheme.danger,
                            icon: Icons.warning_amber_rounded),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _vitalsCard(BuildContext context) {
    final hr = _latest(_hr);
    final spo2 = _latest(_spo2);
    final bp = _bp?.points.isNotEmpty == true ? _bp!.points.last : null;
    return SectionCard(
      icon: Icons.favorite_rounded,
      iconColor: AppTheme.danger,
      title: 'Vitals',
      subtitle: 'Latest from the wearable',
      child: Row(
        children: [
          Expanded(
            child: MetricTile(
              label: 'Heart rate',
              value: hr == null ? '—' : hr.value.toStringAsFixed(0),
              unit: 'bpm',
              color: AppTheme.danger,
            ),
          ),
          Expanded(
            child: MetricTile(
              label: 'SpO₂',
              value: spo2 == null ? '—' : spo2.value.toStringAsFixed(0),
              unit: '%',
              color: AppTheme.good,
            ),
          ),
          Expanded(
            child: MetricTile(
              label: 'Blood pressure',
              value: bp == null
                  ? '—'
                  : '${(bp.systolic ?? bp.value).toStringAsFixed(0)}/${(bp.diastolic ?? 0).toStringAsFixed(0)}',
              color: AppTheme.seed,
            ),
          ),
        ],
      ),
    );
  }

  Widget _remindersCard(BuildContext context) {
    final taken = _meds.where((m) => m.taken).length;
    final total = _meds.length;
    final pending = total - taken;
    return SectionCard(
      icon: Icons.medication_rounded,
      iconColor: AppTheme.warn,
      title: 'Today\'s medications',
      subtitle: total == 0 ? 'No schedule loaded' : '$taken of $total confirmed',
      trailing: total == 0
          ? null
          : StatusPill(
              label: pending == 0 ? 'All done' : '$pending pending',
              color: pending == 0 ? AppTheme.good : AppTheme.warn,
            ),
      child: total == 0
          ? Text('Medication schedule will appear here once available.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant))
          : Column(
              children: [
                for (final m in _meds.take(3))
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Icon(
                          m.taken
                              ? Icons.check_circle
                              : Icons.radio_button_unchecked,
                          color: m.taken
                              ? AppTheme.good
                              : Theme.of(context).colorScheme.onSurfaceVariant,
                          size: 20,
                        ),
                        const SizedBox(width: 10),
                        Expanded(child: Text('${m.name} · ${m.dose}')),
                        Text(DateFormat('h:mm a').format(m.scheduledFor),
                            style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }

  Widget _locationCard(BuildContext context, AppState state) {
    final latest = _locations.isNotEmpty ? _locations.first : null;
    return SectionCard(
      icon: Icons.location_on_rounded,
      iconColor: AppTheme.seed,
      title: 'Location',
      subtitle: latest == null
          ? 'No recent position'
          : 'Updated ${_ago(latest.ts)}',
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => const LocationScreen())),
      child: latest == null
          ? Text('Location updates from the wearable will show here.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant))
          : Row(
              children: [
                Expanded(
                  child: Text(
                    '${latest.lat.toStringAsFixed(5)}, ${latest.lng.toStringAsFixed(5)}',
                    style: const TextStyle(
                        fontFeatures: [FontFeature.tabularFigures()]),
                  ),
                ),
                if (latest.accuracy != null)
                  StatusPill(
                      label: '±${latest.accuracy!.toStringAsFixed(0)} m',
                      color: AppTheme.seed),
              ],
            ),
    );
  }

  Widget _medicalHistoryCard(BuildContext context) {
    return SectionCard(
      icon: Icons.description_rounded,
      iconColor: AppTheme.good,
      title: 'Medical history',
      subtitle: 'Upload & review lab reports',
      onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => const MedicalHistoryScreen())),
      child: Text(
        'Upload a lab-results PDF — Guardian extracts the values and updates the profile automatically.',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant),
      ),
    );
  }

  VitalPoint? _latest(VitalSeries? s) =>
      (s?.points.isNotEmpty ?? false) ? s!.points.last : null;

  String _initials(String name) {
    final parts =
        name.trim().split(RegExp(r'\s+')).where((p) => p.isNotEmpty).toList();
    if (parts.isEmpty) return '?';
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return (parts.first[0] + parts.last[0]).toUpperCase();
  }

  String _ago(DateTime ts) {
    final d = DateTime.now().difference(ts.toLocal());
    if (d.inMinutes < 1) return 'just now';
    if (d.inMinutes < 60) return '${d.inMinutes} min ago';
    if (d.inHours < 24) return '${d.inHours} h ago';
    return DateFormat('MMM d').format(ts.toLocal());
  }
}

class _FallBanner extends StatelessWidget {
  const _FallBanner({required this.fall});
  final FallEvent fall;

  @override
  Widget build(BuildContext context) {
    final confirmed = fall.kind == 'fall_confirmed';
    final color = confirmed ? AppTheme.danger : AppTheme.warn;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, color: color, size: 28),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  confirmed ? 'Fall confirmed' : 'Possible fall detected',
                  style: TextStyle(
                      fontWeight: FontWeight.w800, color: color, fontSize: 15),
                ),
                Text(
                  'Peak impact ${fall.value.toStringAsFixed(1)} g · '
                  '${DateFormat('h:mm a').format(fall.ts.toLocal())} · ${fall.source}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
