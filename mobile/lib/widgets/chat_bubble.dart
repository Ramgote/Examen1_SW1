import 'package:flutter/material.dart';
import '../core/theme/app_theme.dart';
import '../models/chat_message.dart';

class ChatBubble extends StatelessWidget {
  final ChatMessage message;

  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final isError = message.type == MessageType.error;
    final isCrud = message.type == MessageType.crudResult;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: isUser
              ? AppTheme.primaryBlue
              : isError
                  ? const Color(0xFFFEE2E2)
                  : Colors.white,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(16),
            topRight: const Radius.circular(16),
            bottomLeft: Radius.circular(isUser ? 16 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 16),
          ),
          border: isUser ? null : Border.all(color: isError ? AppTheme.accentRed : AppTheme.cardBorder),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              message.text,
              style: TextStyle(
                color: isUser
                    ? Colors.white
                    : isError
                        ? AppTheme.accentRed
                        : AppTheme.primaryDark,
                fontSize: 14,
                fontWeight: isUser ? FontWeight.w500 : FontWeight.w400,
              ),
            ),
            if (isCrud && message.actionPayload != null) ...[
              const SizedBox(height: 8),
              _buildPayloadView(message.actionPayload!),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildPayloadView(Map<String, dynamic> payload) {
    if (payload.containsKey('records') && payload['records'] is List) {
      final list = payload['records'] as List;
      return Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: const Color(0xFFF1F5F9),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: list.map((rec) {
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Text(
                '• $rec',
                style: const TextStyle(fontSize: 12, color: AppTheme.primaryDark),
              ),
            );
          }).toList(),
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFFDCFCE7),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        'Datos: $payload',
        style: const TextStyle(fontSize: 12, color: Color(0xFF166534)),
      ),
    );
  }
}
