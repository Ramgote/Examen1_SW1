enum MessageSender { user, assistant, system }

enum MessageType { text, crudAction, crudResult, error }

class ChatMessage {
  final String id;
  final String text;
  final MessageSender sender;
  final MessageType type;
  final DateTime timestamp;
  final Map<String, dynamic>? actionPayload;

  ChatMessage({
    required this.id,
    required this.text,
    required this.sender,
    this.type = MessageType.text,
    DateTime? timestamp,
    this.actionPayload,
  }) : timestamp = timestamp ?? DateTime.now();

  bool get isUser => sender == MessageSender.user;
}
