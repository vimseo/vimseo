<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# User interfaces (UX)

VIMSEO is used from Python, from the command line and from dashboards.

### REQ-UX-001 — The main operations are exposed by a Python API

- **Statement:** The system shall expose, in `vimseo.api`, the creation of models and
  tools and the loading of archived simulations and tool results.
- **Rationale:** Users should not need to know the internal module layout.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/core/test_api.py`.
- **Satisfied by:** —

### REQ-UX-002 — A tool result is visualized from the command line

- **Statement:** The system shall visualize and tabulate a tool result from its URI with
  a command line, without writing Python.
- **Rationale:** Reviewers of a study are not all Python users.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-UX-003 — The dashboards open without error

- **Statement:** Every dashboard shall start and render its first page without error
  when its extra is installed.
- **Rationale:** Dashboards are rarely tested by hand; regressions go unnoticed.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —
