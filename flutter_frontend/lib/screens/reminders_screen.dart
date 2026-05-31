import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';

class RemindersScreen extends StatefulWidget {
  const RemindersScreen({super.key});

  @override
  State<RemindersScreen> createState() => _RemindersScreenState();
}

class _RemindersScreenState extends State<RemindersScreen> {
  List<Medication> _meds = [];
  bool _loading = true;
  String? _error;
  int _loadedForPatient = -1;
  final Set<int> _busy = {};

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
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final meds = await state.api.listMedications(state.activePatientId);
      if (!mounted) return;
      setState(() {
        _meds = meds;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Medication schedule isn\'t available yet.';
        _loading = false;
      });
    }
  }

  Future<void> _confirm(AppState state, Medication med) async {
    setState(() => _busy.add(med.id));
    try {
      await state.api.confirmIntake(med.id);
      if (!mounted) return;
      setState(() => med.taken = true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Couldn\'t confirm. Try again.')),
      );
    } finally {
      if (mounted) setState(() => _busy.remove(med.id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (!state.backendOnline) {
      return InfoState(
        icon: Icons.cloud_off,
        title: 'Backend offline',
        message: 'Connect to the backend to see today\'s medications.',
        color: AppTheme.danger,
        onRetry: () => state.refreshAll(),
      );
    }
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_meds.isEmpty) {
      return InfoState(
        icon: Icons.medication_outlined,
        title: 'No medications today',
        message: _error ??
            'When a medication schedule is set, doses appear here to confirm.',
        onRetry: () => _load(state),
      );
    }

    final taken = _meds.where((m) => m.taken).length;
    final total = _meds.length;

    return RefreshIndicator(
      onRefresh: () => _load(state),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          _progressHeader(context, taken, total),
          const SizedBox(height: 18),
          for (final m in _meds) ...[
            _medCard(context, state, m),
            const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }

  Widget _progressHeader(BuildContext context, int taken, int total) {
    final theme = Theme.of(context);
    final pct = total == 0 ? 0.0 : taken / total;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('Today\'s doses',
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700)),
                ),
                StatusPill(
                  label: '$taken / $total taken',
                  color: taken == total ? AppTheme.good : AppTheme.warn,
                  icon: taken == total
                      ? Icons.check_circle
                      : Icons.schedule_rounded,
                ),
              ],
            ),
            const SizedBox(height: 14),
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: LinearProgressIndicator(
                value: pct,
                minHeight: 10,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
                color: taken == total ? AppTheme.good : AppTheme.seed,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _medCard(BuildContext context, AppState state, Medication m) {
    final theme = Theme.of(context);
    final busy = _busy.contains(m.id);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: (m.taken ? AppTheme.good : AppTheme.warn)
                    .withOpacity(0.12),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Icon(Icons.medication_rounded,
                  color: m.taken ? AppTheme.good : AppTheme.warn),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(m.name,
                      style: theme.textTheme.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(
                    '${m.dose} · ${DateFormat('h:mm a').format(m.scheduledFor.toLocal())}',
                    style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (m.taken)
              const StatusPill(
                  label: 'Taken', color: AppTheme.good, icon: Icons.check)
            else
              FilledButton.tonal(
                onPressed: busy ? null : () => _confirm(state, m),
                style: FilledButton.styleFrom(
                  minimumSize: const Size(0, 42),
                  padding: const EdgeInsets.symmetric(horizontal: 18),
                ),
                child: busy
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Confirm'),
              ),
          ],
        ),
      ),
    );
  }
}
