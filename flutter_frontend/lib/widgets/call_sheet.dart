import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/call_service.dart';
import '../state/app_state.dart';
import '../theme.dart';

/// Show a confirmation sheet to place an emergency call to [number] and speak
/// [message] aloud. Returns the outcome (or null if dismissed).
Future<CallOutcome?> showEmergencyCallSheet(
  BuildContext context, {
  required String number,
  String? name,
  required String message,
  String? audioUrl,
  bool emergency = false,
}) {
  return showModalBottomSheet<CallOutcome>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => _CallSheet(
      number: number,
      name: name,
      message: message,
      audioUrl: audioUrl,
      emergency: emergency,
    ),
  );
}

class _CallSheet extends StatefulWidget {
  const _CallSheet({
    required this.number,
    required this.name,
    required this.message,
    required this.audioUrl,
    required this.emergency,
  });

  final String number;
  final String? name;
  final String message;
  final String? audioUrl;
  final bool emergency;

  @override
  State<_CallSheet> createState() => _CallSheetState();
}

class _CallSheetState extends State<_CallSheet> {
  TelephonyStatus? _status;
  bool _calling = false;
  CallOutcome? _outcome;

  CallService get _svc => context.read<AppState>().callService;

  @override
  void initState() {
    super.initState();
    _probe();
  }

  Future<void> _probe() async {
    final s = await _svc.status();
    if (mounted) setState(() => _status = s);
  }

  Future<void> _call() async {
    setState(() => _calling = true);
    final outcome = await _svc.callWithVoice(
      number: widget.number,
      message: widget.message,
      audioUrl: widget.audioUrl,
    );
    if (!mounted) return;
    setState(() {
      _calling = false;
      _outcome = outcome;
    });
    if (outcome.placed) {
      await Future.delayed(const Duration(milliseconds: 600));
      if (mounted) Navigator.of(context).maybePop(outcome);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accent = widget.emergency ? AppTheme.danger : AppTheme.seed;
    final status = _status;

    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        4,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.13),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(
                  widget.emergency ? Icons.emergency_share_rounded : Icons.call_rounded,
                  color: accent,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(widget.emergency ? 'Emergency call' : 'Place a call',
                        style: theme.textTheme.titleLarge
                            ?.copyWith(fontWeight: FontWeight.w800)),
                    Text(widget.name == null || widget.name!.isEmpty
                        ? widget.number
                        : '${widget.name} · ${widget.number}',
                        style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant)),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 18),

          // The voice message we'll speak once connected.
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.5),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.record_voice_over_rounded,
                        size: 16, color: theme.colorScheme.onSurfaceVariant),
                    const SizedBox(width: 6),
                    Text(
                        widget.audioUrl != null && widget.audioUrl!.isNotEmpty
                            ? 'Guardian voice played when answered'
                            : 'Spoken aloud when answered',
                        style: theme.textTheme.bodySmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: theme.colorScheme.onSurfaceVariant)),
                  ],
                ),
                const SizedBox(height: 8),
                Text('“${widget.message}”',
                    style: theme.textTheme.bodyMedium?.copyWith(height: 1.35)),
              ],
            ),
          ),
          const SizedBox(height: 14),

          _statusRow(context, status),

          if (_outcome != null && !_outcome!.placed) ...[
            const SizedBox(height: 12),
            Text(_outcome!.reason ?? 'Couldn\'t place the call.',
                style: theme.textTheme.bodySmall?.copyWith(color: AppTheme.danger)),
          ],

          const SizedBox(height: 18),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _calling ? null : () => Navigator.of(context).maybePop(),
                  child: const Text('Cancel'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 2,
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(
                    backgroundColor: accent,
                    minimumSize: const Size(0, 54),
                  ),
                  onPressed: (status?.canCall == true && !_calling) ? _call : null,
                  icon: _calling
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.call_rounded),
                  label: Text(_calling ? 'Calling…' : 'Call now'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _statusRow(BuildContext context, TelephonyStatus? status) {
    if (status == null) {
      return const Row(
        children: [
          SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 8),
          Text('Checking phone & SIM…'),
        ],
      );
    }
    final ok = status.canCall;
    return Row(
      children: [
        Icon(ok ? Icons.sim_card_rounded : Icons.warning_amber_rounded,
            size: 18, color: ok ? AppTheme.good : AppTheme.warn),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            ok ? 'Phone & SIM ready' : status.reason,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: ok ? AppTheme.good : AppTheme.warn,
                fontWeight: FontWeight.w600),
          ),
        ),
      ],
    );
  }
}
