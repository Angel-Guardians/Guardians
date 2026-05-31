import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/models.dart';
import '../services/api_client.dart';
import '../services/call_service.dart';
import '../state/app_state.dart';
import '../theme.dart';
import '../widgets/call_sheet.dart';
import '../widgets/common.dart';

/// A chat-style screen that sends a turn to Guardian and shows the spoken
/// reply, which specialist handled it, and any tools it used.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatMessage {
  _ChatMessage.user(this.text)
      : isUser = true,
        route = null,
        toolCalls = const [],
        callTarget = null;
  _ChatMessage.guardian(this.text, this.route, this.toolCalls)
      : isUser = false,
        callTarget = CallService.extractCallTarget(toolCalls);

  final String text;
  final bool isUser;
  final String? route;
  final List<ToolCall> toolCalls;

  /// A number Guardian asked us to call (from a call_* / alert_* tool), if any.
  final CallTarget? callTarget;
}

const _suggestions = [
  'How am I doing today?',
  'What medications do I take?',
  'I feel a bit lonely',
  'I have a headache',
];

const _routeMeta = {
  'safety': ('Safety', Icons.health_and_safety_rounded, AppTheme.danger),
  'reminder': ('Reminder', Icons.medication_rounded, AppTheme.warn),
  'health': ('Health', Icons.monitor_heart_rounded, AppTheme.seed),
  'behavior': ('Behavior', Icons.psychology_rounded, Color(0xFF8B5CF6)),
  'caregiver': ('Caregiver', Icons.family_restroom_rounded, AppTheme.good),
  'companion': ('Companion', Icons.favorite_rounded, Color(0xFFEC6A9C)),
};

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final List<_ChatMessage> _messages = [];
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send(AppState state, String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty || _sending) return;
    setState(() {
      _messages.add(_ChatMessage.user(trimmed));
      _sending = true;
      _controller.clear();
    });
    _scrollToBottom();
    try {
      final res = await state.api.turn(trimmed, state.activePatientId);
      final msg = _ChatMessage.guardian(res.reply, res.route, res.toolCalls);
      setState(() => _messages.add(msg));
      // Guardian asked us to call someone — offer to place it (and speak the
      // reply aloud) right away.
      if (msg.callTarget != null && mounted) {
        await showEmergencyCallSheet(
          context,
          number: msg.callTarget!.number,
          name: msg.callTarget!.name,
          message: res.reply,
          emergency: res.route == 'safety',
        );
      }
    } on ApiException catch (e) {
      setState(() {
        _messages.add(_ChatMessage.guardian(
            'Sorry, I couldn\'t reach Guardian (${e.status ?? 'error'}).',
            null,
            const []));
      });
    } catch (_) {
      setState(() {
        _messages.add(_ChatMessage.guardian(
            'Something went wrong. Please try again.', null, const []));
      });
    } finally {
      if (mounted) setState(() => _sending = false);
      _scrollToBottom();
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent,
            duration: const Duration(milliseconds: 280),
            curve: Curves.easeOut);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return Column(
      children: [
        Expanded(
          child: _messages.isEmpty
              ? _empty(context, state)
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  itemCount: _messages.length + (_sending ? 1 : 0),
                  itemBuilder: (ctx, i) {
                    if (i >= _messages.length) return const _TypingBubble();
                    return _Bubble(message: _messages[i]);
                  },
                ),
        ),
        _composer(context, state),
      ],
    );
  }

  Widget _empty(BuildContext context, AppState state) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 24),
        Center(
          child: Container(
            width: 76,
            height: 76,
            decoration: BoxDecoration(
              color: AppTheme.seed.withOpacity(0.12),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.shield_rounded,
                size: 38, color: AppTheme.seed),
          ),
        ),
        const SizedBox(height: 18),
        Text('Talk to Guardian',
            textAlign: TextAlign.center,
            style:
                theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        Text(
          'Ask about medications, how you\'re feeling, or just chat. Guardian '
          'routes each message to the right specialist.',
          textAlign: TextAlign.center,
          style: theme.textTheme.bodyMedium
              ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
        ),
        const SizedBox(height: 26),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final s in _suggestions)
              ActionChip(
                label: Text(s),
                onPressed: state.backendOnline ? () => _send(state, s) : null,
              ),
          ],
        ),
      ],
    );
  }

  Widget _composer(BuildContext context, AppState state) {
    final theme = Theme.of(context);
    return Container(
      padding: EdgeInsets.fromLTRB(
          12, 10, 12, 10 + MediaQuery.of(context).padding.bottom * 0),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
            top: BorderSide(color: theme.colorScheme.outlineVariant)),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              enabled: state.backendOnline && !_sending,
              decoration: InputDecoration(
                hintText: state.backendOnline
                    ? 'Type a message…'
                    : 'Backend offline',
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              ),
              onSubmitted: (v) => _send(state, v),
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            onPressed: state.backendOnline && !_sending
                ? () => _send(state, _controller.text)
                : null,
            style: FilledButton.styleFrom(
              minimumSize: const Size(52, 52),
              padding: EdgeInsets.zero,
              shape: const CircleBorder(),
            ),
            child: _sending
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.send_rounded),
          ),
        ],
      ),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});
  final _ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.isUser;
    final meta = _routeMeta[message.route];

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment:
            isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: [
          if (!isUser && meta != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 4, left: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(meta.$2, size: 14, color: meta.$3),
                  const SizedBox(width: 4),
                  Text('${meta.$1} specialist',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: meta.$3, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          Container(
            constraints: BoxConstraints(
                maxWidth: MediaQuery.of(context).size.width * 0.78),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: isUser
                  ? theme.colorScheme.primary
                  : theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
              borderRadius: BorderRadius.only(
                topLeft: const Radius.circular(18),
                topRight: const Radius.circular(18),
                bottomLeft: Radius.circular(isUser ? 18 : 4),
                bottomRight: Radius.circular(isUser ? 4 : 18),
              ),
            ),
            child: Text(
              message.text,
              style: TextStyle(
                color: isUser
                    ? theme.colorScheme.onPrimary
                    : theme.colorScheme.onSurface,
                fontSize: 15,
                height: 1.35,
              ),
            ),
          ),
          if (message.toolCalls.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 6, left: 4),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final t in message.toolCalls)
                    StatusPill(
                        label: _prettyTool(t.tool),
                        color: theme.colorScheme.onSurfaceVariant,
                        icon: Icons.build_rounded),
                ],
              ),
            ),
          if (message.callTarget != null)
            Padding(
              padding: const EdgeInsets.only(top: 8, left: 4),
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: meta?.$3 ?? AppTheme.danger,
                  minimumSize: const Size(0, 44),
                ),
                onPressed: () => showEmergencyCallSheet(
                  context,
                  number: message.callTarget!.number,
                  name: message.callTarget!.name,
                  message: message.text,
                  emergency: message.route == 'safety',
                ),
                icon: const Icon(Icons.call_rounded, size: 18),
                label: Text('Call ${message.callTarget!.name ?? message.callTarget!.number}'),
              ),
            ),
        ],
      ),
    );
  }

  String _prettyTool(String tool) =>
      tool.replaceAll('_', ' ').replaceAll('-', ' ');
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest.withOpacity(0.5),
          borderRadius: BorderRadius.circular(18),
        ),
        child: const SizedBox(
          width: 36,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _Dot(0),
              _Dot(1),
              _Dot(2),
            ],
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatefulWidget {
  const _Dot(this.index);
  final int index;
  @override
  State<_Dot> createState() => _DotState();
}

class _DotState extends State<_Dot> with SingleTickerProviderStateMixin {
  late final AnimationController _c =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 900))
        ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (ctx, _) {
        final t = (_c.value + widget.index * 0.2) % 1.0;
        final scale = 0.6 + 0.4 * (1 - (t - 0.5).abs() * 2).clamp(0.0, 1.0);
        return Transform.scale(
          scale: scale,
          child: Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        );
      },
    );
  }
}
