import 'dart:io' show Platform;

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/models.dart';

/// Result of probing the device's telephony hardware.
class TelephonyStatus {
  const TelephonyStatus({
    required this.isPhonePlatform,
    required this.hasTelephony,
    required this.simReady,
    this.simState = -1,
  });

  /// Running on Android/iOS (vs. web/desktop).
  final bool isPhonePlatform;

  /// Device exposes telephony hardware (a phone, not a tablet/emulator-no-modem).
  final bool hasTelephony;

  /// A SIM is inserted and ready to place calls.
  final bool simReady;

  /// Raw Android `TelephonyManager.simState` (-1 if unknown / not Android).
  final int simState;

  /// True only when we can actually dial out over the cellular network.
  bool get canCall => isPhonePlatform && hasTelephony && simReady;

  String get reason {
    if (!isPhonePlatform) return 'This device isn\'t a phone, so it can\'t place a call.';
    if (!hasTelephony) return 'No telephony hardware (no cellular modem) was found.';
    if (!simReady) return 'No SIM card is ready. Insert an active SIM to place calls.';
    return 'Ready to call.';
  }

  static const unavailable = TelephonyStatus(
    isPhonePlatform: false,
    hasTelephony: false,
    simReady: false,
  );
}

/// Outcome of a call+speak attempt.
class CallOutcome {
  const CallOutcome({required this.placed, this.spoke = false, this.reason});
  final bool placed;
  final bool spoke;
  final String? reason;
}

/// A phone number Guardian wants us to dial, plus who it belongs to.
class CallTarget {
  const CallTarget({required this.number, this.name, this.toolName});
  final String number;
  final String? name;
  final String? toolName;

  String get label => name == null || name!.isEmpty ? number : '$name ($number)';
}

/// Places real phone calls through the device SIM and speaks a received
/// message aloud (best-effort, on speakerphone).
///
/// Platform reality check: mobile OSes do **not** let a third-party app inject
/// audio into a live cellular voice stream. So "calling with the received
/// voice" is implemented as: dial the number over the SIM, then speak the
/// message through the loudspeaker once the call is (likely) connected. On a
/// phone held to/near the listener — or if the callee has the patient on
/// speaker — the spoken alert is heard. On web/desktop/no-SIM we fall back to
/// opening the dialer or report that calling is unavailable.
class CallService {
  static const MethodChannel _channel = MethodChannel('guardian/telephony');
  final FlutterTts _tts = FlutterTts();
  final AudioPlayer _player = AudioPlayer();
  bool _ttsReady = false;

  bool get _isAndroid => !kIsWeb && Platform.isAndroid;
  bool get _isPhone => !kIsWeb && (Platform.isAndroid || Platform.isIOS);

  /// Probe telephony + SIM. On iOS we can't reliably read SIM state without
  /// special entitlements, so we optimistically assume it's available.
  Future<TelephonyStatus> status() async {
    if (!_isPhone) return TelephonyStatus.unavailable;
    if (!_isAndroid) {
      return const TelephonyStatus(
        isPhonePlatform: true,
        hasTelephony: true,
        simReady: true,
      );
    }
    try {
      final m = await _channel.invokeMapMethod<String, dynamic>('getSimState');
      return TelephonyStatus(
        isPhonePlatform: true,
        hasTelephony: m?['hasTelephony'] == true,
        simReady: m?['simReady'] == true,
        simState: (m?['simState'] as int?) ?? -1,
      );
    } catch (_) {
      return const TelephonyStatus(
        isPhonePlatform: true,
        hasTelephony: false,
        simReady: false,
      );
    }
  }

  /// Ask for CALL_PHONE so we can dial without the user tapping the dialer.
  Future<bool> ensureCallPermission() async {
    if (!_isAndroid) return false;
    final current = await Permission.phone.status;
    if (current.isGranted) return true;
    final result = await Permission.phone.request();
    return result.isGranted;
  }

  /// Dial [number]. With CALL_PHONE granted we place the call directly via the
  /// SIM; otherwise we open the dialer pre-filled (user taps to call).
  Future<bool> placeCall(String number) async {
    final clean = number.trim();
    if (_isAndroid) {
      final granted = await ensureCallPermission();
      try {
        final ok = await _channel.invokeMethod<bool>('placeCall', {
          'number': clean,
          'direct': granted,
        });
        return ok ?? false;
      } catch (_) {
        // fall through to url_launcher
      }
    }
    final uri = Uri(scheme: 'tel', path: clean);
    return launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _initTts() async {
    if (_ttsReady) return;
    try {
      await _tts.awaitSpeakCompletion(true);
      await _tts.setSpeechRate(0.45);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);
    } catch (_) {}
    _ttsReady = true;
  }

  /// Speak [message] aloud. On Android we flip on the speakerphone first so the
  /// alert carries during a call.
  Future<bool> speak(String message, {bool speakerphone = true}) async {
    final text = message.trim();
    if (text.isEmpty) return false;
    await _initTts();
    if (speakerphone && _isAndroid) {
      try {
        await _channel.invokeMethod('setSpeakerphone', {'on': true});
      } catch (_) {}
    }
    try {
      await _tts.speak(text);
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Play a remote audio file (the server's Kokoro WAV) through the speaker.
  Future<bool> playUrl(String url, {bool speakerphone = true}) async {
    if (url.isEmpty) return false;
    if (speakerphone && _isAndroid) {
      try {
        await _channel.invokeMethod('setSpeakerphone', {'on': true});
      } catch (_) {}
    }
    try {
      await _player.stop();
      await _player.play(UrlSource(url));
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> stopSpeaking() async {
    try {
      await _tts.stop();
    } catch (_) {}
    try {
      await _player.stop();
    } catch (_) {}
  }

  /// The headline feature: verify we're on a phone with a SIM, dial [number],
  /// wait for it to connect, then play the voice over the speaker.
  ///
  /// If [audioUrl] is given (the server's Kokoro WAV) we play that; otherwise we
  /// fall back to on-device TTS of [message].
  Future<CallOutcome> callWithVoice({
    required String number,
    required String message,
    String? audioUrl,
    Duration connectDelay = const Duration(seconds: 6),
  }) async {
    final st = await status();
    if (!st.canCall) {
      // Still let non-phone callers open a dialer where possible.
      return CallOutcome(placed: false, reason: st.reason);
    }
    final placed = await placeCall(number);
    // Give the network a moment to connect before we start the voice.
    await Future.delayed(connectDelay);
    bool spoke;
    if (audioUrl != null && audioUrl.isNotEmpty) {
      spoke = await playUrl(audioUrl, speakerphone: true);
      // Fall back to local TTS if the server audio couldn't play.
      if (!spoke) spoke = await speak(message, speakerphone: true);
    } else {
      spoke = await speak(message, speakerphone: true);
    }
    return CallOutcome(placed: placed, spoke: spoke);
  }

  // ---------------------------------------------------------------------------
  // Extract a number Guardian asked us to call from a turn's tool calls.
  // ---------------------------------------------------------------------------

  static final RegExp _phoneLike =
      RegExp(r'(\+?\d[\d\-\s().]{6,}\d)');

  static const _phoneKeys = {
    'phone', 'number', 'phone_number', 'to', 'tel', 'telephone', 'contact_phone'
  };
  static const _nameKeys = {'name', 'contact', 'contact_name', 'who', 'recipient'};

  /// Scan a turn's tool calls for a callable number (e.g. `call_911`,
  /// `call_person`, `alert_emergency_contacts`, `notify_caregiver`).
  static CallTarget? extractCallTarget(List<ToolCall> calls) {
    for (final t in calls) {
      final tool = t.tool.toLowerCase();
      final isCallish = tool.contains('call') ||
          tool.contains('alert') ||
          tool.contains('notify') ||
          tool.contains('contact') ||
          tool.contains('dial') ||
          tool.contains('911');

      if (tool.contains('911')) {
        return CallTarget(number: '911', name: 'Emergency services', toolName: t.tool);
      }
      if (!isCallish) continue;

      final number = _findValue(t.args, _phoneKeys, isPhone: true) ??
          _findValue(t.result, _phoneKeys, isPhone: true);
      if (number != null) {
        final name = _findValue(t.args, _nameKeys) ??
            _findValue(t.result, _nameKeys);
        return CallTarget(number: number, name: name, toolName: t.tool);
      }
    }
    return null;
  }

  /// Recursively search a dynamic JSON value. When [isPhone] is true we first
  /// prefer values under known phone keys, then fall back to phone-like strings.
  static String? _findValue(dynamic node, Set<String> keys,
      {bool isPhone = false}) {
    if (node == null) return null;
    if (node is Map) {
      // 1) preferred keys
      for (final entry in node.entries) {
        final k = entry.key.toString().toLowerCase();
        if (keys.contains(k) && entry.value is String &&
            (entry.value as String).trim().isNotEmpty) {
          final v = (entry.value as String).trim();
          if (!isPhone || _phoneLike.hasMatch(v)) return _normalize(v, isPhone);
        }
      }
      // 2) recurse
      for (final v in node.values) {
        final found = _findValue(v, keys, isPhone: isPhone);
        if (found != null) return found;
      }
    } else if (node is List) {
      for (final v in node) {
        final found = _findValue(v, keys, isPhone: isPhone);
        if (found != null) return found;
      }
    } else if (node is String && isPhone) {
      final m = _phoneLike.firstMatch(node);
      if (m != null) return _normalize(m.group(1)!, true);
    }
    return null;
  }

  static String _normalize(String v, bool isPhone) {
    if (!isPhone) return v.trim();
    // keep leading + and digits
    final plus = v.trim().startsWith('+');
    final digits = v.replaceAll(RegExp(r'[^0-9]'), '');
    return plus ? '+$digits' : digits;
  }
}
