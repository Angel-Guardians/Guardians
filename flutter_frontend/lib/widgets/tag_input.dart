import 'package:flutter/material.dart';

/// A chip-based tag editor: type + Enter to add, tap × to remove.
class TagInput extends StatefulWidget {
  const TagInput({
    super.key,
    required this.tags,
    required this.onChanged,
    this.hint = 'Add…',
    this.color,
  });

  final List<String> tags;
  final ValueChanged<List<String>> onChanged;
  final String hint;
  final Color? color;

  @override
  State<TagInput> createState() => _TagInputState();
}

class _TagInputState extends State<TagInput> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _add(String raw) {
    final value = raw.trim();
    if (value.isEmpty) return;
    if (widget.tags.any((t) => t.toLowerCase() == value.toLowerCase())) {
      _controller.clear();
      return;
    }
    widget.onChanged([...widget.tags, value]);
    _controller.clear();
  }

  void _remove(int i) {
    final next = [...widget.tags]..removeAt(i);
    widget.onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? Theme.of(context).colorScheme.primary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.tags.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (var i = 0; i < widget.tags.length; i++)
                  Chip(
                    label: Text(widget.tags[i]),
                    backgroundColor: color.withOpacity(0.10),
                    side: BorderSide(color: color.withOpacity(0.35)),
                    labelStyle:
                        TextStyle(color: color, fontWeight: FontWeight.w600),
                    deleteIconColor: color,
                    onDeleted: () => _remove(i),
                  ),
              ],
            ),
          ),
        TextField(
          controller: _controller,
          decoration: InputDecoration(
            hintText: widget.hint,
            suffixIcon: IconButton(
              icon: const Icon(Icons.add),
              onPressed: () => _add(_controller.text),
            ),
          ),
          textInputAction: TextInputAction.done,
          onSubmitted: _add,
        ),
      ],
    );
  }
}
