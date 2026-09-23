import 'dart:convert';
import 'api_service.dart';

class DialogueReply {
  final String text;
  final Map<String, dynamic>? payload;
  final bool changed;
  DialogueReply(this.text, {this.payload, this.changed = false});
}

class _Operation {
  final String action;
  final Map<String, dynamic> entity;
  final Map<String, dynamic> data = {};
  final Map<String, String> inputs = {};
  dynamic id;
  String? field;
  String? role;
  bool confirm = false;
  bool loaded = false;
  bool needsChanges = false;
  bool edited = false;
  List<Map<String, dynamic>>? candidates;
  _Operation(this.action, this.entity);
}

/// Local, deterministic dialogue. No cloud service and no arbitrary code execution.
class DialogueService {
  final ApiService api;
  _Operation? _pending;
  String? _server;
  bool _busy = false;
  DialogueService(this.api);

  static const help = 'Conecta el servidor y escribe: crear Cliente; listar Cliente; '
      'buscar Cliente id 1; editar Cliente id 1 email=ana@example.test; '
      'eliminar Cliente id 1; relaciones Cliente id 1 pedidos. '
      'Para varios campos: nombre=Ana; email=ana@example.test. '
      'Puedes responder a cada pregunta o escribir cancelar.';

  List<Map<String, dynamic>> get _entities =>
      (api.expectedContract?['entities'] as List? ?? []).map((e) => Map<String, dynamic>.from(e)).toList();

  Map<String, Map<String, dynamic>> fields(Map<String, dynamic> entity) {
    final result = <String, Map<String, dynamic>>{};
    for (final a in entity['attributes'] as List) {
      if (!(entity['request_fields'] as List).contains(a['name'])) continue;
      result[a['name']] = {...Map<String, dynamic>.from(a), 'required': a['is_nullable'] != true};
    }
    for (final r in entity['relationships'] as List) {
      if (r['writable'] == true) result[r['field']] = Map<String, dynamic>.from(r);
    }
    return result;
  }

  Map<String, String> _extract(String text, Iterable<String> names) {
    for (final assignment in RegExp(r'(?:^|[;\s])([A-Za-z]\w*)\s*=').allMatches(text)) {
      if (!names.any((n) => n.toLowerCase() == assignment[1]!.toLowerCase())) {
        throw FormatException('Campo desconocido o de solo lectura: ${assignment[1]}');
      }
    }
    if (names.isEmpty) return {};
    final pattern = RegExp('\\b(${names.map(RegExp.escape).join('|')})\\s*(?:[=:]\\s*|\\s+)', caseSensitive: false);
    final matches = pattern.allMatches(text).toList();
    final out = <String, String>{};
    for (var i = 0; i < matches.length; i++) {
      final m = matches[i];
      final name = names.firstWhere((n) => n.toLowerCase() == m[1]!.toLowerCase());
      if (out.containsKey(name)) throw FormatException('Campo repetido: $name');
      var value = text.substring(m.end, i + 1 < matches.length ? matches[i + 1].start : text.length).trim();
      value = value.replaceAll(RegExp(r'[;,]\s*$'), '').trim();
      if (value.startsWith('"') && value.endsWith('"') && value.length >= 2) value = value.substring(1, value.length - 1);
      out[name] = value;
    }
    return out;
  }

