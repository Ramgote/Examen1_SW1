class EntityAttribute {
  final String name;
  final String type;
  final bool isPk;
  final bool isNullable;

  EntityAttribute({
    required this.name,
    required this.type,
    this.isPk = false,
    this.isNullable = true,
  });

  factory EntityAttribute.fromJson(Map<String, dynamic> json) {
    return EntityAttribute(
      name: json['name'] ?? '',
      type: json['type'] ?? 'String',
      isPk: json['is_pk'] ?? false,
      isNullable: json['is_nullable'] ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
    'name': name,
    'type': type,
    'is_pk': isPk,
    'is_nullable': isNullable,
  };
}

class EntitySchema {
  final String name;
  final String tableName;
  final String endpoint;
  final List<EntityAttribute> attributes;
  final List<Map<String, dynamic>> relationships;
  final Map<String, dynamic> primaryKey;
  final List<String> requestFields;

  EntitySchema({
    required this.name,
    required this.tableName,
    required this.endpoint,
    required this.attributes,
    this.relationships = const [],
    this.primaryKey = const {},
    this.requestFields = const [],
  });

  factory EntitySchema.fromJson(Map<String, dynamic> json) {
    return EntitySchema(
      name: json['name'] ?? '',
      tableName: json['tableName'] ?? json['name']?.toString().toLowerCase() ?? '',
      endpoint: json['endpoint'] as String,
      attributes: (json['attributes'] as List<dynamic>? ?? [])
          .map((a) => EntityAttribute.fromJson(a as Map<String, dynamic>))
          .toList(),
      relationships: (json['relationships'] as List? ?? []).map((r) => Map<String, dynamic>.from(r)).toList(),
      primaryKey: Map<String, dynamic>.from(json['primary_key'] ?? {}),
      requestFields: List<String>.from(json['request_fields'] ?? []),
    );
  }
}
