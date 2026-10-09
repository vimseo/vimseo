<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Workflows (WF)

A workflow chains tools into a study which can be saved, shared and re-executed.

### REQ-WF-001 — A workflow is described in a file

- **Statement:** The system shall save a workflow of tools to a file and execute it from
  that file, from Python or from the command line.
- **Rationale:** A study must be reproducible by someone else, on another machine.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/workflow/`.
- **Satisfied by:** —

### REQ-WF-002 — The tool runs of a workflow are traceable

- **Statement:** The tool runs executed by a workflow should be archived and linked as
  any other tool run (REQ-STO-004, REQ-STO-005).
- **Rationale:** A workflow is the top of the evidence tree of a study.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —
