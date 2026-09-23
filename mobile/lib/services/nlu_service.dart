import '../core/constants/app_constants.dart';
import '../models/entity_schema.dart';

class IntentResult {
  final String action; // CREATE, READ, UPDATE, DELETE, LIST, HELP
  final String? entityName;
  final dynamic recordId;
  final Map<String, dynamic> data;
  final String summary;

  IntentResult({
    required this.action,
    this.entityName,
    this.recordId,
    this.data = const {},
    required this.summary,
  });
}

class NluService {
  /// Interprets natural language command against known schemas
  static IntentResult parse(String input, List<EntitySchema> availableSchemas) {
    final clean = input.trim().toLowerCase();
    
    if (clean.contains('ayuda') || clean.contains('que puedes hacer') || clean.contains('comandos')) {
      return IntentResult(
        action: AppConstants.actionHelp,
        summary: 'Comandos disponibles: crear [entidad], listar [entidades], buscar [entidad] [id], eliminar [entidad] [id].',
      );
    }

    // Match entity from schemas
    EntitySchema? matchedSchema;
    for (final schema in availableSchemas) {
      final sName = schema.name.toLowerCase();
      final tName = schema.tableName.toLowerCase();
      if (clean.contains(sName) || clean.contains(tName) || clean.contains('${sName}s') || clean.contains('${tName}s')) {
        matchedSchema = schema;
        break;
      }
    }

    // LIST / VER TODOS
    if (clean.startsWith('listar') || clean.startsWith('ver') || clean.startsWith('mostrar') || clean.contains('todos')) {
      return IntentResult(
        action: AppConstants.actionList,
        entityName: matchedSchema?.name ?? 'Registro',
        summary: 'Listar registros de ${matchedSchema?.name ?? "entidad"}',
      );
    }

    // DELETE / ELIMINAR
    if (clean.startsWith('eliminar') || clean.startsWith('borrar') || clean.startsWith('quitar')) {
      final idMatch = RegExp(r'\b(?:id|codigo|número)?\s*(\d+)\b').firstMatch(clean);
      final id = idMatch != null ? int.tryParse(idMatch.group(1)!) : null;
      return IntentResult(
        action: AppConstants.actionDelete,
        entityName: matchedSchema?.name ?? 'Registro',
        recordId: id,
        summary: 'Eliminar ${matchedSchema?.name ?? "registro"} con ID $id',
      );
    }

    // READ / BUSCAR
    if (clean.startsWith('buscar') || clean.startsWith('consultar') || clean.startsWith('obtener')) {
      final idMatch = RegExp(r'\b(?:id|codigo|número)?\s*(\d+)\b').firstMatch(clean);
      final id = idMatch != null ? int.tryParse(idMatch.group(1)!) : null;
      return IntentResult(
        action: AppConstants.actionRead,
        entityName: matchedSchema?.name ?? 'Registro',
        recordId: id,
        summary: 'Buscar ${matchedSchema?.name ?? "registro"} con ID $id',
      );
    }

    // CREATE / CREAR / REGISTRAR
    if (clean.startsWith('crear') || clean.startsWith('nuevo') || clean.startsWith('nueva') || clean.startsWith('registrar') || clean.startsWith('agregar')) {
      final extractedData = <String, dynamic>{};
      if (matchedSchema != null) {
        for (final attr in matchedSchema.attributes) {
          if (attr.isPk) continue;
          final pattern = RegExp('${attr.name.toLowerCase()}\\s*[:=]?\\s*([^,]+)', caseSensitive: false);
          final match = pattern.firstMatch(input);
          if (match != null) {
            final valStr = match.group(1)!.trim();
            if (attr.type.toLowerCase().contains('int') || attr.type.toLowerCase().contains('long')) {
              extractedData[attr.name] = int.tryParse(valStr) ?? valStr;
            } else if (attr.type.toLowerCase().contains('double') || attr.type.toLowerCase().contains('float') || attr.type.toLowerCase().contains('decimal')) {
              extractedData[attr.name] = double.tryParse(valStr) ?? valStr;
            } else if (attr.type.toLowerCase().contains('bool')) {
              extractedData[attr.name] = valStr.toLowerCase() == 'true' || valStr.toLowerCase() == 'si' || valStr.toLowerCase() == 'sí';
            } else {
              extractedData[attr.name] = valStr;
            }
          }
        }
      }

      return IntentResult(
        action: AppConstants.actionCreate,
        entityName: matchedSchema?.name ?? 'Registro',
        data: extractedData,
        summary: 'Crear nuevo ${matchedSchema?.name ?? "registro"} con datos: $extractedData',
      );
    }

    // Default Fallback
    return IntentResult(
      action: AppConstants.actionHelp,
      entityName: matchedSchema?.name,
      summary: 'No entendí el comando. Prueba: "listar clientes", "crear cliente nombre Carlos" o "eliminar pedido id 1".',
    );
  }
}
