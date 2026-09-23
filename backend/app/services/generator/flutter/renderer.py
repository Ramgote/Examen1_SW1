"""Generate an Android Flutter project without requiring Flutter on the server."""
from pathlib import Path
import hashlib
import json
import re
from app.services.generator.ast_transformer import GenerationError

BASE = Path(__file__).parent


def render(contract, project_id='example'):
    if not contract['entities']:
        raise GenerationError(['Flutter requiere al menos una entidad concreta con CRUD.'])
    manifest = json.loads((BASE / 'template-manifest.json').read_text(encoding='utf-8'))
    files = {}
    for path, digest in manifest.items():
        raw = (BASE / 'template' / path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != digest:
            raise RuntimeError('Flutter template checksum mismatch: ' + path)
        files[path] = raw
    identity = hashlib.sha256(str(project_id).encode()).hexdigest()[:16]
    path = 'android/app/build.gradle.kts'
    files[path] = files[path].decode().replace('applicationId = "com.umlstudio.mobile.uml_mobile_app"',
                                               f'applicationId = "com.uml.generated.p{identity}"')
    files['assets/mobile-contract.json'] = json.dumps(contract, ensure_ascii=False, indent=2)
    path = 'lib/core/constants/app_constants.dart'
    files[path] = re.sub(r"static const String defaultBackendUrl = '[^']*';",
        "static const String defaultBackendUrl = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8080/api');",
        files[path].decode())
    path = 'lib/screens/settings_screen.dart'
    files[path] = files[path].decode().replace('192.168.1.51:8083', 'IP_DEL_PC:8080')
    files['.gitignore'] = '.dart_tool/\nbuild/\nandroid/local.properties\nandroid/.gradle/\n.env\n'
    files['lib/generated/domain.dart'] = domain_source(contract)
    files['test/generated_contract_test.dart'] = """import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('bundled contract has entities and singular API routes', () async {
    final c = jsonDecode(await rootBundle.loadString('assets/mobile-contract.json'));
    expect(c['format_version'], 1);
    expect(c['entities'], isNotEmpty);
    for (final e in c['entities']) {
      expect(e['endpoint'], '/${e['name'].toString().toLowerCase()}');
      expect(e['request_fields'], contains('entityVersion'));
    }
  });
}
"""
    files['README.md'] = f"""# Flutter generado — Android

Contrato: `{contract['fingerprint']}`. Mismo contrato que `../backend`.
Proyecto Flutter completo para Android, interfaz y CRUD conversacional por texto.
Voz local pendiente del sprint 11; no se certifica STT sin nube.

Requisitos: Flutter 3.41.7 / Dart 3.11.5 o versión compatible, Android SDK y JDK.
Se incluye pubspec.lock. Desde esta carpeta:

```powershell
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
flutter run --dart-define=API_BASE_URL=http://IP_DEL_PC:8080/api
```

El emulador Android usa 10.0.2.2:8080 por defecto. En teléfono físico configura la
IP LAN en Ajustes. Un ajuste guardado tiene prioridad sobre dart-define.
El build debug permite HTTP local; release requiere HTTPS y firma propia.
El backend debe publicar su puerto y el firewall permitir la red privada.
La app verifica `/api/_meta/contract` antes de operar. Si cambias el modelo,
regenera ambos proyectos; no modifica automáticamente una app instalada.

Escribe `ayuda`, `crear NOMBRE_ENTIDAD`, `listar NOMBRE_ENTIDAD`,
`editar NOMBRE_ENTIDAD id ID` o `eliminar NOMBRE_ENTIDAD id ID`.
Responde campos obligatorios; confirma o cancela el borrado.
Modelos de respuesta y servicios por entidad: `lib/generated/domain.dart`.
La conversación utiliza el cliente genérico guiado por el mismo descriptor.
No contiene credenciales PostgreSQL ni datos de la plataforma.
"""
    return files


def domain_source(contract):
    lines = ["import '../services/api_service.dart';", '']
    for e in contract['entities']:
        name = 'Generated' + e['name']
        lines += [f'class {name}Record {{', '  final Map<String, dynamic> data;',
                  f'  {name}Record(Map<String, dynamic> json) : data = Map.unmodifiable(json);',
                  '  Map<String, dynamic> toJson() => Map.of(data);']
        for a in e['attributes']:
            dart_type = {'Integer': 'int', 'Long': 'int', 'Double': 'num', 'Float': 'num',
                         'BigDecimal': 'num', 'Boolean': 'bool'}.get(a['type'], 'String')
            lines.append(f"  {dart_type}? get value{a['name'][0].upper() + a['name'][1:]} => data['{a['name']}'] as {dart_type}?;")
        for r in e['relationships']:
            dtype = 'String' if r['type'] == 'String' else 'int'
            getter = 'relation' + r['name'][0].upper() + r['name'][1:]
            value = f"(data['{r['field']}'] as List?)?.cast<{dtype}>()" if r['many'] else f"data['{r['field']}'] as {dtype}?"
            lines.append(f"  {'List<' + dtype + '>' if r['many'] else dtype}? get {getter} => {value};")
        lines += ['  int? get entityVersion => data[\'entityVersion\'] as int?;', '}',
                  f'class {name}Service {{', '  final ApiService api;', f'  {name}Service(this.api);',
                  f"  static const endpoint = '{e['endpoint']}';",
                  f'  Future<List<{name}Record>> list({{int page = 0}}) async {{',
                  '    await api.checkContract();',
                  f'    return (await api.listRecords(endpoint, page: page)).map({name}Record.new).toList();', '  }',
                  f'  Future<{name}Record> get(Object id) async {{ await api.checkContract(); return {name}Record(await api.getRecord(endpoint, id)); }}',
                  f'  Future<{name}Record> create(Map<String, dynamic> fields) async {{ await api.checkContract(); return {name}Record(await api.createRecord(endpoint, fields)); }}',
                  f'  Future<{name}Record> update(Object id, Map<String, dynamic> fields) async {{ await api.checkContract(); return {name}Record(await api.updateRecord(endpoint, id, fields)); }}',
                  '  Future<bool> delete(Object id) async { await api.checkContract(); return api.deleteRecord(endpoint, id); }', '}', '']
    return '\n'.join(lines)
