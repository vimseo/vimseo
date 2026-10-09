<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Non-functional requirements (NFR)

### REQ-NFR-001 — A study is reproducible

- **Statement:** The archive of a tool run should hold everything needed to re-execute
  it: the settings, the inputs, the version of VIMSEO and of the models.
- **Rationale:** Reproducibility is a credibility criterion of a simulation.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Inspection.
- **Satisfied by:** SPEC-001, SPEC-004

### REQ-NFR-002 — Breaking changes are explicit

- **Statement:** A change breaking the public API or the archive format shall be marked
  as breaking (`!` in the conventional commit), documented in the changelog with its
  migration path.
- **Rationale:** Users keep archives and scripts across versions.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Inspection — pull request review.
- **Satisfied by:** —

### REQ-NFR-003 — The fast tests run in a few minutes

- **Statement:** The default test run (`pytest`, without the `slow` and `very_slow`
  markers) should stay fast enough to run before each commit.
- **Rationale:** Slow tests are skipped, and regressions pass.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** CI duration.
- **Satisfied by:** —

### REQ-NFR-004 — The tests do not write in the user's archive

- **Statement:** The tests shall not write in the archives of the configuration of the
  user.
- **Rationale:** Running the tests must not pollute real studies.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Inspection — `conftest.py`.
- **Satisfied by:** SPEC-004
