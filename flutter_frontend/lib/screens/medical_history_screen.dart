import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/common.dart';

class MedicalHistoryScreen extends StatefulWidget {
  const MedicalHistoryScreen({super.key});

  @override
  State<MedicalHistoryScreen> createState() => _MedicalHistoryScreenState();
}

class _MedicalHistoryScreenState extends State<MedicalHistoryScreen> {
  List<LabReport> _reports = [];
  bool _loading = true;
  bool _uploading = false;
  String? _error;
  LabUploadResult? _lastResult;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final state = context.read<AppState>();
    setState(() => _loading = true);
    try {
      final reports = await state.api.listLabRecords(state.activePatientId);
      if (!mounted) return;
      setState(() {
        _reports = reports;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Couldn\'t load records.';
        _loading = false;
      });
    }
  }

  Future<void> _pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    final bytes = file.bytes;
    if (bytes == null) {
      _snack('Couldn\'t read the file.');
      return;
    }
    if (bytes.length > 25 * 1024 * 1024) {
      _snack('File is larger than 25 MB.');
      return;
    }

    final state = context.read<AppState>();
    setState(() {
      _uploading = true;
      _lastResult = null;
      _error = null;
    });
    try {
      final res = await state.api.uploadLabRecord(
        patientId: state.activePatientId,
        filename: file.name,
        bytes: bytes,
      );
      if (!mounted) return;
      setState(() => _lastResult = res);
      // Profile may have been auto-updated by the backend extraction.
      await state.loadProfile();
      await _load();
    } catch (e) {
      _snack('Upload failed. Is the file a valid PDF?');
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  Future<void> _delete(LabReport r) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete record?'),
        content: Text(
            'Remove "${r.documentFilename ?? r.source}" and its ${r.observationCount} values?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppTheme.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    final state = context.read<AppState>();
    try {
      await state.api.deleteLabRecord(r.id);
      await _load();
    } catch (_) {
      _snack('Couldn\'t delete record.');
    }
  }

  void _snack(String m) {
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(m)));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Medical history')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
          children: [
            _uploadCard(context),
            if (_lastResult != null) ...[
              const SizedBox(height: 14),
              _resultCard(context, _lastResult!),
            ],
            const SizedBox(height: 18),
            Text('Uploaded records',
                style: Theme.of(context).textTheme.titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            if (_loading)
              const Center(
                  child: Padding(
                      padding: EdgeInsets.all(20),
                      child: CircularProgressIndicator()))
            else if (_reports.isEmpty)
              _emptyHint(context)
            else
              for (final r in _reports) ...[
                _reportTile(context, r),
                const SizedBox(height: 10),
              ],
          ],
        ),
      ),
    );
  }

  Widget _uploadCard(BuildContext context) {
    final theme = Theme.of(context);
    return SectionCard(
      icon: Icons.upload_file_rounded,
      iconColor: AppTheme.good,
      title: 'Upload lab results',
      subtitle: 'PDF · up to 25 MB',
      child: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: theme.colorScheme.outlineVariant,
                style: BorderStyle.solid,
              ),
              color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.3),
            ),
            child: Column(
              children: [
                Icon(Icons.picture_as_pdf_rounded,
                    size: 40, color: theme.colorScheme.onSurfaceVariant),
                const SizedBox(height: 12),
                Text(
                  'Guardian reads the PDF, extracts each test value, and updates '
                  'the profile automatically.',
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _uploading ? null : _pickAndUpload,
              icon: _uploading
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.attach_file_rounded),
              label: Text(_uploading ? 'Uploading & parsing…' : 'Choose PDF'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultCard(BuildContext context, LabUploadResult res) {
    final theme = Theme.of(context);
    final p = res.profile;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.good.withOpacity(0.09),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppTheme.good.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.check_circle_rounded,
                  color: AppTheme.good, size: 22),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  res.duplicate
                      ? 'Already uploaded earlier'
                      : 'Parsed ${res.observations} values',
                  style: theme.textTheme.titleSmall
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              StatusPill(label: res.status, color: AppTheme.good),
            ],
          ),
          if (p != null && p.applied) ...[
            const SizedBox(height: 12),
            Text('Profile updated automatically:',
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final c in p.conditionsAdded)
                  StatusPill(label: '+ $c', color: AppTheme.seed),
                for (final a in p.allergiesAdded)
                  StatusPill(label: '+ $a', color: AppTheme.danger),
                for (final m in p.medicationsAdded)
                  StatusPill(label: '+ $m', color: AppTheme.warn),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _reportTile(BuildContext context, LabReport r) {
    final theme = Theme.of(context);
    final statusColor = switch (r.status) {
      'parsed' => AppTheme.good,
      'needs_review' => AppTheme.warn,
      _ => theme.colorScheme.onSurfaceVariant,
    };
    return Card(
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: AppTheme.good.withOpacity(0.12),
            borderRadius: BorderRadius.circular(11),
          ),
          child: const Icon(Icons.description_rounded, color: AppTheme.good),
        ),
        title: Text(r.documentFilename ?? r.labName ?? r.source,
            maxLines: 1, overflow: TextOverflow.ellipsis),
        subtitle: Text(
          '${DateFormat('MMM d, y').format(r.createdAt.toLocal())} · ${r.observationCount} values',
          style: theme.textTheme.bodySmall,
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            StatusPill(label: r.status.replaceAll('_', ' '), color: statusColor),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              color: AppTheme.danger,
              onPressed: () => _delete(r),
            ),
          ],
        ),
        onTap: () => Navigator.of(context).push(MaterialPageRoute(
          builder: (_) => _LabDetailScreen(reportId: r.id),
        )),
      ),
    );
  }

  Widget _emptyHint(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Center(
          child: Text('No records uploaded yet.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant)),
        ),
      );
}

/// Detail view: all parsed observations for one report.
class _LabDetailScreen extends StatefulWidget {
  const _LabDetailScreen({required this.reportId});
  final int reportId;

  @override
  State<_LabDetailScreen> createState() => _LabDetailScreenState();
}

class _LabDetailScreenState extends State<_LabDetailScreen> {
  LabReportDetail? _detail;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  Future<void> _load() async {
    final state = context.read<AppState>();
    try {
      final d = await state.api.getLabRecord(widget.reportId);
      if (!mounted) return;
      setState(() {
        _detail = d;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _detail;
    return Scaffold(
      appBar: AppBar(
        title: Text(d?.documentFilename ?? 'Lab report'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : d == null
              ? const InfoState(
                  icon: Icons.error_outline,
                  title: 'Couldn\'t load report')
              : ListView(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
                  children: [
                    if (d.observations.isEmpty)
                      const InfoState(
                          icon: Icons.science_outlined,
                          title: 'No parsed values',
                          message:
                              'This document was stored but not machine-readable.')
                    else
                      for (final o in d.observations) _obsTile(context, o),
                  ],
                ),
    );
  }

  Widget _obsTile(BuildContext context, LabObservation o) {
    final theme = Theme.of(context);
    final fc = flagColor(o.flag, context);
    final flagged = o.flag != null && o.flag!.isNotEmpty;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 4),
        title: Text(o.testName,
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: o.referenceRange == null
            ? null
            : Text('Reference: ${o.referenceRange}',
                style: theme.textTheme.bodySmall),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  '${o.displayValue}${o.unit != null ? ' ${o.unit}' : ''}',
                  style: TextStyle(
                      fontWeight: FontWeight.w700,
                      color: flagged ? fc : theme.colorScheme.onSurface),
                ),
                if (flagged) ...[
                  const SizedBox(width: 6),
                  StatusPill(label: o.flag!, color: fc),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}
