import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/theme/app_theme.dart';
import '../models/entity_schema.dart';
import '../providers/entities_provider.dart';

class EntitiesCatalogScreen extends StatefulWidget {
  const EntitiesCatalogScreen({super.key});

  @override
  State<EntitiesCatalogScreen> createState() => _EntitiesCatalogScreenState();
}

class _EntitiesCatalogScreenState extends State<EntitiesCatalogScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<EntitiesProvider>().fetchAllRecords();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<EntitiesProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Catálogo de Entidades UML'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => provider.fetchAllRecords(),
          ),
        ],
      ),
      body: provider.isLoading
          ? const Center(child: CircularProgressIndicator())
          : provider.schemas.isEmpty
              ? const Center(child: Text('No hay entidades configuradas.'))
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: provider.schemas.length,
                  itemBuilder: (context, index) {
                    final schema = provider.schemas[index];
                    final records = provider.recordsByEntity[schema.name] ?? [];
                    return _buildEntityCard(schema, records);
                  },
                ),
    );
  }

  Widget _buildEntityCard(EntitySchema schema, List<Map<String, dynamic>> records) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: ExpansionTile(
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.dataset_outlined, color: AppTheme.primaryBlue, size: 20),
        ),
        title: Text(
          schema.name,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: AppTheme.primaryDark),
        ),
        subtitle: Text(
          'Endpoint: ${schema.endpoint} • ${records.length} registro(s)',
          style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
        ),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Atributos del Esquema:',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.primaryDark),
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: schema.attributes.map((attr) {
                    return Chip(
                      label: Text('${attr.name} (${attr.type})', style: const TextStyle(fontSize: 11)),
                      backgroundColor: attr.isPk ? const Color(0xFFFEF3C7) : const Color(0xFFF1F5F9),
                      side: BorderSide(color: attr.isPk ? AppTheme.accentAmber : AppTheme.cardBorder),
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                const Text(
                  'Registros actuales:',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.primaryDark),
                ),
                const SizedBox(height: 6),
                if (records.isEmpty)
                  const Text('No hay datos guardados aún en Spring Boot.', style: TextStyle(fontSize: 12, color: Color(0xFF94A3B8)))
                else
                  ...records.map((r) => Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF8FAFC),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: AppTheme.cardBorder),
                    ),
                    child: Text('$r', style: const TextStyle(fontSize: 12, fontFamily: 'monospace')),
                  )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
