import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uml_mobile_app/services/api_service.dart';
import 'package:uml_mobile_app/services/dialogue_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('real Spring: conversational CRUD and relations, removes only its own records', () async {
    final previous = HttpOverrides.current;
    HttpOverrides.global = null;
    SharedPreferences.setMockInitialValues({});
    final api = ApiService()..expectedContract = jsonDecode(await rootBundle.loadString('assets/mobile-contract.json'));
    await api.setBaseUrl(const String.fromEnvironment('SPRINT9_URL', defaultValue: 'http://127.0.0.1:8083/api'));
    final chat = DialogueService(api);
    dynamic clientId;
    dynamic orderId;
    try {
      final suffix = DateTime.now().microsecondsSinceEpoch;
      expect((await chat.send('crear Cliente')).text, contains('nombre'));
      expect((await chat.send('EnsayoSprint9')).text, contains('email'));
      final client = await chat.send('sprint9-$suffix@example.test');
      clientId = client.payload?['id'];
      expect(client.changed, isTrue, reason: client.text);
      final order = await chat.send('crear Pedido fecha=2026-09-21; total=125.50; estado=PENDIENTE; clienteId=$clientId');
      orderId = order.payload?['id'];
      expect(order.changed, isTrue, reason: order.text);
      final update = await chat.send('editar Pedido id $orderId estado=CONFIRMADO');
      expect(update.changed, isTrue, reason: update.text);
      expect((await chat.send('buscar Pedido id $orderId')).payload?['estado'], 'CONFIRMADO');
      expect((await chat.send('relaciones Cliente id $clientId pedidos')).text, contains('$orderId'));
      await chat.send('eliminar Cliente id $clientId');
      expect((await chat.send('cancelar')).changed, isFalse);
      await chat.send('eliminar Cliente id $clientId');
      final conflict = await chat.send('confirmar');
      expect(conflict.changed, isFalse);
      expect(conflict.text, contains('409'));
      await chat.send('eliminar Pedido id $orderId');
      expect((await chat.send('confirmar')).changed, isTrue);
      orderId = null;
      await chat.send('eliminar Cliente id $clientId');
      expect((await chat.send('confirmar')).changed, isTrue);
      clientId = null;
    } finally {
      try {
        if (orderId != null) await api.deleteRecord('/pedido', orderId);
        if (clientId != null) await api.deleteRecord('/cliente', clientId);
      } finally {
        HttpOverrides.global = previous;
      }
    }
  }, skip: !const bool.fromEnvironment('SPRINT9_LIVE'));
}
