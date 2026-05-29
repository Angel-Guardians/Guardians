"""Vitals page - HR / SpO2 / BP charts."""
from __future__ import annotations

import streamlit as st


def main() -> None:
    st.title("Vitals")
    st.caption("Heart rate, SpO2, blood pressure - last 24 hours")
    # TODO: query GET /vitals?kind=hr&since=24h; render Plotly line chart
    st.info("Vitals chart will appear here once the wearable is streaming.")


if __name__ == "__main__":
    main()
