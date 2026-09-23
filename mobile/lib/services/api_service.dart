import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../core/constants/app_constants.dart';

class ApiService extends ChangeNotifier {
  final http.Client _client;
  Map<String, dynamic>? expectedContract;
  ApiService({http.Client? client}) : _client = client ?? http.Client();

  Future<Map<String, dynamic>> checkContract() async {
    final server = _baseUrl;
    final expected = expectedContract;
    if (expected == null) throw StateError('No hay descriptor local cargado.');
    final response = await _client.get(Uri.parse('$server/_meta/contract'), headers: _headers).timeout(AppConstants.apiTimeout);
    if (server != _baseUrl) throw StateError('El servidor cambio durante la comprobacion. Vuelve a conectar.');
    if (response.statusCode != 200) throw Exception('Contrato no disponible (HTTP ${response.statusCode}). Regenera Spring con sprint 8.');
    final remote = jsonDecode(utf8.decode(response.bodyBytes));
    if (remote is! Map || remote['format_version'] != 1 || remote['fingerprint'] != expected['fingerprint']) {
      throw Exception('Backend incompatible con esta app. Revisa la URL o regenera ambos proyectos.');
    }
    return expected;
  }

  String _baseUrl = AppConstants.defaultBackendUrl;

  String get baseUrl => _baseUrl;

  Future<void> init() async {
    expectedContract = jsonDecode(await rootBundle.loadString('assets/mobile-contract.json')) as Map<String, dynamic>;
    final prefs = await SharedPreferences.getInstance();
    _baseUrl = prefs.getString(AppConstants.prefBackendUrlKey) ?? AppConstants.defaultBackendUrl;
  }

  Future<void> setBaseUrl(String url) async {
    final normalized = url.trim().replaceAll(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(normalized);
    if (uri == null || !['http', 'https'].contains(uri.scheme) || uri.host.isEmpty || uri.userInfo.isNotEmpty || uri.hasQuery || uri.hasFragment || uri.path != '/api') {
      throw FormatException('Usa http(s)://servidor:puerto/api, sin credenciales ni parametros.');
    }
    _baseUrl = normalized;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(AppConstants.prefBackendUrlKey, _baseUrl);
    notifyListeners();
  }

  Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  /// List entities from Spring Boot endpoint
  Future<List<Map<String, dynamic>>> listRecords(String endpoint, {int page = 0, int size = 20}) async {
    final uri = Uri.parse('$_baseUrl$endpoint').replace(queryParameters: {'page': '$page', 'size': '$size'});
    final response = await _client.get(uri, headers: _headers).timeout(AppConstants.apiTimeout);
    
    if (response.statusCode == 200) {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is List) {
        return decoded.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      }
      if (decoded is Map && decoded.containsKey('content')) {
        return (decoded['content'] as List).map((e) => Map<String, dynamic>.from(e as Map)).toList();
      }
      throw const FormatException('La respuesta no contiene una lista de registros.');
    } else {
      throw Exception('Error al obtener registros: ${response.statusCode} - ${response.body}');
    }
  }

  /// Get single record by ID
  Future<Map<String, dynamic>> getRecord(String endpoint, dynamic id) async {
    final uri = Uri.parse('$_baseUrl$endpoint/${Uri.encodeComponent(id.toString())}');
    final response = await _client.get(uri, headers: _headers).timeout(AppConstants.apiTimeout);
    
    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(utf8.decode(response.bodyBytes)));
    } else {
      throw Exception('Error al obtener registro: ${response.statusCode}');
    }
  }

  /// Create new record (POST)
  Future<Map<String, dynamic>> createRecord(String endpoint, Map<String, dynamic> data) async {
    final uri = Uri.parse('$_baseUrl$endpoint');
    final response = await _client
        .post(uri, headers: _headers, body: jsonEncode(data))
        .timeout(AppConstants.apiTimeout);
    
    if (response.statusCode == 200 || response.statusCode == 201) {
      return Map<String, dynamic>.from(jsonDecode(utf8.decode(response.bodyBytes)));
    } else {
      throw Exception('Error al crear registro: ${response.statusCode} - ${response.body}');
    }
  }

  /// Update record (PUT)
  Future<Map<String, dynamic>> updateRecord(String endpoint, dynamic id, Map<String, dynamic> data) async {
    final uri = Uri.parse('$_baseUrl$endpoint/${Uri.encodeComponent(id.toString())}');
    final response = await _client
        .put(uri, headers: _headers, body: jsonEncode(data))
        .timeout(AppConstants.apiTimeout);
    
    if (response.statusCode == 200) {
      return Map<String, dynamic>.from(jsonDecode(utf8.decode(response.bodyBytes)));
    } else {
      throw Exception('Error al actualizar registro: ${response.statusCode} - ${response.body}');
    }
  }

  /// Delete record (DELETE)
  Future<bool> deleteRecord(String endpoint, dynamic id) async {
    final uri = Uri.parse('$_baseUrl$endpoint/${Uri.encodeComponent(id.toString())}');
    final response = await _client.delete(uri, headers: _headers).timeout(AppConstants.apiTimeout);
    if (response.statusCode == 200 || response.statusCode == 204) return true;
    throw Exception('No se eliminó el registro: HTTP ${response.statusCode}. ${response.body}');
  }

  Future<dynamic> getRelation(String endpoint, dynamic id, String role) async {
    final uri = Uri.parse('$_baseUrl$endpoint/${Uri.encodeComponent(id.toString())}/${Uri.encodeComponent(role)}');
    final response = await _client.get(uri, headers: _headers).timeout(AppConstants.apiTimeout);
    if (response.statusCode != 200) throw Exception('Consulta relacional: HTTP ${response.statusCode}');
    return jsonDecode(utf8.decode(response.bodyBytes));
  }
}
