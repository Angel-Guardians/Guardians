# The Spark Hack Series | Presented by NVIDIA

**Location:** Antler Office, OneEleven  
**Address:** [325 Front St W 4th Floor, Toronto](https://www.google.com/maps/search/?api=1&query=43.6432809%2C-79.39026969999999&query_place_id=ChIJ4Z2bl800K4gR0kGHVLYTxM4)  
**Dates:** May 29-31  
**Format:** In Person

Welcome to The Spark Hack Series - Toronto, Hosted by NVIDIA, ASUS, and Antler! We're excited to host a diverse group of builders for a weekend.

---

## Table of Contents

- [Submission Link](#submission-link)
- [Hacker Resources](#hacker-resources)
- [Join The Spark Hack Discord](#join-the-spark-hack-discord)
- [Submit Your Project](#submit-your-project)
- [Getting Situated](#getting-situated)
- [Build Challenges](#build-challenges)
  - [Context](#context)
  - [Challenge Track 1: Economic Systems](#challenge-track-1-economic-systems)
  - [Challenge Track 2: Public Services](#challenge-track-2-public-services)
  - [Challenge Track 3: Urban Operations](#challenge-track-3-urban-operations)
  - [Bounties](#bounties)
- [Judging Criteria](#judging-criteria)
  - [1. Technical Execution & Completeness - 30 Points](#1-technical-execution--completeness---30-points)
  - [2. NVIDIA Ecosystem & Spark Utility - 30 Points](#2-nvidia-ecosystem--spark-utility---30-points)
  - [3. Value & Impact - 20 Points](#3-value--impact---20-points)
  - [4. Innovation & Execution - 20 Points](#4-innovation--execution---20-points)
- [Submission Checklist](#submission-checklist)
- [Agenda - Day 1: May 29](#agenda---day-1-may-29)
- [Agenda - Day 2: May 30](#agenda---day-2-may-30)
- [Agenda - Day 3: May 31](#agenda---day-3-may-31)
- [Sponsors](#sponsors)

---

## Submission Link

[SUBMIT YOUR PROJECT HERE!](https://airtable.com/appWQWPtBqDUhCPPj/shrjv9xAoxSXUYju9)

---

## Hacker Resources

- [Demo Video Instructions](https://concrete-panther-c83.notion.site/Demo-Video-Instructions-36ff567d17cc80c3a8f1cbfe14547ef6?pvs=25)
- [DGX Spark Playbooks](https://concrete-panther-c83.notion.site/DGX-Spark-Playbooks-36ff567d17cc80c9bd43eb2033d918dd?pvs=25)
- [DGX Spark Livestreams](https://concrete-panther-c83.notion.site/DGX-Spark-Livestreams-36ff567d17cc80bba535c008b8fedb85?pvs=25)
- [ASUS GX10 Wifi Setup Guide](https://concrete-panther-c83.notion.site/ASUS-GX10-Wifi-Setup-Guide-36ff567d17cc80c0860ce3638ae71a1b?pvs=25)

---

## Join The Spark Hack Discord

[Join The Spark Hack Discord!](https://discord.gg/egPwhV9y)

This will be the easiest way to communicate with our team, get updates on the hackathon, and connect with other hackers. Please join ASAP!

Introduce yourself in the `#introductions` channel and we will add you to our private channel for the hackathon.

---

## Submit Your Project

[SUBMIT YOUR PROJECT!](https://airtable.com/appWQWPtBqDUhCPPj/shrjv9xAoxSXUYju9)

---

## Getting Situated

- [Wifi](https://concrete-panther-c83.notion.site/Wifi-36ff567d17cc80e18d4fcaf38b26d970?pvs=25)

---

## Build Challenges

### Context

All submissions must align with one of the three Challenge Tracks below. Leveraging [open data from the City of Toronto](https://open.toronto.ca/), these tracks guide submissions across diverse facets of urban life and community growth.

Each track defines a theme of impact, not the scope of your idea - teams are free to build any solution using any of the open datasets linked above.

### Challenge Track 1: Economic Systems

**Focus:** Improving how money flows through the city across businesses, workers, and markets.

**The Goal:** Build agentic systems that help individuals and organizations make better economic decisions, unlock opportunities, or optimize costs.

### Challenge Track 2: Public Services

**Focus:** Enhancing how people access and interact with city services and resources.

**The Goal:** Use data to build tools that simplify navigation of public systems, making essential services more accessible, efficient, and user-friendly.

### Challenge Track 3: Urban Operations

**Focus:** Optimizing how Toronto runs, from large-scale infrastructure to everyday city life.

**The Goal:** Develop systems that improve how the city functions behind the scenes and in real time.

### Bounties

- [Best Use of NVIDIA Nemotron](https://concrete-panther-c83.notion.site/Best-Use-of-NVIDIA-Nemotron-36ff567d17cc801e9a02d75f568d3fc0?pvs=25)

---

## Judging Criteria

### Philosophy

We are judging **Systems Engineering**. A winning project isn't just a slide deck or a simple API wrapper; it is a functioning system that ingests raw data, processes it locally using the DGX Spark, and produces a valuable result.

**The Scoring Breakdown:** 100 Points Total

### 1. Technical Execution & Completeness - 30 Points

**Did they actually build a working, complex system?**

- **15 pts - Completeness:** Does the system successfully complete the full data workflow without crashing?
- **15 pts - Technical Depth:** Is there significant engineering "under the hood"? Did they build a complex pipeline, such as Simulation, RAG, Fine-Tuning, or Custom Logic, rather than just a simple static dashboard or basic API wrapper?

### 2. NVIDIA Ecosystem & Spark Utility - 30 Points

**Did they leverage the unique hardware and software provided?**

- **15 pts - The Stack:** Did they use at least one major NVIDIA library/tool? Examples include:
  - NIMs
  - RAPIDS
  - cuOpt
  - Modulus
  - NeMo Models

  **Note:** Merely calling GPT-4 via API gets 0 points here.

- **15 pts - The "Spark Story":** Can they articulate why this runs better on a DGX Spark?

  **Examples:**
  - "We used the 128GB Unified Memory to hold the video buffer and the LLM context simultaneously."
  - "We ran inference locally to ensure privacy/latency."

### 3. Value & Impact - 20 Points

**Is the solution actually useful?**

- **10 pts - Insight Quality:** Is the insight non-obvious and valuable?
  - Example: "Traffic jams happen at 5 PM" is obvious.
  - Example: "Rain causes specific stalls on this specific ramp" is valuable.

- **10 pts - Usability:** Could a real City Planner, or Factory Foreman actually use this tool to make a decision tomorrow?

### 4. Innovation & Execution - 20 Points

**Did they push the boundaries?**

- **10 pts - Creativity:** Did they combine data or models in a novel way?
  - Example: Using vision models to "read" traffic maps.

- **10 pts - Performance:** Did they optimize the system for speed or scale?
  - Example: "We optimized the simulation to run at 50x real-time speed."

---

## Submission Checklist

[Submission Checklist](https://concrete-panther-c83.notion.site/Submission-Checklist-36ff567d17cc80a29ff9e8615f5aa4f0?pvs=25)

---

## Agenda - Day 1: May 29

| Time | Activity |
|---|---|
| 5:00 PM - 6:00 PM | [Doors Open + Check-in](https://concrete-panther-c83.notion.site/Doors-Open-Check-in-36ff567d17cc80fc9e7ad1bf7193ea97?pvs=25) |
| 6:00 PM - 6:45 PM | [Kick Off: Welcome & Hackathon Intro](https://concrete-panther-c83.notion.site/Kick-Off-Welcome-Hackathon-Intro-36ff567d17cc80008b77d759727e25fa?pvs=25) |
| 6:45 PM - 8:00 PM | [Team formation, DGX Spark Checkout](https://concrete-panther-c83.notion.site/Team-formation-DGX-Spark-Checkout-36ff567d17cc808e8263c8913c6b7fef?pvs=25) |
| 8:00 PM - 9:00 PM | [Dinner Served](https://concrete-panther-c83.notion.site/Dinner-Served-36ff567d17cc8062be13c29d40311f74?pvs=25) |
| 9:00 PM onwards | [Hacking Begins](https://concrete-panther-c83.notion.site/Hacking-Begins-36ff567d17cc80a49495ee8e3c6fd86f?pvs=25) |

---

## Agenda - Day 2: May 30

| Time | Activity |
|---|---|
| 9:00 AM | [Breakfast](https://concrete-panther-c83.notion.site/Breakfast-36ff567d17cc80b58aede95a73be53a2?pvs=25) |
| 9:30 AM onwards | [Continue Hacking](https://concrete-panther-c83.notion.site/Continue-Hacking-36ff567d17cc80d79badf6cd500f0d0f?pvs=25) |
| 12:30 PM - 2:30 PM | [Lunch Served](https://concrete-panther-c83.notion.site/Lunch-Served-36ff567d17cc80af9b88cf572a13cb40?pvs=25) |
| 6:30 PM - 7:00 PM | [Progress Checkin](https://concrete-panther-c83.notion.site/Progress-Checkin-36ff567d17cc805db64fd3a9617492fd?pvs=25) |
| 7:00 PM | [Dinner Served](https://concrete-panther-c83.notion.site/Dinner-Served-36ff567d17cc80508917fa820c03bdd2?pvs=25) |
| 7:00 PM onwards | [Overnight Hacking](https://concrete-panther-c83.notion.site/Overnight-Hacking-36ff567d17cc8008bc44e02bc01dd8fc?pvs=25) |

---

## Agenda - Day 3: May 31

| Time | Activity |
|---|---|
| 9:00 AM | [Breakfast](https://concrete-panther-c83.notion.site/Breakfast-36ff567d17cc80749695e3be9f579a07?pvs=25) |
| 11:00 AM | [Code Freeze - Submissions Due!](https://concrete-panther-c83.notion.site/Code-Freeze-Submissions-Due-36ff567d17cc807bbf12fa5b4a4bfb4a?pvs=25) |
| 11:00 AM - 12:00 PM | [NVIDIA Developer Roundtable](https://concrete-panther-c83.notion.site/NVIDIA-Developer-Roundtable-36ff567d17cc8007ba93ef92d6e98940?pvs=25) |
| 12:00 PM - 2:30 PM | [Judging](https://concrete-panther-c83.notion.site/Judging-36ff567d17cc80c4a11ad02ba453951c?pvs=25) |
| 3:00 PM - 4:00 PM | [Finale: NVIDIA Keynote, Awards, Winner Demos](https://concrete-panther-c83.notion.site/Finale-NVIDIA-Keynote-Awards-Winner-Demos-36ff567d17cc805d9384e7f9be466afc?pvs=25) |

If you have any questions, please reach out on the [Developer Discord](https://discord.gg/kzBChvAc).

---

## Sponsors

The PDF includes a section titled "Thank you to our Sponsors" and a sponsor card/link for [NVIDIA](https://concrete-panther-c83.notion.site/NVIDIA-36ff567d17cc804f8af5cfc0fbd8a5d6?pvs=25), but the sponsor content is mostly not visible/readable in the exported PDF pages.

---

## Source Notes

Converted from the uploaded PDF: `The Spark Hack Series _ Presented by NVIDIA.PDF`.

Some linked Notion subpages may require access permissions.
