import 'dart:convert';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:uml_mobile_app/services/api_service.dart';
import 'package:uml_mobile_app/services/dialogue_service.dart';

class Backend {
  final Map<String, dynamic> contract;
  final rows = <String, Map<int, Map<String, dynamic>>>{'cliente': {}, 'pedido': {}};
  final writes = <Map<String, dynamic>>[];
  final pages = <int>[];
  int? rejectWrite;
  late final ApiService api;
  Backend(this.contract) {
    api = ApiService(client: MockClient(handle))..expectedContract = contract;
  }
  Future<http.Response> handle(http.Request r) async {
    http.Response response(dynamic body, [int status = 200]) => http.Response(jsonEncode(body), status);
    if (r.url.path.endsWith('/_meta/contract')) return response(contract);
    final parts = r.url.pathSegments;
    final entity = parts[1];
    final table = rows[entity]!;
    final id = parts.length > 2 ? int.parse(parts[2]) : null;
    if (r.method == 'GET') {
      if (parts.length == 4) return response(rows['pedido']!.values.where((p) => p['clienteId'] == id).map((p) => p['id']).toList());
      if (id != null) return response(table[id], table.containsKey(id) ? 200 : 404);
      final page = int.parse(r.url.queryParameters['page'] ?? '0');
      final size = int.parse(r.url.queryParameters['size'] ?? '20');
      pages.add(page);
      return response(table.values.skip(page * size).take(size).toList());
    }
    final body = r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body) as Map<String, dynamic>;
    writes.add({'method': r.method, 'entity': entity, 'id': id, 'body': body});
    if (rejectWrite != null) return response({'error': 'conflicto'}, rejectWrite!);
    if (r.method == 'DELETE') {
      if (entity == 'cliente' && rows['pedido']!.values.any((p) => p['clienteId'] == id)) return response({}, 409);
      table.remove(id);
      return http.Response('', 204);
    }
    if (r.method == 'PUT') {
      if (table[id]?['entityVersion'] != body['entityVersion']) return response({}, 409);
      table[id!] = {...body, 'id': id, 'entityVersion': (body['entityVersion'] as int) + 1};
      return response(table[id]);
    }
    final next = table.length + 1;
    table[next] = {...body, 'id': next, 'entityVersion': 0};
    return response(table[next], 201);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Backend backend;
  late DialogueService chat;
  setUp(() async {
    backend = Backend(jsonDecode(await rootBundle.loadString('assets/mobile-contract.json')));
    chat = DialogueService(backend.api);
  });
  Future<void> client() async {
    final reply = await chat.send('crear Cliente nombre=Ana; email=ana@example.test');
    expect(reply.changed, isTrue);
  }

  test('collects required fields across turns and creates once', () async {
    expect((await chat.send('crear Cliente')).text, contains('nombre'));
    expect((await chat.send('Ana')).text, contains('email'));
    expect(backend.writes, isEmpty);
    expect((await chat.send('ana@example.test')).changed, isTrue);
    expect(backend.writes.single['body'], {'nombre': 'Ana', 'email': 'ana@example.test'});
  });

  test('creates relationship, edits complete PUT and queries related IDs', () async {
    await client();
    final created = await chat.send('crear Pedido fecha=2026-09-21; total=125.50; estado=PENDIENTE; clienteId=nombre Ana');
    expect(created.changed, isTrue, reason: created.text);
    expect(backend.writes.last['body']['clienteId'], 1);
    final edited = await chat.send('editar Pedido id 1 estado=CONFIRMADO');
    expect(edited.changed, isTrue, reason: edited.text);
    expect(backend.writes.last['body'], {'fecha': '2026-09-21', 'total': 125.50, 'estado': 'CONFIRMADO', 'clienteId': 1, 'entityVersion': 0});
    expect((await chat.send('relaciones Cliente id 1 pedidos')).text, contains('[1]'));
    expect((await chat.send('buscar Pedido id 1')).payload?['estado'], 'CONFIRMADO');
  });

  test('delete requires confirmation, cancellation does not write, FK failure is visible', () async {
    await client();
    expect((await chat.send('eliminar Cliente id 1')).text, contains('confirmar'));
    await chat.send('cancelar');
    expect(backend.writes.length, 1);
    await chat.send('eliminar Cliente id 1');
    backend.rejectWrite = 409;
    final failed = await chat.send('confirmar');
    expect(failed.changed, isFalse);
    expect(failed.text, contains('409'));
    await chat.send('confirmar');
    expect(backend.writes.length, 2, reason: 'No automatic retry');
    backend.rejectWrite = null;
    await chat.send('eliminar Cliente id 1');
    expect((await chat.send('confirmar')).changed, isTrue);
  });

  test('invalid fields and dates do not produce requests; corrected value continues', () async {
    await client();
    expect((await chat.send('crear Pedido fecha=2026-02-30')).text, contains('inválido'));
    expect(backend.writes.length, 1);
    expect((await chat.send('2026-09-21')).text, contains('total'));
    expect((await chat.send('abc')).text, contains('inválido'));
    expect((await chat.send('125.50')).text, contains('estado'));
    expect((await chat.send('PENDIENTE')).text, contains('clienteId'));
    expect((await chat.send('1')).changed, isTrue);
    final bad = await chat.send('crear Cliente telefono=123');
    expect(bad.text, contains('desconocido'));
    expect(backend.writes.length, 2);
  });

