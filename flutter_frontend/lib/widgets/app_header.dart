import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_state.dart';
import '../theme.dart';
import 'common.dart';

/// The shared top app bar: title, a patient switcher, online status, a theme
/// toggle and a settings entry (backend URL).
class GuardianHeader extends StatelessWidget implements PreferredSizeWidget {
  const GuardianHeader({super.key, required this.title});

  final String title;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return AppBar(
      titleSpacing: 16,
      title: Row(
        children: [
          Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: AppTheme.seed,
              borderRadius: BorderRadius.circular(9),
            ),
            child: const Icon(Icons.shield_rounded,
                color: Colors.white, size: 18),
          ),
          const SizedBox(width: 10),
          Text(title),
        ],
      ),
      actions: [
        _OnlineDot(online: state.backendOnline),
        if (state.patients.length > 1) const _PatientSwitcher(),
        IconButton(
          tooltip: 'Theme',
          icon: Icon(_themeIcon(state.themeMode)),
          onPressed: () => _cycleTheme(context, state),
        ),
        IconButton(
          tooltip: 'Settings',
          icon: const Icon(Icons.settings_outlined),
          onPressed: () => _openSettings(context, state),
        ),
        const SizedBox(width: 4),
      ],
    );
  }

  IconData _themeIcon(ThemeMode mode) => switch (mode) {
        ThemeMode.light => Icons.light_mode_outlined,
        ThemeMode.dark => Icons.dark_mode_outlined,
        ThemeMode.system => Icons.brightness_auto_outlined,
      };

  void _cycleTheme(BuildContext context, AppState state) {
    final next = switch (state.themeMode) {
      ThemeMode.system => ThemeMode.light,
      ThemeMode.light => ThemeMode.dark,
      ThemeMode.dark => ThemeMode.system,
    };
    state.setThemeMode(next);
  }

  Future<void> _openSettings(BuildContext context, AppState state) async {
    final controller = TextEditingController(text: state.baseUrl);
    final url = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Backend connection'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Set the address of your Guardian backend. Use 10.0.2.2 on the '
              'Android emulator, or your computer\'s LAN IP on a real device.',
              style: TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: controller,
              autofocus: true,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                labelText: 'Base URL',
                hintText: 'http://10.0.2.2:8000',
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Icon(
                  state.backendOnline ? Icons.check_circle : Icons.error_outline,
                  size: 16,
                  color: state.backendOnline ? AppTheme.good : AppTheme.danger,
                ),
                const SizedBox(width: 6),
                Text(
                  state.backendOnline ? 'Currently connected' : 'Not reachable',
                  style: const TextStyle(fontSize: 13),
                ),
              ],
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text),
            child: const Text('Save & reconnect'),
          ),
        ],
      ),
    );
    if (url != null && url.trim().isNotEmpty) {
      await state.setBaseUrl(url);
    }
  }
}

class _OnlineDot extends StatelessWidget {
  const _OnlineDot({required this.online});
  final bool online;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 4),
      child: Tooltip(
        message: online ? 'Backend online' : 'Backend offline',
        child: Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: online ? AppTheme.good : AppTheme.danger,
          ),
        ),
      ),
    );
  }
}

class _PatientSwitcher extends StatelessWidget {
  const _PatientSwitcher();

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final active = state.activePatient;
    return PopupMenuButton<int>(
      tooltip: 'Switch patient',
      onSelected: state.setActivePatient,
      itemBuilder: (ctx) => [
        for (final p in state.patients)
          PopupMenuItem<int>(
            value: p.id,
            child: Row(
              children: [
                InitialsAvatar(initials: p.initials, size: 30),
                const SizedBox(width: 10),
                Text(p.name),
                if (p.id == state.activePatientId) ...[
                  const SizedBox(width: 8),
                  const Icon(Icons.check, size: 16),
                ],
              ],
            ),
          ),
      ],
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4),
        child: InitialsAvatar(
          initials: active?.initials ?? '?',
          size: 32,
        ),
      ),
    );
  }
}
