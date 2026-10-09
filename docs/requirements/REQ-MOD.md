<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Models (MOD)

A model wraps a simulation so that the VV&UQ tools can execute it as a black box.

### REQ-MOD-001 — A model is a GEMSEO discipline

- **Statement:** Every VIMSEO model shall be a GEMSEO `Discipline`, with typed input
  and output grammars, so that any GEMSEO or VIMSEO tool can execute it.
- **Rationale:** The tools are generic; they must not depend on the model.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-MOD-002 — A model is discovered by name

- **Statement:** The system shall create a model from its name and its load case, the
  models of the plugins included.
- **Rationale:** Studies and workflows are described in files, by names.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-MOD-003 — A load case declares its plots

- **Statement:** A load case should declare the plots of its model outputs in code,
  next to the load case, rather than in separate configuration files.
- **Rationale:** The plots of a load case must evolve with it and be checked by the tests.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-MOD-004 — A simulation is not run twice

- **Statement:** A model should reuse the result of a simulation already executed with
  the same inputs (cache), and the reuse shall remain traceable (REQ-STO-003).
- **Rationale:** Simulations are expensive.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —
