<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Storage and traceability (STO)

The simulations and the tool results are archived, and the evidence of a VV&UQ
conclusion can be followed from the conclusion down to each simulation.

### REQ-STO-001 — The simulations are archived locally by default

- **Statement:** The system shall archive the simulations in a local directory when no
  archive is configured, without any server nor optional dependency.
- **Rationale:** A model must be usable on a laptop or an HPC node with no tracking
  server.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/storage_management/`.
- **Satisfied by:** —

### REQ-STO-002 — A simulation and a tool run are uniquely identified

- **Statement:** The system shall give every simulation a unique `run_id`, and every
  tool run a unique `tool_run_id`. A simulation shall carry the `tool_run_id` of the
  tool run which executed it.
- **Rationale:** Identifiers are the base of every link between archived objects.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-STO-003 — A tool result is traceable to the simulations it used

- **Statement:** The system shall record, in every tool result, the `run_id` of the
  simulations it used, including those of its subtools and those read from the model
  cache.
- **Rationale:** Credibility evidence must be auditable from a VV&UQ conclusion down to
  each simulation.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-STO-004 — The tool results are archived

- **Statement:** The system shall archive the result of every tool run, with a
  searchable summary (tool, date, settings, parent tool run), in a local directory or
  in MLflow, and shall allow the archive to be disabled.
- **Rationale:** A study is made of many tool runs; they must be found and compared
  after the session which produced them.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-STO-005 — A subtool is archived like its parent

- **Statement:** A tool executed by another tool shall be archived in the same archive
  as its parent, and linked to the tool run of its parent.
- **Rationale:** A VV&UQ tool (validation case, calibration) is built from subtools; its
  archive must show the whole tree.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-STO-006 — An archive does not alter the global state of its backend

- **Statement:** Opening or writing an archive shall not change any process-wide state
  of its backend (e.g. the global MLflow tracking URI or active run).
- **Rationale:** Several archives, and the user's own MLflow usage, must coexist in one
  process.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-STO-007 — The key values of a tool result are searchable

- **Statement:** The archive should expose the key scalar values of a tool result
  (e.g. validation metrics, sensitivity indices) as searchable metrics.
- **Rationale:** Comparing tool runs should not require loading every result file.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —
