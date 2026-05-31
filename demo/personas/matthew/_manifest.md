---
persona_id: matthew
doc_type: manifest
synthetic: true
note: Synthetic demo persona — NOT a real individual.
---

# Matthew Brennan — Persona Record (Vector-Store Source)

This folder is Matthew's **personal knowledge record**: the documents Guardian
embeds into its vector store and recalls (via the `recall_history` tool) during
a turn. Each document is the output of a **data-extraction step that happens
once, at onboarding** — not something typed by hand. This manifest is the
"how we got this data" layer.

## How the record is built (extraction pipeline)

```
Onboarding (one-time, at installation)
  ├─ Guided voice INTERVIEW ........... → profile, daily rhythm, self-reported history, contacts
  ├─ DOCUMENT uploads (scanned PDFs/photos)
  │     ├─ medication list + pill-bottle labels ... → medications
  │     ├─ lab panel + ECG/echo reports (PDF) ..... → lab_results   (OCR → table parse → normalize)
  │     └─ cardiology discharge summary (PDF) ..... → medical_history (merged with interview)
  └─ CONSENT wizard (resident + caregiver) ........ → care_plan, contacts, consent matrix
        │
        ▼
  chunk per section → embed → vector store → recalled at runtime via recall_history
```

Every document carries the same provenance frontmatter:
`source_type` · `source_ref` · `captured_on` · `extraction_method` ·
`confidence` · `last_reviewed`.

## Documents in this record

| File | doc_type | source_type | Source (how we got it) | Confidence |
|---|---|---|---|---|
| `00_profile.md` | profile | onboarding_interview | Spoken setup interview + watch pairing | high |
| `01_medical_history.md` | medical_history | mixed | Interview (self-report) + 2021 discharge summary (PDF, OCR) | medium-high |
| `02_medications.md` | medications | document_upload | Pharmacy med-list printout + pill-bottle label photos (OCR) | high |
| `03_lab_results.md` | lab_results | document_upload | LifeLabs blood panel + ECG/echo reports (scanned PDF, OCR) | high |
| `04_care_plan_and_contacts.md` | care_plan | consent_wizard | Contacts & consent setup form (caregiver co-present) | high |

## Source types (controlled vocabulary — reused across personas)

- **onboarding_interview** — captured from the guided voice setup session (ASR → structured).
- **document_upload** — extracted from a scanned PDF or photo (OCR → parse → normalize).
- **mixed** — reconciled from more than one of the above.
- **consent_wizard** — entered as a structured form during setup.
- **sensor_baseline** — derived from the watch's first days of data (not used here yet).

## Relationship to the relational data

This record is the **vector** half of Matthew's data. The **relational** half —
ambulance stations, paramedic incident data, AED locations — is public **Toronto
Open Data**, seeded separately. The scenario walkthrough tags every step
🟪 VECTOR (this record) or 🟦 RELATIONAL (Toronto Open Data) so the two sources
are never confused.
