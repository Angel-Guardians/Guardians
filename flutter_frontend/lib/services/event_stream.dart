import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// One event off the backend SSE stream (`GET /events/sse`).
/// Shape: `{id, kind, ts, summary, payload}`.
class SseEvent {
  SseEvent({
    required this.id,
    required this.kind,
    required this.summary,
    required this.payload,
  });

  final String id;
  final String kind;
  final String summary;
  final Map<String, dynamic> payload;
}

/// Long-lived Server-Sent-Events client for the Guardian backend.
///
/// Connects to `{baseUrl}/events/sse`, parses the `data:` frames, and exposes a
/// broadcast [events] stream. Auto-reconnects (with backoff) whenever the
/// connection drops or the backend is briefly unreachable.
class EventStreamService {
  EventStreamService(this._baseUrl);

  final String Function() _baseUrl;

  final _controller = StreamController<SseEvent>.broadcast();
  Stream<SseEvent> get events => _controller.stream;

  http.Client? _client;
  bool _running = false;
  bool _connected = false;
  bool get connected => _connected;

  void start() {
    if (_running) return;
    _running = true;
    _loop();
  }

  /// Force the current connection to drop so the loop reconnects (e.g. after
  /// the backend URL changed in Settings).
  void reconnect() {
    _client?.close();
    _client = null;
  }

  Future<void> _loop() async {
    while (_running) {
      try {
        await _connectOnce();
      } catch (_) {
        // swallow; we retry below
      } finally {
        _connected = false;
        _client?.close();
        _client = null;
      }
      if (!_running) break;
      await Future<void>.delayed(const Duration(seconds: 3));
    }
  }

  Future<void> _connectOnce() async {
    final base = _baseUrl().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.parse('$base/events/sse');
    final client = http.Client();
    _client = client;
    final req = http.Request('GET', uri)
      ..headers['Accept'] = 'text/event-stream'
      ..headers['Cache-Control'] = 'no-cache';
    final resp = await client.send(req);
    if (resp.statusCode != 200) {
      throw http.ClientException('SSE ${resp.statusCode}', uri);
    }
    _connected = true;

    var buffer = '';
    await for (final chunk in resp.stream.transform(utf8.decoder)) {
      if (!_running) break;
      buffer += chunk;
      // SSE events are separated by a blank line.
      int sep;
      while ((sep = buffer.indexOf('\n\n')) != -1) {
        final rawEvent = buffer.substring(0, sep);
        buffer = buffer.substring(sep + 2);
        _emit(rawEvent);
      }
    }
  }

  void _emit(String rawEvent) {
    final dataLines = <String>[];
    for (final line in rawEvent.split('\n')) {
      final l = line.replaceAll('\r', '');
      if (l.startsWith('data:')) {
        dataLines.add(l.substring(5).trimLeft());
      }
    }
    if (dataLines.isEmpty) return;
    try {
      final obj = jsonDecode(dataLines.join('\n')) as Map<String, dynamic>;
      _controller.add(SseEvent(
        id: '${obj['id']}',
        kind: '${obj['kind']}',
        summary: '${obj['summary'] ?? ''}',
        payload: (obj['payload'] as Map?)?.cast<String, dynamic>() ??
            <String, dynamic>{},
      ));
    } catch (e) {
      if (kDebugMode) debugPrint('SSE parse error: $e');
    }
  }

  void stop() {
    _running = false;
    _connected = false;
    _client?.close();
    _client = null;
  }

  void dispose() {
    stop();
    _controller.close();
  }
}
