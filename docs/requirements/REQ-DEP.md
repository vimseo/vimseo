<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Deployment (DEP)

VIMSEO installs and runs on HPC machines with no graphical stack.

### REQ-DEP-001 — Building and executing a core model needs only the mandatory dependencies

- **Statement:** The system shall build a model, execute it and serialize its results
  with the mandatory dependencies only. The dashboard, MLflow, mesh and JAX features
  shall be shipped by extras. The mandatory dependencies shall install without a
  graphical stack (no display, no browser).
- **Rationale:** The HPC user profile has no graphical stack and limited installation
  rights.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tox -e core-py312`, `tests/test_optional_dependencies.py`.
- **Satisfied by:** —
- **Known exception:** executing `TanOpenHole` needs the `mesh` extra.

### REQ-DEP-002 — A missing extra fails loudly, at use time

- **Statement:** Using a feature whose extra is not installed shall raise an error naming
  the extra to install. Discovering or importing the classes shall not fail, nor silently
  hide a class.
- **Rationale:** GEMSEO factories swallow import errors, which makes a class silently
  disappear.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/test_optional_dependencies.py`.
- **Satisfied by:** SPEC-004, SPEC-005

### REQ-DEP-003 — VIMSEO runs on Linux and Windows

- **Statement:** The system shall support Linux and Windows, with Python 3.12.
- **Rationale:** Analysts work on Windows, computations run on Linux clusters.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** CI on both platforms.
- **Satisfied by:** —
