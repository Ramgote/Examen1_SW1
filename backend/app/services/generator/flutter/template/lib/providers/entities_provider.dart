import 'package:flutter/material.dart';
import '../models/entity_schema.dart';
import '../services/api_service.dart';

class EntitiesProvider extends ChangeNotifier {
  final ApiService _apiService;
  ApiService get api => _apiService;
  
  List<EntitySchema> _schemas = [];
  Map<String, List<Map<String, dynamic>>> _recordsByEntity = {};
  bool _isLoading = false;
  String? _error;

  bool _connected = false;
  bool get isConnected => _connected;
  EntitiesProvider(this._apiService) {
    _apiService.addListener(_resetConnection);
  }
  void _resetConnection() {
    _connected = false;
    _schemas = [];
    _recordsByEntity = {};
    _error = null;
    notifyListeners();
  }
  @override
  void dispose() {
    _apiService.removeListener(_resetConnection);
    super.dispose();
  }

  List<EntitySchema> get schemas => _schemas;
  Map<String, List<Map<String, dynamic>>> get recordsByEntity => _recordsByEntity;
  bool get isLoading => _isLoading;
  String? get error => _error;

  Future<void> fetchAllRecords() async {
    if (_isLoading) return;
    _isLoading = true;
    _connected = false;
    _error = null;
    _recordsByEntity = {};
    notifyListeners();
    final url = _apiService.baseUrl;
    try {
      final contract = await _apiService.checkContract();
      final schemas = (contract['entities'] as List).map((e) => EntitySchema.fromJson(Map<String, dynamic>.from(e))).toList();
      final records = <String, List<Map<String, dynamic>>>{};
      for (final schema in schemas) {
        records[schema.name] = await _apiService.listRecords(schema.endpoint);
      }
      if (url != _apiService.baseUrl) return;
      _schemas = schemas;
      _recordsByEntity = records;
      _connected = true;
    } catch (e) {
      if (url == _apiService.baseUrl) _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<Map<String, dynamic>> createEntityRecord(String entityName, Map<String, dynamic> data) async {
    await _apiService.checkContract();
    final schema = _schemas.firstWhere(
      (s) => s.name.toLowerCase() == entityName.toLowerCase(),
      orElse: () => throw Exception('Entidad $entityName no encontrada'),
    );
    final result = await _apiService.createRecord(schema.endpoint, data);
    await fetchAllRecords();
    return result;
  }

  Future<bool> deleteEntityRecord(String entityName, dynamic id) async {
    await _apiService.checkContract();
    final schema = _schemas.firstWhere(
      (s) => s.name.toLowerCase() == entityName.toLowerCase(),
      orElse: () => throw Exception('Entidad $entityName no encontrada'),
    );
    final ok = await _apiService.deleteRecord(schema.endpoint, id);
    if (ok) {
      await fetchAllRecords();
    }
    return ok;
  }
}
