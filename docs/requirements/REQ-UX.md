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
- **Satisfied by:** SPEC-007, SPEC-009, SPEC-010

### REQ-UX-002 — A tool result is visualized from the command line

- **Statement:** The system shall visualize and tabulate a tool result from its URI with
  a command line, without writing Python.
- **Rationale:** Reviewers of a study are not all Python users.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-007

### REQ-UX-003 — The dashboards open without error

- **Statement:** Every dashboard shall start and render its first page without error
  when its extra is installed.
- **Rationale:** Dashboards are rarely tested by hand; regressions go unnoticed.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test — `tests/dashboards/`.
- **Satisfied by:** —

### REQ-UX-004 — Models and tools share one vocabulary for their archives

- **Statement:** The settings locating an archive (`archive_manager`,
  `directory_archive_root`) shall have the same names, meanings and defaults for the
  models, the tools and the loading functions; the object giving access to an archive
  shall be called an archive manager everywhere.
- **Rationale:** Two names for one concept, or one name for two concepts (an archive and
  a working directory), are the first source of confusion reported by the reviewers.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — a model and a tool configured with the same settings archive
  in the same place; Inspection of the docs.
- **Satisfied by:** SPEC-004, SPEC-007, SPEC-010

### REQ-UX-005 — The roundtrip of a result is the same for every kind of result and archive

- **Statement:** Generating, saving, finding, loading and visualizing a result should use
  the same pattern for a model result and a tool result, and the same code for a
  Directory and an MLflow archive, the archive manager aside.
- **Rationale:** Users should learn one pattern, not one per backend and kind of result.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Example — `14_data_management/plot_01_roundtrip`; Test of the API.
- **Satisfied by:** SPEC-009, SPEC-010

### REQ-UX-006 — Data management is taught by progressive examples

- **Statement:** The documentation should teach data management from a stripped-down,
  usage-oriented roundtrip to the details of each archive, in one gallery.
- **Rationale:** The current examples mix usage and internals; new users find the
  roundtrip too technical.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Inspection — review of the gallery `14_data_management`.
- **Satisfied by:** SPEC-010
