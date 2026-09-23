import 'package:flutter_test/flutter_test.dart';
import 'package:uml_mobile_app/models/chat_message.dart';
import 'package:uml_mobile_app/providers/chat_provider.dart';
import 'package:uml_mobile_app/providers/entities_provider.dart';
import 'package:uml_mobile_app/services/api_service.dart';
import 'package:uml_mobile_app/services/speech_service.dart';

class MockSpeechService extends SpeechService {
  bool initResult = true;
  bool listenTriggered = false;
  String spokenText = '';
  int speakCount = 0;
  int stopSpeakCount = 0;

  @override
  bool get isAvailable => initResult;

  @override
  Future<bool> init() async => initResult;

  @override
  Future<void> startListening({
    required Function(String text) onResult,
    required void Function() onDone,
  }) async {
    listenTriggered = true;
  }

  @override
  Future<void> stopListening() async {
    listenTriggered = false;
  }

  @override
  Future<void> cancelListening() async {
    listenTriggered = false;
  }

  @override
  Future<void> speak(String text) async {
    spokenText = text;
    speakCount++;
  }

  @override
  Future<void> stopSpeaking() async {
    stopSpeakCount++;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('SpeechService configuration and TTS toggle', () {
    final speech = SpeechService();
    expect(speech.ttsEnabled, isTrue);
    speech.ttsEnabled = false;
    expect(speech.ttsEnabled, isFalse);
    expect(speech.isListening, isFalse);
    expect(speech.isSpeaking, isFalse);
  });

  test('ChatProvider triggers speak on user command and handles voice response', () async {
    final mockSpeech = MockSpeechService();
    final client = ApiService();
    final entities = EntitiesProvider(client);
    final chat = ChatProvider(mockSpeech, entities);

    expect(chat.messages.first.sender, MessageSender.assistant);
    expect(chat.ttsEnabled, isTrue);

    // Enviar mensaje simulado
    await chat.sendUserMessage('ayuda', fromVoice: true);

    expect(chat.messages.length, greaterThanOrEqualTo(2));
    expect(chat.messages.any((m) => m.text == 'ayuda' && m.sender == MessageSender.user), isTrue);
    expect(mockSpeech.speakCount, greaterThanOrEqualTo(1));
    expect(mockSpeech.spokenText, contains('crear Cliente'));
  });

  test('ChatProvider toggleTts disables voice synthesis', () async {
    final mockSpeech = MockSpeechService();
    final client = ApiService();
    final entities = EntitiesProvider(client);
    final chat = ChatProvider(mockSpeech, entities);

    chat.toggleTts();
    expect(chat.ttsEnabled, isFalse);
    expect(mockSpeech.ttsEnabled, isFalse);

    await chat.sendUserMessage('ayuda', fromVoice: false);
    expect(mockSpeech.speakCount, 0);
  });

  test('Voice recording toggles and cancels on dispose', () async {
    final mockSpeech = MockSpeechService();
    final client = ApiService();
    final entities = EntitiesProvider(client);
    final chat = ChatProvider(mockSpeech, entities);

    await chat.toggleVoiceRecording();
    expect(mockSpeech.listenTriggered, isTrue);

    chat.dispose();
    expect(mockSpeech.listenTriggered, isFalse);
  });
}