  test('ambiguous name requests an exact ID and searches all pages', () async {
    for (var i = 1; i <= 101; i++) {
      backend.rows['cliente']![i] = {'id': i, 'nombre': i == 1 || i == 101 ? 'Ana' : 'Otro', 'email': '$i@example.test', 'entityVersion': 0};
    }
    await chat.send('buscar Cliente');
    final ambiguous = await chat.send('nombre Ana');
    expect(ambiguous.text, contains('Coincidencias: 2'));
    expect(backend.pages, [0, 1]);
    expect((await chat.send('2')).text, contains('no pertenece'));
    expect((await chat.send('101')).payload?['id'], 101);
  });

  test('update prompts changes and reports optimistic version conflict without retry', () async {
    await client();
    expect((await chat.send('editar Cliente id 1')).text, contains('campos'));
    backend.rows['cliente']![1]!['entityVersion'] = 1;
    final reply = await chat.send('email=nuevo@example.test');
    expect(reply.text, contains('409'));
    expect(reply.changed, isFalse);
    expect(backend.writes.last['body']['nombre'], 'Ana');
    expect(backend.writes.last['body']['entityVersion'], 0);
  });

  test('unsuccessful name lookup allows correcting with an ID', () async {
    await client();
    await chat.send('buscar Cliente');
    expect((await chat.send('nombre Inexistente')).text, contains('No hay coincidencias'));
    expect((await chat.send('1')).payload?['nombre'], 'Ana');
  });

  test('strict scalar types', () {
    expect(chat.scalar('no', 'Boolean'), isFalse);
    expect(chat.scalar('ABC-123', 'String'), 'ABC-123');
    for (final pair in [['quizas', 'Boolean'], ['NaN', 'Double'], ['1.2', 'Integer'], ['2026-02-30', 'LocalDate'], ['2026-09-21T25:00:00', 'LocalDateTime']]) {
      expect(() => chat.scalar(pair[0], pair[1]), throwsFormatException);
    }
  });

  test('simultaneous sends cannot duplicate a creation', () async {
    final gate = Completer<void>();
    final api = ApiService(client: MockClient((request) async {
      if (request.url.path.endsWith('/_meta/contract')) await gate.future;
      return backend.handle(request);
    }))..expectedContract = backend.contract;
    final dialogue = DialogueService(api);
    final first = dialogue.send('crear Cliente nombre=Ana; email=ana@example.test');
    final repeated = await dialogue.send('crear Cliente nombre=Ana; email=ana@example.test');
    expect(repeated.text, contains('en curso'));
    gate.complete();
    expect((await first).changed, isTrue);
    expect(backend.writes.length, 1);
  });

  test('correcting an invalid update continues without losing other fields', () async {
    await client();
    await chat.send('crear Pedido fecha=2026-09-21; total=1; estado=PENDIENTE; clienteId=1');
    await chat.send('editar Pedido id 1');
    expect((await chat.send('total=abc')).text, contains('inválido'));
    expect((await chat.send('10.50')).changed, isTrue);
    expect(backend.writes.last['body']['fecha'], '2026-09-21');
    expect(backend.writes.last['body']['total'], 10.50);
  });

  test('assigned text key and boolean no are supported through dialogue', () async {
    final contract = <String, dynamic>{'format_version': 1, 'fingerprint': 'test-product', 'entities': [
      {'name': 'Producto', 'endpoint': '/producto', 'primary_key': {'name': 'codigo', 'type': 'String', 'generated': false},
       'attributes': [
         {'name': 'codigo', 'type': 'String', 'is_pk': true, 'is_nullable': false},
         {'name': 'activo', 'type': 'Boolean', 'is_pk': false, 'is_nullable': false}],
       'request_fields': ['codigo', 'activo', 'entityVersion'], 'relationships': []}
    ]};
    Map<String, dynamic>? record;
    final api = ApiService(client: MockClient((r) async {
      if (r.url.path.endsWith('/_meta/contract')) return http.Response(jsonEncode(contract), 200);
      if (r.method == 'GET') return http.Response(jsonEncode(record), 200);
      record = {...jsonDecode(r.body), 'entityVersion': 0};
      return http.Response(jsonEncode(record), r.method == 'POST' ? 201 : 200);
    }))..expectedContract = contract;
    final dialogue = DialogueService(api);
    expect((await dialogue.send('crear Producto')).text, contains('codigo'));
    expect((await dialogue.send('ABC-123')).text, contains('activo'));
    expect((await dialogue.send('no')).changed, isTrue);
    expect(record?['codigo'], 'ABC-123');
    expect(record?['activo'], isFalse);
    final update = await dialogue.send('editar Producto id ABC-123 activo=si');
    expect(update.changed, isTrue, reason: update.text);
    expect(record?['codigo'], 'ABC-123');
    expect(record?['activo'], isTrue);
  });
}
