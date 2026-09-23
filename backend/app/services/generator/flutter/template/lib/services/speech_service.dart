import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

class SpeechService {
  stt.SpeechToText? _speechInstance;
  FlutterTts? _ttsInstance;

  stt.SpeechToText get _speech => _speechInstance ??= stt.SpeechToText();
  FlutterTts get _tts => _ttsInstance ??= FlutterTts();

  bool _isAvailable = false;
  bool _isListening = false;
  bool _isSpeaking = false;
  bool _hasPermission = false;
  String _lastError = '';
  bool ttsEnabled = true;

  SpeechService({stt.SpeechToText? speech, FlutterTts? tts})
      : _speechInstance = speech,
        _ttsInstance = tts;

  bool get isAvailable => _isAvailable;
  bool get isListening => _isListening;
  bool get isSpeaking => _isSpeaking;
  bool get hasPermission => _hasPermission;
  String get lastError => _lastError;

  Future<bool> init() async {
    if (_isAvailable) return true;
    try {
      _isAvailable = await _speech.initialize(
        onError: (val) {
          _lastError = val.errorMsg;
          _isListening = false;
          debugPrint('SpeechService error: ${val.errorMsg} (permanent: ${val.permanent})');
        },
        onStatus: (val) {
          if (val == 'done' || val == 'notListening') {
            _isListening = false;
          }
          debugPrint('SpeechService status: $val');
        },
        debugLogging: false,
      );
      _hasPermission = await _speech.hasPermission;

      // Configurar TTS local
      await _tts.setLanguage('es-ES');
      await _tts.setSpeechRate(0.9);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);

      _tts.setStartHandler(() => _isSpeaking = true);
      _tts.setCompletionHandler(() => _isSpeaking = false);
      _tts.setCancelHandler(() => _isSpeaking = false);
      _tts.setErrorHandler((_) => _isSpeaking = false);

      return _isAvailable;
    } catch (e) {
      _lastError = e.toString();
      _isAvailable = false;
      _hasPermission = false;
      debugPrint('Error al inicializar SpeechService: $e');
      return false;
    }
  }

  Future<void> startListening({
    required Function(String text) onResult,
    required VoidCallback onDone,
  }) async {
    if (_isSpeaking) {
      await stopSpeaking();
    }

    if (!_isAvailable) {
      final ok = await init();
      if (!ok) {
        onDone();
        return;
      }
    }

    _lastError = '';
    _isListening = true;

    try {
      await _speech.listen(
        listenOptions: stt.SpeechListenOptions(
          listenMode: stt.ListenMode.confirmation,
          cancelOnError: true,
          partialResults: true,
          localeId: 'es_ES',
        ),
        onResult: (result) {
          onResult(result.recognizedWords);
          if (result.finalResult) {
            _isListening = false;
            onDone();
          }
        },
      );
    } catch (e) {
      _lastError = e.toString();
      _isListening = false;
      onDone();
    }
  }

  Future<void> stopListening() async {
    if (_isListening) {
      try {
        await _speech.stop();
      } catch (_) {}
      _isListening = false;
    }
  }

  Future<void> cancelListening() async {
    if (_isListening) {
      try {
        await _speech.cancel();
      } catch (_) {}
      _isListening = false;
    }
  }

  Future<void> speak(String text) async {
    if (!ttsEnabled || text.trim().isEmpty) return;
    try {
      if (_isListening) {
        await cancelListening();
      }
      _isSpeaking = true;
      final cleanText = text
          .replaceAll(RegExp(r'[{}[\]"]'), '')
          .replaceAll(RegExp(r'\s+'), ' ')
          .trim();
      if (cleanText.isNotEmpty) {
        await _tts.speak(cleanText);
      }
    } catch (e) {
      debugPrint('Error en TTS: $e');
      _isSpeaking = false;
    }
  }

  Future<void> stopSpeaking() async {
    if (_isSpeaking) {
      try {
        await _tts.stop();
      } catch (_) {}
      _isSpeaking = false;
    }
  }
}
