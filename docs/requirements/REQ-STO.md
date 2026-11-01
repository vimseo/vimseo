<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Storage and traceability (STO)

The simulations and the analysis node results are archived, and the evidence of a VV&UQ
conclusion can be followed from the conclusion down to each simulation.

### REQ-STO-001 — The simulations are archived locally by default

- **Statement:** The system shall archive the simulations in a local directory when no
  archive is configured, without any server nor optional dependency.
- **Rationale:** A model must be usable on a laptop or an HPC node with no tracking
  server.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/storage_management/`.
- **Satisfied by:** SPEC-009

### REQ-STO-002 — A simulation and an analysis node run are uniquely identified

- **Statement:** The system shall give every simulation a unique `run_id`, and every
  analysis node run a unique `analysis_node_run_id`. A simulation shall carry the `analysis_node_run_id` of the
  analysis node run which executed it.
- **Rationale:** Identifiers are the base of every link between archived objects.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/core/test_run_ids.py`, `tests/analysis_nodes/test_analysis_node_run_ids.py`.
- **Satisfied by:** SPEC-003

### REQ-STO-003 — An analysis node result is traceable to the simulations it used

- **Statement:** The system shall record, in every analysis node result, the `run_id` of the
  simulations it used, including those of its sub-analysis nodes and those read from the model
  cache.
- **Rationale:** Credibility evidence must be auditable from a VV&UQ conclusion down to
  each simulation.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-003, SPEC-004, SPEC-005

### REQ-STO-004 — The analysis node results are archived

- **Statement:** The system shall archive the result of every analysis node run, with a
  searchable summary (analysis node, date, settings, parent analysis node run), in a local directory or
  in MLflow, and shall allow the archive to be disabled.
- **Rationale:** A study is made of many analysis node runs; they must be found and compared
  after the session which produced them.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/storage_management/test_analysis_node_archive.py`.
- **Satisfied by:** SPEC-004, SPEC-005, SPEC-011

### REQ-STO-005 — A sub-analysis node is archived like its parent

- **Statement:** An analysis node executed by another analysis node shall be archived in the same archive
  as its parent, and linked to the analysis node run of its parent.
- **Rationale:** A VV&UQ analysis node (validation case, calibration) is built from sub-analysis nodes; its
  archive must show the whole tree.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-004, SPEC-005, SPEC-011

### REQ-STO-006 — An archive does not alter the global state of its backend

- **Statement:** Opening or writing an archive shall not change any process-wide state
  of its backend (e.g. the global MLflow tracking URI or active run).
- **Rationale:** Several archives, and the user's own MLflow usage, must coexist in one
  process.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-002, SPEC-005, SPEC-011

### REQ-STO-007 — The key values of an analysis node result are searchable

- **Statement:** The archive should expose the key scalar values of an analysis node result
  (e.g. validation metrics, sensitivity indices) as searchable metrics.
- **Rationale:** Comparing analysis node runs should not require loading every result file.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-005

### REQ-STO-008 — The runs of an archive are grouped by study

- **Statement:** The system shall group the simulations and the analysis node runs of an archive
  by study, with the same meaning for every archive manager, and shall find a run from
  its identifier whatever its study.
- **Rationale:** Several studies (e.g. one per layup) share an archive, or an MLflow
  server shared by a team, without mixing their runs nor losing the links between them.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/storage_management/`.
- **Satisfied by:** SPEC-011, SPEC-005

### REQ-STO-009 — Archive maintenance is explicit

- **Statement:** No exploration, selection, inspection nor dashboard action shall delete
  archived runs; deleting runs shall only be possible through an explicit method of the
  archive manager.
- **Rationale:** Study scripts deleted duplicate runs silently at each start
  (`JobBundle.remove_duplicate_jobs(delete_dirs=True)`); archives are evidence.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test; Inspection of the verbs of the collection.
- **Satisfied by:** SPEC-010
