"""Streamlit entry.

Three pages live under ui/pages/:
  1_Live.py       - live event stream + current transcript
  2_Vitals.py     - HR / SpO2 / BP charts
  3_Reminders.py  - today's schedule + intake checklist + tap-to-confirm

Run with `streamlit run ui/app.py` (or `make ui`).
"""
from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Guardian", page_icon=":shield:", layout="wide")
    st.title("Guardian")
    st.caption("Home Emergency AI Companion - always-on, fully local")

    st.markdown(
        """
        Welcome. Use the sidebar to navigate.

        - **Live** - see what Guardian is hearing and doing right now
        - **Vitals** - heart rate, blood pressure, SpO2 trends
        - **Reminders** - today's medications and check-ins
        """
    )


if __name__ == "__main__":
    main()