  dynamic scalar(String value, String type, {bool nullable = false}) {
    if (value.toLowerCase() == 'null') {
      if (nullable) return null;
      throw const FormatException('El campo es obligatorio.');
    }
    if (value.isEmpty) throw const FormatException('Introduce un valor.');
    if (type == 'String') return value;
    if (type == 'Boolean') {
      if (['true', 'si', 'sí'].contains(value.toLowerCase())) return true;
      if (['false', 'no'].contains(value.toLowerCase())) return false;
      throw const FormatException('Usa sí/no o true/false.');
    }
    if (type == 'Integer' || type == 'Long') {
      final number = int.tryParse(value);
      if (number == null || (type == 'Integer' && (number < -2147483648 || number > 2147483647))) {
        throw FormatException('Se requiere un $type válido.');
      }
      return number;
    }
    if (['Double', 'Float', 'BigDecimal'].contains(type)) {
      final number = num.tryParse(value);
      if (number == null || !number.isFinite) throw const FormatException('Usa un número finito con punto decimal, por ejemplo 125.50.');
      return number;
    }
    if (type == 'LocalDate' || type == 'LocalDateTime') {
      final datePattern = type == 'LocalDate' ? r'^\d{4}-\d{2}-\d{2}$' : r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$';
      final date = DateTime.tryParse(value);
      if (!RegExp(datePattern).hasMatch(value) || date == null || !date.toIso8601String().startsWith(value)) {
        throw FormatException(type == 'LocalDate' ? 'Usa una fecha válida AAAA-MM-DD.' : 'Usa fecha y hora válidas AAAA-MM-DDTHH:mm:ss.');
      }
      return value;
    }
    throw FormatException('Tipo no soportado: $type');
  }

  Future<List<Map<String, dynamic>>> _findByName(Map<String, dynamic> entity, String name) async {
    final names = (entity['attributes'] as List).where((a) => a['type'] == 'String' && a['is_pk'] != true).map((a) => a['name']).toList();
    if (names.isEmpty) throw const FormatException('Esta entidad no tiene campos de texto para buscar. Indica el ID.');
    final found = <Map<String, dynamic>>[];
    for (var page = 0; page < 10; page++) {
      final batch = await api.listRecords(entity['endpoint'], page: page, size: 100);
      found.addAll(batch.where((record) => names.any((n) => record[n]?.toString().toLowerCase() == name.toLowerCase())));
      if (batch.length < 100) return found;
    }
    throw const FormatException('Búsqueda limitada a 1000 registros. Indica el ID para evitar una selección incompleta.');
  }

  Future<dynamic> _value(String text, Map<String, dynamic> field) async {
    if (field.containsKey('entity')) {
      final target = _entities.where((e) => e['name'] == field['entity']).toList();
      if (target.isEmpty) throw const FormatException('El destino no dispone de CRUD.');
      if (text == 'null' && field['required'] != true) return null;
      final pk = target.single['primary_key'];
      if (field['many'] == true) {
        final decoded = jsonDecode(text);
        if (decoded is! List || decoded.length < field['minimum'] || decoded.length > field['input_maximum']) {
          throw const FormatException('Introduce una lista JSON de IDs dentro de los límites de la relación.');
        }
        final ids = <dynamic>[];
        for (final item in decoded) {
          final id = scalar(item.toString(), pk['type']);
          await api.getRecord(target.single['endpoint'], id);
          if (!ids.contains(id)) ids.add(id);
        }
        if (ids.length < field['minimum']) throw const FormatException('Faltan IDs distintos.');
        return ids;
      }
      dynamic id;
      if (text.toLowerCase().startsWith('nombre ')) {
        final matches = await _findByName(target.single, text.substring(7).trim());
        if (matches.length != 1) throw FormatException('Coincidencias: ${matches.map((r) => r[pk['name']]).toList()}. Responde con el ID exacto.');
        id = matches.single[pk['name']];
      } else {
        id = scalar(text.replaceFirst(RegExp(r'^id\s+', caseSensitive: false), ''), pk['type']);
      }
      await api.getRecord(target.single['endpoint'], id);
      return id;
    }
    final value = scalar(text, field['type'], nullable: field['required'] != true);
    if (value is String && field['max_length'] != null && value.length > field['max_length']) {
      throw FormatException('Máximo ${field['max_length']} caracteres.');
    }
    return value;
  }

  Future<DialogueReply> send(String input) async {
    if (_busy) return DialogueReply('Hay una operación en curso. Espera su respuesta.');
    _busy = true;
    try {
      final text = input.trim();
      if (text.toLowerCase() == 'cancelar' || (text.toLowerCase() == 'no' && _pending?.confirm == true)) {
        _pending = null;
        return DialogueReply('Operación cancelada.');
      }
      if (text.toLowerCase() == 'ayuda') return DialogueReply(help);
      if (_pending != null && _server != api.baseUrl) {
        _pending = null;
        return DialogueReply('Cambió el servidor. Operación cancelada; introduce de nuevo la instrucción.');
      }
      await api.checkContract();
      _server = api.baseUrl;
      if (_pending == null) {
        final match = RegExp(r'^(crear|crea|registrar|listar|lista|buscar|consultar|editar|actualizar|cambiar|eliminar|borrar|relaciones)\s+(?:un\s+|una\s+)?([\w]+)\b\s*(.*)$', caseSensitive: false).firstMatch(text);
        if (match == null) return DialogueReply(help);
        final action = switch (match[1]!.toLowerCase()) {
          'crear' || 'crea' || 'registrar' => 'create',
          'listar' || 'lista' => 'list',
          'buscar' || 'consultar' => 'get',
          'editar' || 'actualizar' || 'cambiar' => 'update',
          'relaciones' => 'relation',
          _ => 'delete',
        };
        final noun = match[2]!.toLowerCase();
        final matches = _entities.where((e) => [e['name'].toString().toLowerCase(), '${e['name'].toString().toLowerCase()}s', '${e['name'].toString().toLowerCase()}es'].contains(noun)).toList();
        if (matches.length != 1) return DialogueReply('Indica una entidad exacta: ${_entities.map((e) => e['name']).join(', ')}.');
        final entity = matches.single;
        var tail = match[3]!.trim();
        if (action == 'list') {
          final page = tail.isEmpty ? 0 : int.tryParse(tail.replaceFirst('pagina ', ''));
          if (page == null || page < 0) return DialogueReply('Usa listar ${entity['name']} pagina 0.');
          final records = await api.listRecords(entity['endpoint'], page: page);
          return DialogueReply('Página $page: ${records.length} registros. Para continuar: listar ${entity['name']} pagina ${page + 1}.', payload: {'records': records});
        }
        _pending = _Operation(action, entity);
        final op = _pending!;
        if (action != 'create') {
          final id = RegExp(r'^id\s+("[^"]+"|[^\s;,]+)\s*[;,]?\s*(.*)$', caseSensitive: false).firstMatch(tail);
          if (id != null) {
            op.id = scalar(id[1]!.replaceAll('"', ''), entity['primary_key']['type']);
            tail = id[2]!;
          }
        } else if (tail.startsWith('llamado ') && fields(entity).containsKey('nombre')) {
          tail = 'nombre=${tail.substring(8)}';
        }
        if (action == 'relation' && op.id != null) {
          op.role = tail;
        } else {
          op.inputs.addAll(_extract(tail, fields(entity).keys));
          if (action == 'create' && tail.isNotEmpty && op.inputs.isEmpty) {
            return DialogueReply('Usa campo=valor o responde las preguntas. Campos: ${fields(entity).keys.join(', ')}. Escribe continuar.');
          }
        }
      } else {
        final op = _pending!;
        if (op.confirm) {
          if (!['confirmar', 'si', 'sí'].contains(text.toLowerCase())) return DialogueReply('Escribe confirmar para borrar o cancelar.');
          _pending = null; // Never automatically retry a mutation with uncertain outcome.
          await api.deleteRecord(op.entity['endpoint'], op.id);
          return DialogueReply('${op.entity['name']} ID ${op.id} eliminado.', changed: true);
        }
        if (op.field != null) {
          final field = op.field!;
          op.data[field] = await _value(text, fields(op.entity)[field]!);
          op.inputs.remove(field);
          op.edited = true;
          op.field = null;
        } else if (op.action != 'create' && op.id == null) {
          final pk = op.entity['primary_key'];
          if (text.toLowerCase().startsWith('nombre ')) {
            op.candidates = await _findByName(op.entity, text.substring(7).trim());
            if (op.candidates!.isEmpty) {
              op.candidates = null;
              return DialogueReply('No hay coincidencias. Indica un ID, busca otro nombre o cancela.');
            }
            if (op.candidates!.length == 1) {
              op.id = op.candidates!.single[pk['name']];
            } else {
              return DialogueReply('Coincidencias: ${op.candidates!.length}. Indica el ID exacto o cancelar.', payload: {'records': op.candidates!});
            }
          } else {
            final id = scalar(text.replaceFirst(RegExp(r'^id\s+', caseSensitive: false), ''), pk['type']);
            if (op.candidates != null && !op.candidates!.any((r) => r[pk['name']] == id)) throw const FormatException('El ID no pertenece a las coincidencias mostradas.');
            op.id = id;
          }
        } else if (op.action == 'relation') {
          op.role = text;
        } else if (op.needsChanges) {
          op.inputs.addAll(_extract(text, fields(op.entity).keys));
        }
      }
      return await _advance();
    } on FormatException catch (e) {
      return DialogueReply('Dato inválido: ${e.message} Puedes corregirlo o cancelar.');
    } catch (e) {
      _pending = null;
      return DialogueReply('No se pudo completar: $e. No se reintentó la escritura. Consulta el registro antes de repetir si hubo un fallo de red.');
    } finally {
      _busy = false;
    }
  }

