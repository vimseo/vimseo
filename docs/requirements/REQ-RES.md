<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Results (RES)

A tool result is a self-sufficient object: it can be persisted, reloaded, visualized and
tabulated long after, and far from, the tool run which produced it.

### REQ-RES-001 — A result is visualized without its tool

- **Statement:** The system shall produce the figures of a tool result from the result
  alone, without instantiating the tool nor its model.
- **Rationale:** The analyst reading a result is often not the one who ran the tool, and
  may not have the model installed.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — every result class; Example —
  `13_tool_result_management`.
- **Satisfied by:** SPEC-006, SPEC-010

### REQ-RES-002 — A result is tabulated

- **Statement:** The system shall return the numerical values of a tool result as
  tables (DataFrames).
- **Rationale:** Figures are not enough to report or post-process values.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-006

### REQ-RES-003 — The visualization is complete by default and can be narrowed

- **Statement:** Visualizing a result with no setting shall produce all its figures;
  settings should only narrow (variables, figures) or style them.
- **Rationale:** A first look must not require knowing the settings.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-006

### REQ-RES-004 — A result is persisted and reloaded identically

- **Statement:** The system shall save a tool result to a file and load it back with the
  same content and metadata.
- **Rationale:** Results are evidence; their content must not change between sessions.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-001, SPEC-006

### REQ-RES-005 — A result is addressed by a URI

- **Statement:** The system shall load a tool result from a file path, an archived tool
  run directory, or the identifier of the tool run in an archive.
- **Rationale:** Users share and script results by reference, not by copying files.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/storage_management/test_tool_result_uri.py`.
- **Satisfied by:** SPEC-007, SPEC-010

### REQ-RES-006 — The figures are exported as static images

- **Statement:** The figures of a result should be exportable as static images
  (PNG, SVG) for reports, on Linux and Windows.
- **Rationale:** Credibility reports are documents, not interactive pages.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-006
