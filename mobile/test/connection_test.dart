import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uml_mobile_app/services/api_service.dart';
import 'package:uml_mobile_app/providers/entities_provider.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUp(() => SharedPreferences.setMockInitialValues({}));

  test('restores saved URL and rejects invalid URL', () async {
    final api = ApiService();
    await api.init();
    await api.setBaseUrl('http://localhost:8082/api/');
    final restarted = ApiService();
    await restarted.init();
    expect(restarted.baseUrl, 'http://localhost:8082/api');
    await expectLater(api.setBaseUrl('http://localhost:8082/api/v1'), throwsFormatException);
  });

  for (final scenario in ['empty', 'mismatch', 'http404', 'offline']) {
    test('connection $scenario distinguishes failure from empty collection', () async {
      final raw = await rootBundle.loadString('assets/mobile-contract.json');
      final contract = jsonDecode(raw) as Map<String, dynamic>;
      final paths = <String>[];
      final api = ApiService(client: MockClient((request) async {
        paths.add(request.url.path);
        if (scenario == 'offline') throw http.ClientException('sin red');
        if (request.url.path.endsWith('/_meta/contract')) {
          return http.Response(jsonEncode({...contract, if (scenario == 'mismatch') 'fingerprint': 'other'}), 200);
        }
        return http.Response('[]', scenario == 'http404' ? 404 : 200);
      }));
      await api.init();
      final provider = EntitiesProvider(api);
      await provider.fetchAllRecords();
      expect(provider.isConnected, scenario == 'empty');
      if (scenario == 'empty') {
        expect(provider.error, isNull);
        expect(paths, containsAll(['/api/cliente', '/api/pedido']));
        expect(provider.recordsByEntity['Pedido'], isEmpty);
        await api.setBaseUrl('http://otro:8082/api');
        expect(provider.isConnected, isFalse);
        expect(provider.recordsByEntity, isEmpty);
      } else {
        expect(provider.error, isNotNull);
        expect(provider.recordsByEntity, isEmpty);
        if (scenario == 'mismatch') expect(paths.length, 1);
      }
      provider.dispose();
    });
  }
}
