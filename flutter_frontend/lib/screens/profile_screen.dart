import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/call_sheet.dart';
import '../widgets/common.dart';
import '../widgets/tag_input.dart';

const _languages = {
  'en': 'English',
  'es': 'Spanish',
  'fr': 'French',
  'zh': 'Chinese',
  'ar': 'Arabic',
  'pt': 'Portuguese',
};

const _relationships = [
  'daughter',
  'son',
  'spouse',
  'neighbour',
  'family_doctor',
  'caregiver',
  'other',
];

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  PatientProfile? _draft;
  String _originalJson = '';
  bool _saving = false;
  int _loadedForPatient = -1;

  final _nameCtrl = TextEditingController();
  final _ageCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final state = Provider.of<AppState>(context);
    if (state.profile != null && state.activePatientId != _loadedForPatient) {
      _loadedForPatient = state.activePatientId;
      _resetFrom(state.profile!);
    }
  }

  void _resetFrom(PatientProfile p) {
    _draft = p.copy();
    _originalJson = p.toUpdateJson().toString();
    _nameCtrl.text = _draft!.name;
    _ageCtrl.text = _draft!.age.toString();
    _notesCtrl.text = _draft!.notes ?? '';
    setState(() {});
  }

  bool get _dirty {
    if (_draft == null) return false;
    _syncControllers();
    return _draft!.toUpdateJson().toString() != _originalJson;
  }

  void _syncControllers() {
    if (_draft == null) return;
    _draft!.name = _nameCtrl.text;
    _draft!.age = int.tryParse(_ageCtrl.text) ?? _draft!.age;
    _draft!.notes = _notesCtrl.text.isEmpty ? null : _notesCtrl.text;
  }

  Future<void> _save(AppState state) async {
    _syncControllers();
    setState(() => _saving = true);
    try {
      final saved =
          await state.api.updatePatientProfile(state.activePatientId, _draft!);
      state.setProfile(saved);
      _resetFrom(saved);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile saved')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Couldn\'t save profile')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _ageCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (!state.backendOnline) {
      return InfoState(
        icon: Icons.cloud_off,
        title: 'Backend offline',
        message: 'Connect to the backend to view the profile.',
        color: AppTheme.danger,
        onRetry: () => state.refreshAll(),
      );
    }
    final draft = _draft;
    if (draft == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
          children: [
            _basicCard(context, draft),
            const SizedBox(height: 14),
            _medicalCard(context, draft),
            const SizedBox(height: 14),
            _contactsCard(context, draft),
            const SizedBox(height: 14),
            _medsCard(context, draft),
            const SizedBox(height: 14),
            _emergencyPreview(context, draft),
          ],
        ),
        if (_dirty)
          Positioned(
            left: 16,
            right: 16,
            bottom: 16,
            child: _saveBar(context, state),
          ),
      ],
    );
  }

  Widget _saveBar(BuildContext context, AppState state) {
    return Material(
      elevation: 8,
      borderRadius: BorderRadius.circular(16),
      color: Theme.of(context).colorScheme.inverseSurface,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 10, 10, 10),
        child: Row(
          children: [
            Expanded(
              child: Text('You have unsaved changes',
                  style: TextStyle(
                      color: Theme.of(context).colorScheme.onInverseSurface,
                      fontWeight: FontWeight.w600)),
            ),
            TextButton(
              onPressed: _saving ? null : () => _resetFrom(state.profile!),
              child: const Text('Discard'),
            ),
            const SizedBox(width: 4),
            FilledButton(
              onPressed: _saving ? null : () => _save(state),
              child: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _basicCard(BuildContext context, PatientProfile p) {
    return SectionCard(
      icon: Icons.badge_rounded,
      title: 'Basic information',
      child: Column(
        children: [
          TextField(
            controller: _nameCtrl,
            decoration: const InputDecoration(labelText: 'Full name'),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              SizedBox(
                width: 110,
                child: TextField(
                  controller: _ageCtrl,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Age'),
                  onChanged: (_) => setState(() {}),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  value: _languages.containsKey(p.primaryLanguage)
                      ? p.primaryLanguage
                      : 'en',
                  decoration: const InputDecoration(labelText: 'Language'),
                  items: [
                    for (final e in _languages.entries)
                      DropdownMenuItem(value: e.key, child: Text(e.value)),
                  ],
                  onChanged: (v) =>
                      setState(() => p.primaryLanguage = v ?? 'en'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _medicalCard(BuildContext context, PatientProfile p) {
    return SectionCard(
      icon: Icons.medical_information_rounded,
      iconColor: AppTheme.danger,
      title: 'Medical',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Conditions', style: _labelStyle(context)),
          const SizedBox(height: 8),
          TagInput(
            tags: p.conditions,
            hint: 'Add a condition…',
            color: AppTheme.seed,
            onChanged: (t) => setState(() => p.conditions = t),
          ),
          const SizedBox(height: 16),
          Text('Allergies', style: _labelStyle(context)),
          const SizedBox(height: 8),
          TagInput(
            tags: p.allergies,
            hint: 'Add an allergy…',
            color: AppTheme.danger,
            onChanged: (t) => setState(() => p.allergies = t),
          ),
          const SizedBox(height: 16),
          Text('Notes', style: _labelStyle(context)),
          const SizedBox(height: 8),
          TextField(
            controller: _notesCtrl,
            minLines: 2,
            maxLines: 5,
            decoration:
                const InputDecoration(hintText: 'Anything caregivers should know…'),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
    );
  }

  Widget _contactsCard(BuildContext context, PatientProfile p) {
    return SectionCard(
      icon: Icons.contacts_rounded,
      iconColor: AppTheme.good,
      title: 'Emergency contacts',
      subtitle: 'Lowest priority number is called first',
      trailing: IconButton.filledTonal(
        icon: const Icon(Icons.add),
        onPressed: () => setState(() => p.emergencyContacts.add(EmergencyContact(
              name: '',
              relationship: 'daughter',
              phone: '',
              priority: p.emergencyContacts.length + 1,
            ))),
      ),
      child: p.emergencyContacts.isEmpty
          ? _emptyHint(context, 'No contacts yet. Add one above.')
          : Column(
              children: [
                for (var i = 0; i < p.emergencyContacts.length; i++) ...[
                  _contactRow(context, p, i),
                  if (i != p.emergencyContacts.length - 1)
                    const Divider(height: 24),
                ],
              ],
            ),
    );
  }

  Widget _contactRow(BuildContext context, PatientProfile p, int i) {
    final c = p.emergencyContacts[i];
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: c.name,
                decoration: const InputDecoration(labelText: 'Name'),
                onChanged: (v) {
                  c.name = v;
                  setState(() {});
                },
              ),
            ),
            const SizedBox(width: 4),
            IconButton(
              tooltip: 'Call now',
              icon: const Icon(Icons.call_rounded),
              color: AppTheme.good,
              onPressed: c.phone.trim().isEmpty
                  ? null
                  : () => showEmergencyCallSheet(
                        context,
                        number: c.phone,
                        name: c.name.isEmpty ? c.relationship : c.name,
                        message:
                            'Hello, this is a Guardian alert for ${p.name}. '
                            'Please check on them when you can.',
                      ),
            ),
            IconButton(
              tooltip: 'Remove',
              icon: const Icon(Icons.delete_outline),
              color: AppTheme.danger,
              onPressed: () =>
                  setState(() => p.emergencyContacts.removeAt(i)),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _relationships.contains(c.relationship)
                    ? c.relationship
                    : 'other',
                decoration: const InputDecoration(labelText: 'Relationship'),
                items: [
                  for (final r in _relationships)
                    DropdownMenuItem(
                        value: r,
                        child: Text(r.replaceAll('_', ' '))),
                ],
                onChanged: (v) =>
                    setState(() => c.relationship = v ?? 'other'),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 92,
              child: TextFormField(
                initialValue: c.priority.toString(),
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Priority'),
                onChanged: (v) {
                  c.priority = int.tryParse(v) ?? c.priority;
                  setState(() {});
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        TextFormField(
          initialValue: c.phone,
          keyboardType: TextInputType.phone,
          decoration: const InputDecoration(labelText: 'Phone'),
          onChanged: (v) {
            c.phone = v;
            setState(() {});
          },
        ),
      ],
    );
  }

  Widget _medsCard(BuildContext context, PatientProfile p) {
    return SectionCard(
      icon: Icons.medication_rounded,
      iconColor: AppTheme.warn,
      title: 'Medications',
      trailing: IconButton.filledTonal(
        icon: const Icon(Icons.add),
        onPressed: () => setState(() => p.medications.add(ProfileMedication(
              name: '',
              dose: '',
              scheduleCron: '0 8 * * *',
              withFood: false,
            ))),
      ),
      child: p.medications.isEmpty
          ? _emptyHint(context, 'No medications yet. Add one above.')
          : Column(
              children: [
                for (var i = 0; i < p.medications.length; i++) ...[
                  _medRow(context, p, i),
                  if (i != p.medications.length - 1) const Divider(height: 24),
                ],
              ],
            ),
    );
  }

  Widget _medRow(BuildContext context, PatientProfile p, int i) {
    final m = p.medications[i];
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: m.name,
                decoration: const InputDecoration(labelText: 'Medication'),
                onChanged: (v) {
                  m.name = v;
                  setState(() {});
                },
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              icon: const Icon(Icons.delete_outline),
              color: AppTheme.danger,
              onPressed: () => setState(() => p.medications.removeAt(i)),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                initialValue: m.dose,
                decoration: const InputDecoration(labelText: 'Dose'),
                onChanged: (v) {
                  m.dose = v;
                  setState(() {});
                },
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextFormField(
                initialValue: m.scheduleCron,
                decoration: const InputDecoration(
                    labelText: 'Schedule (cron)', hintText: '0 8 * * *'),
                onChanged: (v) {
                  m.scheduleCron = v;
                  setState(() {});
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          title: const Text('Take with food'),
          value: m.withFood,
          onChanged: (v) => setState(() => m.withFood = v),
        ),
      ],
    );
  }

  Widget _emergencyPreview(BuildContext context, PatientProfile p) {
    final theme = Theme.of(context);
    final sorted = [...p.emergencyContacts]
      ..sort((a, b) => a.priority.compareTo(b.priority));
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.danger.withOpacity(0.07),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.danger.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.emergency_share_rounded,
                  color: AppTheme.danger, size: 20),
              const SizedBox(width: 8),
              Text('Emergency summary',
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'In an emergency, Guardian shares: ${_nameCtrl.text.isEmpty ? "—" : _nameCtrl.text}, '
            'age ${_ageCtrl.text}, '
            '${p.conditions.isEmpty ? "no known conditions" : p.conditions.join(", ")}'
            '${p.allergies.isEmpty ? "" : "; allergic to ${p.allergies.join(", ")}"}.',
            style: theme.textTheme.bodyMedium?.copyWith(height: 1.4),
          ),
          if (sorted.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text('Contacts called in order:',
                style: theme.textTheme.bodySmall
                    ?.copyWith(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            for (final c in sorted)
              Text('${c.priority}. ${c.name} (${c.relationship.replaceAll("_", " ")}) — ${c.phone}',
                  style: theme.textTheme.bodySmall),
          ],
        ],
      ),
    );
  }

  Widget _emptyHint(BuildContext context, String text) => Text(text,
      style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: Theme.of(context).colorScheme.onSurfaceVariant));

  TextStyle? _labelStyle(BuildContext context) => Theme.of(context)
      .textTheme
      .bodyMedium
      ?.copyWith(fontWeight: FontWeight.w700);
}
