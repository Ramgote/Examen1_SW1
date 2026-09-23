# UML Mobile App (Flutter)

Sprint 9: CRUD por texto desde la conversación. Escribe `crear Cliente` y responde
las preguntas. Para cancelar usa `cancelar`; el borrado exige `confirmar`.
[Guía y pruebas del sprint 9](../docs/sprint-9.md).

Prototipo móvil de **UML Studio**. En sprint 8 se integra el contrato del Spring
generado; la generación Flutter completa y la voz local siguen pendientes.

En Ajustes usar `http://IP_DEL_PC:8083/api` y pulsar Comprobar conexión. La API
debe exponer `/api/_meta/contract` con la misma huella del descriptor empaquetado
`assets/mobile-contract.json` (Cliente–Pedido). Cambiar la URL no cambia de dominio.
La URL se recupera al iniciar. El build debug Android permite HTTP local.

[Preparación del nuevo Spring, pruebas y pendientes del sprint 8](../docs/sprint-8.md).

## Directorio de Ejecución

Todos los comandos deben ejecutarse dentro de este directorio:
```powershell
cd E:\Proyectos\Software1\Examen_1-SW1\mobile
```

## Comandos Rápidos

### 1. Ejecutar en el Teléfono Conectado
```powershell
flutter run
```

### 2. Generar Instalador APK
```powershell
flutter build apk --debug
```
*Archivo generado en:* `build/app/outputs/flutter-apk/app-debug.apk`

### 3. Instalar APK directamente por USB (ADB)
```powershell
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

### 4. Probar en Chrome
```powershell
flutter run -d chrome
```

Para ver la guía completa con solución de problemas y comandos de Hot Reload, consulta [`docs/guia-ejecucion-flutter.md`](../docs/guia-ejecucion-flutter.md).
