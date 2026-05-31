---
persona_id: matthew
doc_type: lab_results
source_type: document_upload
source_ref: "LifeLabs blood panel (collected 2025-04-18) + St. Michael's ECG/echo reports — scanned PDFs"
captured_on: 2025-04-20
extraction_method: "OCR of scanned PDF → table extraction → LLM normalization to standard test names/units → automatic out-of-range flagging"
confidence: high
last_reviewed: 2025-05-20
synthetic: true
note: Synthetic demo persona — NOT a real individual. Values illustrative but clinically coherent.
---

# Matthew Brennan — Recent Lab & Diagnostic Results

> **Provenance.** Extracted from scanned **lab and diagnostic PDFs** uploaded at
> onboarding: a LifeLabs blood panel (drawn 2025-04-18) plus St. Michael's
> ECG/echocardiogram reports. The scans were OCR'd, the result tables parsed,
> test names and units normalized, and out-of-range values flagged
> automatically. This is the canonical "extracted from a bloodwork PDF" document
> Guardian recalls during a turn (e.g. "your last potassium was low-normal").

## Bloodwork — drawn 2025-04-18 (most recent)
| Test | Result | Reference range | Flag |
|---|---|---|---|
| Hemoglobin | 128 g/L | 135–175 | **Low** (mild anemia) |
| Platelets | 210 ×10⁹/L | 150–400 | Normal |
| Sodium | 139 mmol/L | 135–145 | Normal |
| Potassium | 3.6 mmol/L | 3.5–5.1 | Low-normal |
| Creatinine | 132 µmol/L | 64–110 | **High** |
| eGFR | 52 mL/min/1.73m² | >60 | **Low** (CKD stage 3a) |
| HbA1c | 6.9 % | <7.0 target | At target |
| LDL cholesterol | 1.7 mmol/L | <2.0 target | At target |
| NT-proBNP | 612 ng/L | age-adjusted elevated | **Elevated** (consistent with HFpEF) |
| Troponin (baseline) | <14 ng/L | <14 | Normal at baseline |
| TSH | 2.1 mIU/L | 0.4–4.0 | Normal |

## ECG — 2025-02-10 (clinic)
- Underlying **normal sinus rhythm** with documented **paroxysmal AFib** on prior tracings.
- Q waves in inferior leads consistent with **prior inferior MI**.
- QTc 446 ms (upper-normal — relevant if new QT-prolonging drugs are added).

## Echocardiogram — 2025-02-10
- **EF approx 55%** (preserved). Mild left-ventricular diastolic dysfunction.
- Mild mitral regurgitation. No pericardial effusion.

## 24-hour Holter — 2024-11
- Several short runs of AFib (longest 22 minutes), max ventricular rate 142 bpm.
- Two brief pauses (<2.5 s) — flagged for follow-up; no pacemaker yet.

## Clinically relevant takeaways
- **Anticoagulated (apixaban)** — bleeding risk; a head strike would warrant imaging.
- **Reduced kidney function** — affects drug dosing.
- **Documented AFib with rapid rates + brief pauses** — predisposes to arrhythmic
  syncope and raises cardiac-arrest risk.
- **Mild anemia + low-normal potassium** — less physiological reserve.
