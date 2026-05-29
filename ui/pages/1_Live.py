"""Live page - event stream + active transcript.

Subscribes to /events/sse from the Backend. Renders the Event Log table
in reverse-chronological order plus the active transcript pane.
"""
from __future__ import annotations

import streamlit as st


def main() -> None:
    st.title("Live")
    st.caption("Event stream + active transcript")
    # TODO: open SSE connection to settings.backend_url/events/sse
    #       render two columns: event table + transcript pane
    st.info("Live event stream will appear here.")


if __name__ == "__main__":
    main()
