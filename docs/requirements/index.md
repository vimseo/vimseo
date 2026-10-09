<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# VIMSEO requirements

This section states **what VIMSEO must do**, independently of how a given feature
implements it. The requirements are stable: they outlive the branches and the
features that satisfy them.

The *how* lives in the SPDD specifications (REASONS canvases), see
[Specifications](../specs/index.md). Each canvas lists the requirements it satisfies,
and each requirement lists the canvases that satisfy it.

## Areas

| Area | File | Scope |
|---|---|---|
| MOD | [Models](REQ-MOD.md) | `IntegratedModel`, components, load cases, model discovery |
| TOOL | [Tools](REQ-TOOL.md) | the `BaseTool` contract: inputs, settings, execution, subtools |
| RES | [Results](REQ-RES.md) | tool results: visualization, tabulation, persistence, reload |
| STO | [Storage and traceability](REQ-STO.md) | run archive, tool archive, identifiers |
| SER | [Serialization](REQ-SER.md) | settings, spaces and distributions written in clear |
| DEP | [Deployment](REQ-DEP.md) | mandatory dependencies, extras, HPC profile, platforms |
| WF | [Workflows](REQ-WF.md) | chaining tools, workflow files, workflow execution |
| UX | [User interfaces](REQ-UX.md) | Python API, command line, dashboards |
| NFR | [Non-functional](REQ-NFR.md) | reproducibility, compatibility, performance, tests |

## Writing a requirement

A requirement is identified by `REQ-<AREA>-<NNN>`. An identifier is never reused nor
renumbered: a requirement which no longer applies is marked `Deprecated`, with the
identifier of the requirement replacing it, if any.

```markdown
### REQ-STO-003 — A tool result is traceable to the simulations it used

- **Statement:** The system shall ...
- **Rationale:** Why it matters for a VV&UQ user.
- **Priority:** Must | Should | Could
- **Status:** Proposed | Accepted | Implemented | Deprecated
- **Verification:** Test | Example | Inspection — where it is checked.
- **Satisfied by:** SPEC-NNN, ...
```

Guidelines:

- One requirement states one need, with "shall" (Must) or "should" (Should, Could).
- State the need of the user, not the design: "a tool result can be visualized
  without its tool", not "`BaseResult` has a `visualize()` method". The design goes
  in the canvas.
- A requirement is verifiable: name the test, the runnable example or the inspection
  which checks it.
- `Satisfied by` lists the canvases (`SPEC-NNN`) implementing it, in both directions.

## Lifecycle

1. A requirement is added as `Proposed`, usually by a `/spdd-analysis` of a new need,
   in the same pull request as the canvas using it.
2. It becomes `Accepted` when the pull request is reviewed.
3. It becomes `Implemented` when a canvas satisfying it is `Implemented`
   and its verification passes.

## Glossary

- **Simulation:** one execution of a model, identified by its `run_id`.
- **Tool run:** one execution of a tool, identified by its `tool_run_id`. A tool run
  launched by another tool run (a subtool) is its child.
- **Run archive:** the storage of the simulations (`DirectoryArchive`, `MlflowArchive`).
- **Tool archive:** the storage of the tool results (`DirectoryToolArchive`,
  `MlflowToolArchive`).
- **Canvas:** a REASONS structured prompt describing one feature, in `spdd/prompt/`.