  Future<DialogueReply> _advance() async {
    final op = _pending!;
    final entity = op.entity;
    if (op.action != 'create' && op.id == null) return DialogueReply('Indica el ID de ${entity['name']} o escribe nombre seguido del valor exacto.');
    if (op.action == 'get') {
      final record = await api.getRecord(entity['endpoint'], op.id);
      _pending = null;
      return DialogueReply('Registro consultado.', payload: record);
    }
    if (op.action == 'relation') {
      final roles = (entity['relationships'] as List).map((r) => r['name']).toList();
      if (!roles.contains(op.role)) return DialogueReply('Indica la relación: ${roles.join(', ')}.');
      final result = await api.getRelation(entity['endpoint'], op.id, op.role!);
      _pending = null;
      return DialogueReply('Identificadores relacionados (${op.role}): ${jsonEncode(result)}');
    }
    if (op.action == 'delete') {
      final record = await api.getRecord(entity['endpoint'], op.id);
      op.confirm = true;
      return DialogueReply('¿Eliminar ${entity['name']} ID ${op.id}? Escribe confirmar o cancelar.', payload: record);
    }
    if (op.action == 'update' && !op.loaded) {
      final record = await api.getRecord(entity['endpoint'], op.id);
      for (final name in entity['request_fields'] as List) {
        op.data[name] = record[name];
      }
      op.loaded = true;
    }
    if (op.action == 'update' && op.inputs.isEmpty && !op.needsChanges && !op.edited) {
      op.needsChanges = true;
      return DialogueReply('¿Qué campos deseas cambiar? Usa campo=valor; campos: ${fields(entity).keys.where((f) => f != entity['primary_key']['name']).join(', ')}.');
    }
    if (op.needsChanges && op.inputs.isEmpty && !op.edited) return DialogueReply('Indica al menos un campo=valor o cancelar.');
    final definitions = fields(entity);
    for (final entry in op.inputs.entries.toList()) {
      if (op.action == 'update' && entry.key == entity['primary_key']['name']) throw const FormatException('La clave primaria no se puede editar.');
      op.field = entry.key;
      op.data[entry.key] = await _value(entry.value, definitions[entry.key]!);
      op.edited = true;
      op.inputs.remove(entry.key);
      op.field = null;
    }
    op.needsChanges = false;
    for (final entry in definitions.entries) {
      if (entry.value['required'] == true && op.data[entry.key] == null) {
        op.field = entry.key;
        return DialogueReply('Indica ${entry.key} (${entry.value['type']}${entry.value['many'] == true ? ', lista JSON de IDs' : ''}).${entry.value.containsKey('entity') ? ' Relación con ${entry.value['entity']}: ID o nombre exacto precedido de nombre.' : ''}');
      }
    }
    _pending = null;
    final result = op.action == 'create'
        ? await api.createRecord(entity['endpoint'], op.data)
        : await api.updateRecord(entity['endpoint'], op.id, op.data);
    return DialogueReply('${entity['name']} ${op.action == 'create' ? 'creado' : 'actualizado'} correctamente.', payload: result, changed: true);
  }
}
