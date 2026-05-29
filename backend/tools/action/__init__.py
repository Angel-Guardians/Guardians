"""Action bucket of the Tool Bus.

Tools that change the world: tts (voice output), notification_dispatcher
(tiered: whisper/nudge/alarm/call), ambient_lights, emergency_caller,
contact_tree, ui_renderer, tap_confirm.

Every Action tool accepts a `severity` enum so the same tool whispers a
text or makes a voice call depending on the level.
"""
