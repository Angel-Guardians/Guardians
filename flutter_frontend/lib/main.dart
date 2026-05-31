import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/event_stream.dart';
import 'state/app_state.dart';
import 'theme.dart';
import 'screens/dashboard_screen.dart';
import 'screens/vitals_screen.dart';
import 'screens/chat_screen.dart';
import 'screens/reminders_screen.dart';
import 'screens/profile_screen.dart';
import 'widgets/app_header.dart';
import 'widgets/call_sheet.dart';

/// Global navigator key so backend-pushed call requests can open the call sheet
/// from anywhere (no matter which screen is on top).
final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

void main() {
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState()..bootstrap(),
      child: const GuardianApp(),
    ),
  );
}

class GuardianApp extends StatelessWidget {
  const GuardianApp({super.key});

  @override
  Widget build(BuildContext context) {
    final mode = context.select<AppState, ThemeMode>((s) => s.themeMode);
    return MaterialApp(
      title: 'Guardian',
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: mode,
      home: const RootShell(),
    );
  }
}

/// The five primary destinations, shown in a bottom navigation bar.
class RootShell extends StatefulWidget {
  const RootShell({super.key});

  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  int _index = 0;
  StreamSubscription<SseEvent>? _eventSub;
  final Set<String> _handledCalls = {};

  static const _titles = ['Guardian', 'Vitals', 'Talk', 'Care', 'Profile'];

  @override
  void initState() {
    super.initState();
    // Listen for backend-pushed call requests (the agent decided to call
    // someone — e.g. from a spoken request on the watch). Dial + play the
    // server's Kokoro voice once connected.
    final state = context.read<AppState>();
    _eventSub = state.eventStream.events.listen(_onServerEvent);
  }

  @override
  void dispose() {
    _eventSub?.cancel();
    super.dispose();
  }

  void _onServerEvent(SseEvent e) {
    if (!mounted || e.kind != 'call_request') return;
    if (_handledCalls.contains(e.id)) return; // SSE may re-deliver
    _handledCalls.add(e.id);

    final state = context.read<AppState>();
    final p = e.payload;
    final pid = p['patient_id'];
    if (pid is int && pid != state.activePatientId) return; // other patient

    final phone = '${p['phone'] ?? ''}'.trim();
    if (phone.isEmpty) return;
    final message = '${p['message'] ?? ''}';
    final name = p['contact_name'] as String?;
    final route = '${p['route'] ?? 'safety'}';
    final rel = '${p['audio_url'] ?? ''}';
    final audioUrl = rel.isEmpty
        ? null
        : state.baseUrl.replaceAll(RegExp(r'/+$'), '') + rel;

    final ctx = navigatorKey.currentContext;
    if (ctx == null) return;
    showEmergencyCallSheet(
      ctx,
      number: phone,
      name: name,
      message: message,
      audioUrl: audioUrl,
      emergency: route == 'safety' || phone == '911',
    );
  }

  final _pages = const [
    DashboardScreen(),
    VitalsScreen(),
    ChatScreen(),
    RemindersScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    if (state.initializing) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: GuardianHeader(title: _titles[_index]),
      body: SafeArea(
        child: IndexedStack(index: _index, children: _pages),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home_rounded),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.favorite_outline),
            selectedIcon: Icon(Icons.favorite_rounded),
            label: 'Vitals',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble_rounded),
            label: 'Talk',
          ),
          NavigationDestination(
            icon: Icon(Icons.medication_outlined),
            selectedIcon: Icon(Icons.medication_rounded),
            label: 'Care',
          ),
          NavigationDestination(
            icon: Icon(Icons.person_outline),
            selectedIcon: Icon(Icons.person_rounded),
            label: 'Profile',
          ),
        ],
      ),
    );
  }
}
