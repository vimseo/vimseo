<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Tools (TOOL)

A tool performs one VV&UQ analysis (DOE, sensitivity, calibration, verification,
validation, surrogate, statistics, Bayesian analysis, design value) on models or data.

### REQ-TOOL-001 — A tool validates its inputs and settings

- **Statement:** Every tool shall declare its inputs and settings as validated schemas,
  and reject unknown or invalid ones before executing anything.
- **Rationale:** A typo in a setting must not silently produce a wrong study.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-TOOL-002 — A tool produces a typed result

- **Statement:** Every tool shall store its outcome in a result object of a class
  dedicated to the tool, independent of the tool instance.
- **Rationale:** The result is the deliverable; see REQ-RES-*.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-006

### REQ-TOOL-003 — A tool can be composed of subtools

- **Statement:** A tool may execute other tools; the subtools shall inherit the
  configuration of their parent (archive, working directory) unless overridden.
- **Rationale:** Complex VV&UQ analyses are built from simpler ones.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** SPEC-004
