import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/models.dart';

/// Thrown when the backend responds with a non-2xx status.
class ApiException implements Exception {
  ApiException(this.message, [this.status]);
  final String message;
  final int? status;
  @override
  String toString() => message;
}

/// Typed client for the Guardian FastAPI backend.
///
/// Mirrors `frontend/src/lib/api.ts`. The base URL is supplied via a callback
/// so the Settings screen can change it at runtime.
class ApiClient {
  ApiClient(this._baseUrl);

  /// A getter so a single client instance always reads the latest URL.
  final String Function() _baseUrl;

  Uri _uri(String path, [Map<String, dynamic>? query]) {
    final base = _baseUrl().replaceAll(RegExp(r'/+$'), '');
    final q = query?.map((k, v) => MapEntry(k, '$v'));
    return Uri.parse('$base$path').replace(
      queryParameters: q == null || q.isEmpty ? null : q,
    );
  }

  Future<dynamic> _getJson(String path, [Map<String, dynamic>? query]) async {
    final res = await http
        .get(_uri(path, query), headers: {'Accept': 'application/json'})
        .timeout(const Duration(seconds: 20));
    return _decode(res, 'GET $path');
  }

  Future<dynamic> _send(String method, String path, {Object? body}) async {
    final req = http.Request(method, _uri(path));
    req.headers['Accept'] = 'application/json';
    if (body != null) {
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
    }
    final streamed = await req.send().timeout(const Duration(seconds: 30));
    final res = await http.Response.fromStream(streamed);
    return _decode(res, '$method $path');
  }

  dynamic _decode(http.Response res, String label) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw ApiException('$label → ${res.statusCode}', res.statusCode);
    }
    if (res.body.isEmpty) return null;
    return jsonDecode(res.body);
  }

  // --- Health -------------------------------------------------------------

  Future<bool> ping() async {
    try {
      await _getJson('/ping');
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> health() async =>
      (await _getJson('/health')) as Map<String, dynamic>;

  // --- Patients -----------------------------------------------------------

  Future<List<Patient>> listPatients() async {
    final data = await _getJson('/patient/') as List;
    return data.map((e) => Patient.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PatientProfile> getPatientProfile(int id) async {
    final data = await _getJson('/patient/$id/profile') as Map<String, dynamic>;
    return PatientProfile.fromJson(data);
  }

  Future<PatientProfile> updatePatientProfile(
      int id, PatientProfile profile) async {
    final data =
        await _send('PUT', '/patient/$id/profile', body: profile.toUpdateJson())
            as Map<String, dynamic>;
    return PatientProfile.fromJson(data);
  }

  // --- Talk to Guardian ---------------------------------------------------

  Future<TurnResponse> turn(String text, int patientId) async {
    final data = await _send('POST', '/turn/',
        body: {'text': text, 'patient_id': patientId}) as Map<String, dynamic>;
    return TurnResponse.fromJson(data);
  }

  // --- Vitals -------------------------------------------------------------

  Future<VitalSeries> getVitals(String kind,
      {String since = '24h', int? patientId}) async {
    final data = await _getJson('/vitals', {
      'kind': kind,
      'since': since,
      if (patientId != null) 'patient_id': patientId,
    }) as Map<String, dynamic>;
    return VitalSeries.fromJson(data);
  }

  Future<List<FallEvent>> getFalls(
      {String since = '24h', int? patientId}) async {
    final data = await _getJson('/vitals/falls', {
      'since': since,
      if (patientId != null) 'patient_id': patientId,
    }) as List;
    return data
        .map((e) => FallEvent.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // --- Location -----------------------------------------------------------

  Future<List<LocationPoint>> getLocations(
      {String since = '24h', required int patientId}) async {
    final data = await _getJson('/location', {
      'since': since,
      'patient_id': patientId,
    }) as List;
    return data
        .map((e) => LocationPoint.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // --- Medications / reminders -------------------------------------------

  Future<List<Medication>> listMedications(int patientId) async {
    final data =
        await _getJson('/medications', {'patient_id': patientId}) as List;
    return data
        .map((e) => Medication.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> confirmIntake(int medicationId) async {
    await _send('POST', '/events',
        body: {'kind': 'tap_confirmed', 'medication_id': medicationId});
  }

  // --- Lab / medical-history records --------------------------------------

  Future<List<LabReport>> listLabRecords(int patientId) async {
    final data =
        await _getJson('/lab-records', {'patient_id': patientId}) as List;
    return data
        .map((e) => LabReport.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<LabReportDetail> getLabRecord(int reportId) async {
    final data =
        await _getJson('/lab-records/$reportId') as Map<String, dynamic>;
    return LabReportDetail.fromJson(data);
  }

  Future<void> deleteLabRecord(int reportId) async {
    await _send('DELETE', '/lab-records/$reportId');
  }

  /// Upload a PDF of lab results. [bytes] is required on web; on mobile/desktop
  /// the picker also gives bytes, so we always send bytes.
  Future<LabUploadResult> uploadLabRecord({
    required int patientId,
    required String filename,
    required List<int> bytes,
    String source = 'lifelabs_upload',
  }) async {
    final req = http.MultipartRequest('POST', _uri('/lab-records/upload'));
    req.headers['Accept'] = 'application/json';
    req.fields['patient_id'] = '$patientId';
    req.fields['source'] = source;
    req.files.add(http.MultipartFile.fromBytes('file', bytes,
        filename: filename));
    final streamed = await req.send().timeout(const Duration(seconds: 120));
    final res = await http.Response.fromStream(streamed);
    final data = _decode(res, 'POST /lab-records/upload') as Map<String, dynamic>;
    return LabUploadResult.fromJson(data);
  }
}
