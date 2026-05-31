---
persona_id: sarah
doc_type: lab_results
source_type: document_upload
source_ref: "LifeLabs blood panel (collected 2025-04-25) + PHQ-9 depression screen (clinic, 2025-04-25) — scanned PDFs"
captured_on: 2025-04-28
extraction_method: "OCR of scanned PDF → table extraction → LLM normalization to standard test names/units → automatic out-of-range flagging"
confidence: high
last_reviewed: 2025-05-22
synthetic: true
note: Synthetic demo persona — NOT a real individual. Values illustrative but clinically coherent.
---

# Sarah Okafor — Recent Lab & Screening Results

> **Provenance.** Extracted from scanned **clinical PDFs** uploaded at
> onboarding: a LifeLabs blood panel (drawn 2025-04-25) plus a PHQ-9 depression
> screen completed the same day. The scans were OCR'd, the result tables parsed,
> test names and units normalized, and out-of-range / clinically notable values
> flagged automatically. This is the canonical "extracted from a clinical PDF"
> document Guardian recalls during a turn.

## Bloodwork — drawn 2025-04-25 (most recent)
| Test | Result | Reference range | Flag |
|---|---|---|---|
| Hemoglobin | 124 g/L | 120–155 | Normal |
| Ferritin | 18 µg/L | 15–150 | Low-normal |
| Vitamin D (25-OH) | 58 nmol/L | 75–250 | **Low** (supplementing) |
| TSH | 2.4 mIU/L | 0.4–4.0 | Normal |
| Sodium | 140 mmol/L | 135–145 | Normal |
| Potassium | 4.2 mmol/L | 3.5–5.1 | Normal |
| Creatinine | 71 µmol/L | 49–90 | Normal |
| HbA1c | 5.3 % | <5.7 (non-diabetic) | Normal |
| CRP | 2.1 mg/L | <3.0 | Normal |

## PHQ-9 depression screen — 2025-04-25 (clinic)
- **Score: 14 / 27 → moderate depression.** (Prior screen 2025-01: 11, mild–moderate.)
- Notable items: low energy, reduced interest/pleasure, sleeping more than usual.
- No item-9 (self-harm) endorsement on this screen.
- Clinician note: continue sertraline; encourage activity, social re-engagement,
  and structured routine.

## Clinically relevant takeaways
- **Moderate, recurrent depression** — multi-day isolation is an expected pattern.
- **Activity and social re-engagement are part of the care plan.**
- **Low vitamin D / low-normal ferritin** — contributes to fatigue and low energy.
