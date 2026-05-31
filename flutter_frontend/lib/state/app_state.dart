import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config.dart';
import '../models/models.dart';
import '../services/api_client.dart';
import '../services/call_service.dart';
import '../services/event_stream.dart';

/// Global app state: backend URL, active patient, patient list, and the
/// currently loaded profile. Screens read this via Provider and call its
/// methods to refresh data.
class AppState extends ChangeNotifier {
  AppState() {
    api = ApiClient(() => _baseUrl);
  }

  late final ApiClient api;

  /// Places real phone calls via the SIM and speaks alerts aloud.
  final CallService callService = CallService();

  /// Live event stream from the backend (used for server-pushed call requests).
  late final EventStreamService eventStream = EventStreamService(() => _baseUrl);

  String _baseUrl = AppConfig.defaultBaseUrl;
  String get baseUrl => _baseUrl;

  int _activePatientId = AppConfig.defaultPatientId;
  int get activePatientId => _activePatientId;

  List<Patient> _patients = [];
  List<Patient> get patients => _patients;

  PatientProfile? _profile;
  PatientProfile? get profile => _profile;

  bool _backendOnline = false;
  bool get backendOnline => _backendOnline;

  bool _initializing = true;
  bool get initializing => _initializing;

  ThemeMode _themeMode = ThemeMode.system;
  ThemeMode get themeMode => _themeMode;

  Patient? get activePatient {
    for (final p in _patients) {
      if (p.id == _activePatientId) return p;
    }
    return null;
  }

  /// Load persisted settings, then fetch the patient list + active profile.
  Future<void> bootstrap() async {
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString(AppConfig.prefBaseUrl) ?? AppConfig.defaultBaseUrl;
    _activePatientId =
        prefs.getInt(AppConfig.prefActivePatientId) ?? AppConfig.defaultPatientId;
    final themeName = prefs.getString('guardian.theme_mode');
    _themeMode = ThemeMode.values.firstWhere(
      (m) => m.name == themeName,
      orElse: () => ThemeMode.system,
    );
    _initializing = false;
    notifyListeners();
    eventStream.start(); // self-reconnects; survives backend coming up later
    await refreshAll();
  }

  Future<void> setThemeMode(ThemeMode mode) async {
    _themeMode = mode;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('guardian.theme_mode', mode.name);
    notifyListeners();
  }

  Future<void> setBaseUrl(String url) async {
    _baseUrl = url.trim();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConfig.prefBaseUrl, _baseUrl);
    eventStream.reconnect(); // re-point the SSE stream at the new URL
    notifyListeners();
    await refreshAll();
  }

  Future<void> setActivePatient(int id) async {
    if (id == _activePatientId) return;
    _activePatientId = id;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(AppConfig.prefActivePatientId, id);
    _profile = null;
    notifyListeners();
    await loadProfile();
  }

  /// Ping backend, load patient list and the active profile.
  Future<void> refreshAll() async {
    _backendOnline = await api.ping();
    notifyListeners();
    if (!_backendOnline) return;
    try {
      _patients = await api.listPatients();
      // If the active id is not in the list, fall back to the first patient.
      if (_patients.isNotEmpty &&
          !_patients.any((p) => p.id == _activePatientId)) {
        _activePatientId = _patients.first.id;
      }
    } catch (_) {
      // Leave patients as-is; profile load below will surface errors.
    }
    notifyListeners();
    await loadProfile();
  }

  Future<void> loadProfile() async {
    if (!_backendOnline) return;
    try {
      _profile = await api.getPatientProfile(_activePatientId);
    } catch (_) {
      // keep last known profile
    }
    notifyListeners();
  }

  /// Replace the in-memory profile (e.g. after a successful save).
  void setProfile(PatientProfile profile) {
    _profile = profile;
    // Keep the lightweight patient list label in sync.
    _patients = _patients
        .map((p) => p.id == profile.id
            ? Patient(
                id: profile.id,
                name: profile.name,
                age: profile.age,
                conditions: profile.conditions,
                allergies: profile.allergies,
                primaryLanguage: profile.primaryLanguage,
              )
            : p)
        .toList();
    notifyListeners();
  }
}
