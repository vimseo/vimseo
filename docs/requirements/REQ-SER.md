<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Serialization (SER)

What is archived must remain readable by a human and by another version of VIMSEO.

### REQ-SER-001 — Settings are serialized in clear

- **Statement:** The system shall write the settings and inputs of a tool run in a
  human-readable form (JSON-compatible values), not as pickled objects, including
  Pydantic models, enumerations and paths.
- **Rationale:** An archive must be auditable without Python, and pickles break across
  versions.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test — `tests/tools/test_serialization.py`.
- **Satisfied by:** —

### REQ-SER-002 — Parameter spaces and distributions are serialized in clear

- **Statement:** The system shall write parameter spaces, design spaces and OpenTURNS
  distributions in a readable form from which they can be rebuilt.
- **Rationale:** The uncertainty model is a key part of the evidence of a VV&UQ study.
- **Priority:** Must
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —

### REQ-SER-003 — Reading an archive is tolerant to unknown types

- **Statement:** A value which cannot be serialized in clear should be stored with an
  explicit fallback (e.g. its representation) rather than making the archive fail.
- **Rationale:** Archiving must never lose a tool run because of one exotic setting.
- **Priority:** Should
- **Status:** Proposed
- **Verification:** Test.
- **Satisfied by:** —
