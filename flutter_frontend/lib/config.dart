/// App-wide configuration.
///
/// The backend base URL is configurable at runtime (Settings screen) and
/// persisted, because a phone/emulator cannot reach the developer's
/// `localhost` directly:
///
///   * Android emulator  -> http://10.0.2.2:8000
///   * iOS simulator     -> http://localhost:8000
///   * Real device       -> http://<your-computer-LAN-ip>:8000
///   * Desktop / web      -> http://localhost:8000
///
/// The default below targets the Android emulator, which is the most common
/// case. Change it in Settings (gear icon in the header) if you run elsewhere.
class AppConfig {
  static const String defaultBaseUrl = 'http://10.0.2.2:8000';

  /// Fallback patient id when none has been selected yet.
  static const int defaultPatientId = 1;

  /// SharedPreferences keys.
  static const String prefBaseUrl = 'guardian.base_url';
  static const String prefActivePatientId = 'guardian.active_patient_id';
}
