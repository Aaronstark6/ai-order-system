# AI Order System — PROJECT STATUS

## Current Branch

v4-core-codex-rebuild

---

## Current Stable Tag

v4.0-chat-to-excel

Commit:

0eb3739

Message:

V4-FIX27 add chat to Excel E2E API

---

## Current Collaboration Model

### ChatGPT

Role:

System Brain

Responsibilities:

- GitHub audit
- architecture analysis
- root cause analysis
- risk control
- workflow design
- task decomposition
- Solo / Codex decision
- modification strategy
- verification strategy

ChatGPT decides.

ChatGPT does not allow execution tools to freely redesign architecture.

---

### SOLO

Role:

Low-cost execution layer

Suitable for:

- small APIs
- imports
- helper files
- small fixes
- compile validation
- simple audit execution
- small documentation tasks

SOLO executes exact instructions only.

No free refactor.

No free optimization.

---

### Codex

Role:

High-value engineering executor

Reserved for:

- multi-file modifications
- state-flow changes
- architecture work
- workflow integration
- high-risk refactors
- frontend workflow work
- productization tasks
- large debugging tasks

---

### Git

Git commands are executed manually by project owner.

Not by Solo.

---

## Current Product Architecture

Current V4 architecture:

Chat Text
↓
Chat Preprocess
↓
AI Parse
↓
Flat Fields
↓
V4 Order Normalizer
↓
V4 Order Object
↓
Template Profile Rules
↓
Core Pipeline
↓
Render Preview
↓
Excel Export

---

## Current Completed Milestones

### V4-FIX16

Backend foundation for Template Profiles.

---

### V4-FIX17

Profile-based mapping rules.

---

### V4-FIX18

Profile debug visibility.

---

### V4-FIX20

Active template profile selection.

---

### V4-FIX22

Ignore runtime generated profile data.

---

### V4-FIX23

V4 Order Object payload input API.

---

### V4-FIX24

V4 Order Object Normalizer.

flat fields

↓

V4 order_object

---

### V4-FIX25

Chat → Order Object API.

POST:

/api/v4/parse-chat-to-order-object

---

### V4-FIX26

Chat → Pipeline E2E API.

POST:

/api/v4/parse-chat-run-pipeline

---

### V4-FIX27

Chat → Excel E2E API.

POST:

/api/v4/parse-chat-export-excel

Validated:

Chat
↓
AI Parse
↓
Order Object
↓
Pipeline
↓
Render Preview
↓
Excel Export

Real verification passed.

Verified values:

Anna → C5

50000 → C6

20260518 → F4

Excel file generated successfully.

---

## Current Verified Facts

Template Upload

→ Template Analysis

→ Auto Mapping Preview

→ Mapping Workbench

→ Saved Rules

→ Builder

→ Core Pipeline

→ Render Preview

→ Excel Export

Core Pipeline does NOT directly consume template_analysis.

Only saved rules are used.

This is confirmed design behavior.

---

## Next Recommended Direction

Recommended next phase:

V4 Chat Workspace UI.

Goal:

Transform V4 from backend capability into usable product workflow.

Possible flow:

Chat Input
↓
Parse
↓
Order Object Preview
↓
Pipeline Preview
↓
Template Upload
↓
Export Excel

Likely suitable for Codex.