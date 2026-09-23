import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme/app_theme.dart';
import 'providers/chat_provider.dart';
import 'providers/entities_provider.dart';
import 'screens/main_screen.dart';
import 'services/api_service.dart';
import 'services/speech_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiService();
  await api.init();
  runApp(UmlMobileApp(apiService: api));
}

class UmlMobileApp extends StatelessWidget {
  final ApiService? apiService;
  final SpeechService? speechService;

  const UmlMobileApp({
    super.key,
    this.apiService,
    this.speechService,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveApi = apiService ?? ApiService();
    final effectiveSpeech = speechService ?? SpeechService();

    return MultiProvider(
      providers: [
        ChangeNotifierProvider<ApiService>.value(value: effectiveApi),
        Provider<SpeechService>.value(value: effectiveSpeech),
        ChangeNotifierProvider(create: (_) => EntitiesProvider(effectiveApi)),
        ChangeNotifierProxyProvider<EntitiesProvider, ChatProvider>(
          create: (ctx) => ChatProvider(
            effectiveSpeech,
            ctx.read<EntitiesProvider>(),
          ),
          update: (ctx, entitiesProvider, previous) =>
              previous ?? ChatProvider(effectiveSpeech, entitiesProvider),
        ),
      ],
      child: MaterialApp(
        title: 'UML Mobile Studio',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.lightTheme,
        home: const MainScreen(),
      ),
    );
  }
}
