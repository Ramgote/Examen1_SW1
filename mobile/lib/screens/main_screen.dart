import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../providers/entities_provider.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/voice_mic_button.dart';
import 'settings_screen.dart';

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});
  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  final _text = TextEditingController();
  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  void _send(ChatProvider chat) {
    if (chat.isProcessing || _text.text.trim().isEmpty) return;
    final input = _text.text;
    _text.clear();
    chat.sendUserMessage(input);
  }

  @override
  Widget build(BuildContext context) {
    final entities = context.watch<EntitiesProvider>();
    final chat = context.watch<ChatProvider>();
    final busy = chat.isProcessing || entities.isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Asistente UML'),
        actions: [
          IconButton(
            tooltip: chat.ttsEnabled ? 'Respuesta por voz activa' : 'Respuesta por voz silenciada',
            icon: Icon(chat.ttsEnabled ? Icons.volume_up_rounded : Icons.volume_off_rounded),
            onPressed: () => chat.toggleTts(),
          ),
          IconButton(
            tooltip: 'Comprobar conexión',
            icon: const Icon(Icons.refresh),
            onPressed: busy ? null : () => entities.fetchAllRecords(),
          ),
          IconButton(
            tooltip: 'Ajustes del servidor',
            icon: const Icon(Icons.settings),
            onPressed: busy
                ? null
                : () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  entities.isConnected ? 'Conectado' : 'Pulsa actualizar para comprobar la conexión',
                  style: TextStyle(color: entities.isConnected ? Colors.green : Colors.orange, fontWeight: FontWeight.w600),
                ),
              ),
            ),
            if (entities.error != null)
              Padding(
                padding: const EdgeInsets.all(8),
                child: Text(entities.error!, style: const TextStyle(color: Colors.red)),
              ),
            if (entities.schemas.isNotEmpty)
              ExpansionTile(
                title: const Text('Entidades y campos de referencia'),
                children: [
                  ConstrainedBox(
                    constraints: const BoxConstraints(maxHeight: 150),
                    child: ListView(
                      shrinkWrap: true,
                      children: entities.schemas
                          .map((s) => ListTile(
                                dense: true,
                                title: Text(s.name, style: const TextStyle(fontWeight: FontWeight.bold)),
                                subtitle: Text(s.requestFields.where((f) => f != 'entityVersion').join(', ')),
                              ))
                          .toList(),
                    ),
                  ),
                ],
              ),
            Expanded(
              child: ListView.builder(
                reverse: true,
                padding: const EdgeInsets.symmetric(vertical: 8),
                itemCount: chat.messages.length,
                itemBuilder: (_, index) => ChatBubble(message: chat.messages[chat.messages.length - 1 - index]),
              ),
            ),
            if (busy) const LinearProgressIndicator(),
            if (chat.isListening || chat.currentSpeechText.isNotEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: const Color(0xFFFEF2F2),
                child: Row(
                  children: [
                    const Icon(Icons.graphic_eq, color: Colors.red, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        chat.currentSpeechText.isEmpty ? 'Escuchando tu voz...' : chat.currentSpeechText,
                        style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w500, fontSize: 13),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _text,
                      enabled: !busy,
                      decoration: const InputDecoration(
                        hintText: 'Escribe o dicta una orden o respuesta',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(chat),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IgnorePointer(
                    ignoring: busy,
                    child: VoiceMicButton(
                      isListening: chat.isListening,
                      onPressed: () => chat.toggleVoiceRecording(),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Enviar',
                    icon: const Icon(Icons.send),
                    onPressed: busy ? null : () => _send(chat),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
