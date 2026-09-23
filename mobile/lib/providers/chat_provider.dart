import 'package:flutter/material.dart';
import '../models/chat_message.dart';
import '../services/dialogue_service.dart';
import '../services/speech_service.dart';
import 'entities_provider.dart';

class ChatProvider extends ChangeNotifier {
  final SpeechService _speechService;
  final EntitiesProvider _entitiesProvider;
  final DialogueService _dialogue;
  final List<ChatMessage> _messages = [];
  bool _isProcessing = false;
  String _currentSpeechText = '';
  int _sequence = 0;
  bool _disposed = false;

  ChatProvider(this._speechService, this._entitiesProvider)
      : _dialogue = DialogueService(_entitiesProvider.api) {
    _add(DialogueService.help, MessageSender.assistant);
  }

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isProcessing => _isProcessing;
  bool get isListening => _speechService.isListening;
  bool get isSpeaking => _speechService.isSpeaking;
  bool get ttsEnabled => _speechService.ttsEnabled;
  String get currentSpeechText => _currentSpeechText;

  void toggleTts() {
    _speechService.ttsEnabled = !_speechService.ttsEnabled;
    if (!_speechService.ttsEnabled && _speechService.isSpeaking) {
      _speechService.stopSpeaking();
    }
    notifyListeners();
  }

  void _add(String text, MessageSender sender, {Map<String, dynamic>? payload}) {
    _messages.add(ChatMessage(
      id: 'msg_${_sequence++}',
      text: text,
      sender: sender,
      type: payload == null ? MessageType.text : MessageType.crudResult,
      actionPayload: payload,
    ));
  }

  Future<void> sendUserMessage(String text, {bool fromVoice = false}) async {
    if (_isProcessing || text.trim().isEmpty || _disposed) return;
    _isProcessing = true;
    _add(text.trim(), MessageSender.user);
    notifyListeners();

    try {
      final reply = await _dialogue.send(text);
      if (_disposed) return;
      _add(reply.text, MessageSender.assistant, payload: reply.payload);

      // Si la petición vino por voz o TTS está activo, responder por voz local
      if (fromVoice || _speechService.ttsEnabled) {
        await _speechService.speak(reply.text);
      }

      if (reply.changed) {
        await _entitiesProvider.fetchAllRecords();
        if (_entitiesProvider.error != null) {
          final errText = 'La escritura fue confirmada, pero no se pudo actualizar el listado: ${_entitiesProvider.error}';
          _add(errText, MessageSender.assistant);
          if (fromVoice || _speechService.ttsEnabled) {
            await _speechService.speak(errText);
          }
        }
      }
    } finally {
      _isProcessing = false;
      if (!_disposed) notifyListeners();
    }
  }

  Future<void> toggleVoiceRecording() async {
    if (_isProcessing || _disposed) return;

    if (_speechService.isListening) {
      await _speechService.stopListening();
      if (_currentSpeechText.trim().isNotEmpty) {
        final textToSend = _currentSpeechText;
        _currentSpeechText = '';
        notifyListeners();
        await sendUserMessage(textToSend, fromVoice: true);
      } else {
        notifyListeners();
      }
    } else {
      if (_speechService.isSpeaking) {
        await _speechService.stopSpeaking();
      }
      _currentSpeechText = '';
      notifyListeners();

      await _speechService.startListening(
        onResult: (text) {
          _currentSpeechText = text;
          notifyListeners();
        },
        onDone: () async {
          if (_currentSpeechText.trim().isNotEmpty) {
            final textToSend = _currentSpeechText;
            _currentSpeechText = '';
            notifyListeners();
            await sendUserMessage(textToSend, fromVoice: true);
          } else {
            notifyListeners();
          }
        },
      );

      if (!_speechService.isAvailable && _speechService.lastError.isNotEmpty) {
        _add('Reconocimiento de voz no disponible o permiso denegado: ${_speechService.lastError}', MessageSender.assistant);
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _speechService.stopListening();
    _speechService.stopSpeaking();
    super.dispose();
  }
}
