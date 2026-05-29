"""Integrations bucket of the Tool Bus.

Tools that talk to external systems. Almost all egress lives here, which
means almost everything in this bucket is wrapped with @consent_check.

Fitbit / Apple Health, Dexcom / Omron, Google / Apple Calendar, Pharmacy
refill, EHR / FHIR share, Twilio voice + SMS, Counselor / Officer portal,
Spotify (calming music).
"""
