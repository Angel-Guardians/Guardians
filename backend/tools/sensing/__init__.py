"""Sensing bucket of the Tool Bus.

Tools that read the world: audio_listener, bio_marker (wearable vitals),
env_signal, manual_input, vision_motion, geolocation, wake_stt.

Fill in one file per tool. Each tool: Pydantic ArgsModel + ResultModel +
@register_tool + @audit_log decorator.
"""
