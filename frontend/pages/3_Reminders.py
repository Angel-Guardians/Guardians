"""Reminders page - today's schedule + intake checklist."""
from __future__ import annotations

import streamlit as st


def main() -> None:
    st.title("Reminders")
    st.caption("Today's medications and check-ins")
    # TODO: query GET /medications?patient_id=1
    #       render checklist with tap-to-confirm buttons
    #       posting POST /events with TapConfirmedEvent
    st.info("Today's reminders will appear here.")


if __name__ == "__main__":
    main()
