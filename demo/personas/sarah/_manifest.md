---
persona_id: sarah
doc_type: manifest
synthetic: true
note: Synthetic demo persona — NOT a real individual.
---

# Sarah Okafor — Persona Record (Vector-Store Source)

This folder is Sarah's **personal knowledge record**: the documents Guardian
embeds into its vector store and recalls (via the `recall_history` tool) during
a turn. Each document is the output of a **data-extraction step that happens
once, at onboarding** — not something typed by hand. This manifest is the
"how we got this data" layer.

The format is **identical to Matthew's record** (same doc set, same provenance
frontmatter, same controlled vocabulary) so the two personas read as outputs of
the *same* extraction pipeline.

## How the record is built (extraction pipeline)

```
Onboarding (one-time, at installation)
  ├─ Guided voice INTERVIEW ........... → profile, daily rhythm, interests, mood, contacts
  ├─ DOCUMENT uploads (scanned PDFs/photos)
  │     ├─ medication list (pharmacy printout) ... → medications
  │     ├─ blood panel + PHQ-9 screen (PDF) ...... → lab_results   (OCR → table parse → normalize)
  │     └─ physiatry/rehab discharge summary (PDF) → medical_history (merged with interview)
  └─ CONSENT wizard (resident + supporter) ........ → care_plan, contacts, consent matrix
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
| `01_medical_history.md` | medical_history | mixed | Interview (self-report) + 2019 rehab discharge summary (PDF, OCR) | medium-high |
| `02_medications.md` | medications | document_upload | Pharmacy med-list printout (OCR) | high |
| `03_lab_results.md` | lab_results | document_upload | Blood panel + PHQ-9 depression screen (scanned PDF, OCR) | high |
| `04_care_plan_and_contacts.md` | care_plan | consent_wizard | Contacts & consent setup form (supporter co-present) | high |

## Source types (controlled vocabulary — reused across personas)

- **onboarding_interview** — captured from the guided voice setup session (ASR → structured).
- **document_upload** — extracted from a scanned PDF or photo (OCR → parse → normalize).
- **mixed** — reconciled from more than one of the above.
- **consent_wizard** — entered as a structured form during setup.
- **sensor_baseline** — derived from the watch's first days of data (not used here yet).

## Relationship to the relational data

This record is the **vector** half of Sarah's data. The **relational** half —
recreation programs, accessible facility attributes, Wheel-Trans service, parks
& washrooms — is public **Toronto Open Data**, seeded separately. The scenario
walkthrough tags every step 🟪 VECTOR (this record) or 🟦 RELATIONAL (Toronto
Open Data) so the two sources are never confused.
