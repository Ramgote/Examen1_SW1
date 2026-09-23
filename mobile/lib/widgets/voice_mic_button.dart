import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';

class VoiceMicButton extends StatelessWidget {
  final bool isListening;
  final VoidCallback onPressed;

  const VoiceMicButton({
    super.key,
    required this.isListening,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onPressed,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: isListening ? 56 : 48,
        height: isListening ? 56 : 48,
        decoration: BoxDecoration(
          color: isListening ? AppTheme.accentRed : AppTheme.primaryBlue,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: (isListening ? AppTheme.accentRed : AppTheme.primaryBlue).withValues(alpha: 0.4),
              blurRadius: isListening ? 16 : 8,
              spreadRadius: isListening ? 4 : 1,
            ),
          ],
        ),
        child: Icon(
          isListening ? Icons.mic : Icons.mic_none,
          color: Colors.white,
          size: isListening ? 28 : 24,
        ),
      ),
    );
  }
}
