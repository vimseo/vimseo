# SPDD Analysis: Data management examples and a simpler results roundtrip

## Original Business Requirement

SPEC-010. Review feedback on feat/result-visualization about data management (model
results and tool results). (1) Create a dedicated example sub-folder for data management
(model results and tool results). A first example explains the roundtrip generate, save,
reload, visualize, very stripped down and usage oriented; e.g. a table compares the API
functions involved for Directory vs MLflow and model results vs tool results. Then 3
small examples for the basic operation (roundtrip storage/load/visualization). Then 4
examples: model results with DirectoryArchive, model results with MlflowArchive, tool
results with DirectoryArchive, tool results with MlflowArchive. (2) In the examples, show
load_tool_result() next to tool_archive_manager.get_tool_result(tool_run_id), since both
tell how to load a result; name the simulations variable model_results when they are
ModelResult objects. (3) The user finds the roundtrip rather technical (function names,
CLI commands): see whether it can be simplified, e.g. ideas from JobBundle (SPEC-009).
Existing examples: docs/runnable_examples/02_integrated_models/plot_03_model_result_management.py,
docs/runnable_examples/13_tool_result_management/*. Related canvases: SPEC-004, SPEC-006,
SPEC-007, SPEC-009.

Original review notes (French, verbatim):

> remonter le load_tool_results() à coté du result = tool_archive.get_tool_result(design_value_id),
> car les deux indiquent comment charger un result simulations: indiquer que la var
> simulation sont des model_results.
>
> Globalement, on pourrait faire un sous dossier d'exemple dédié au data management
> (modèles results et tool results. Un premier exemple explique le round trip génération,
> sauvegarde, rechagement, visualisation, de façon très épurée (orienté utilisation). Par
> ex un tableau compare les fonction d'api en jeu, pour Directory, Mlflow, modèle results,
> tool results. Faire 3 petits exemples pour le fonctionnement basique (roundtrip
> stockage/load/visu). Puis, 4 exemples : 1 pour model results DirectoryArchive, 1 pour
> model results MlFlowArchive , 1 pour tool results DirectoryArchive, 1 pour tool results
> results MlFlowArchive
>
> L'utilisateur trouve le roundtrip assez technique (nom des fonctions, commandes CLI), à
> voir si une simplification peut être apportée

## Domain Concept Identification

### Existing Concepts (from codebase)

- **Simulation / model result**: one execution of a model, identified by `run_id`. Archived
  automatically by `model.execute()` through `model.archive_manager` (`DirectoryArchive`
  or `MlflowArchive`). Read back as a raw dict (`archive_manager.get_result`,
  `get_results_by_run_id`) then converted with `ModelResult.from_data`, or directly as
  `ModelResult` with `vimseo.api.load_simulation_results` (renamed `load_model_results`
  by SPEC-007 iteration 1).
- **ModelResult**: derives from `BaseResult`, holds scalars, vectors, curves and
  `plots` (curve sets with their `Plot`), so it could draw itself; but it defines no
  `_create_figures`, so `ModelResult.visualize()` returns no figure. The figures of a
  simulation are drawn by `IntegratedModel.plot_results`, which needs the model.
- **Tool run / tool result**: one execution of a tool, `tool_run_id`, archived
  automatically by `BaseTool` (SPEC-004/005). Read back with
  `open_tool_archive(...).get_tool_result(tool_run_id)`, `vimseo.api.load_tool_result(uri)`
  or `BaseTool.load_results(path)`; visualized with `result.visualize()` /
  `result.tabulate()` (SPEC-006) or the CLI `visualize_tool_result`.
- **Archive managers**: `model.archive_manager` for simulations; the object returned by
  `open_tool_archive` for tool results (named `tool_archive_manager`, SPEC-004 iteration
  1). Their query APIs differ: `search_tool_runs`/`find_tool_runs_of_simulation` for tool
  runs; `get_archived_results`, `get_result`, `get_results_by_run_id` for simulations, and
  the MLflow fluent API (`mlflow.search_runs`) in `plot_03` to search simulations.
- **Example gallery**: `docs/runnable_examples/<NN_topic>/` folders with a `README.md`
  are discovered by `docs/gallery_conf.py`; data management is split today between
  `02_integrated_models/plot_03_model_result_management.py` (model results, Directory
  then MLflow in one file, ~300 lines) and `13_tool_result_management/` (2 examples,
  ~200 lines each, Directory and MLflow).
- **Exploration UIs**: `dashboard_database_viewer`, `dashboard_mlflow`, `mlflow ui
  --backend-store-uri ...`, `visualize_tool_result --uri ...`.
- **JobBundle** (SPEC-009): sandbox explorer of a directory archive; ideas of one entry
  point from a location, a collection with verbs, "show what differs".

### New Concepts Required

- **Data management example folder**: one gallery folder gathering the 8 examples, ordered
  from the stripped-down roundtrip to the backend-specific details.
- **Roundtrip vocabulary**: four verbs used everywhere, *generate*, *save*, *load*,
  *visualize*, each mapped to one API entry per kind of result (model / tool), the same
  for both backends.
- **Symmetric loading entry points** (candidate): a model result and a tool result are
  loaded the same way, by identifier or URI, from the same archive settings, and
  visualized the same way (`result.visualize()`), without the model nor the tool.

### Key Business Rules

- The roundtrip must work without the object that produced the result: a tool result
  without its tool (REQ-RES-001), a model result without its model (to be made true for
  the figures).
- Saving is automatic for both kinds of results (archives enabled by default); the user
  only chooses *where* (`archive_manager`, `directory_archive_root`, SPEC-004).
- A backend change (Directory ↔ MLflow) must not change the user code of the roundtrip,
  only the `archive_manager` value.
- Examples must run repeatedly and in the doc build (`EXAMPLE_RUNS_DIR`, cleanup of their
  archives), and must not require the `mlflow` extra except the MLflow ones.

## Strategic Approach

### Solution Direction

- Two complementary tracks in one canvas:
  1. **Documentation**: a new gallery folder (e.g. `14_data_management`), whose first
     example is a usage-oriented roundtrip with a comparison table, followed by three
     small roundtrip examples and four backend × result-kind examples, reusing and
     splitting the content of `plot_03_model_result_management.py` and
     `13_tool_result_management/`.
  2. **API simplification**, limited to what makes the roundtrip read the same for the
     two kinds of results: model results gain figures (`ModelResult.visualize()`), and the
     public API offers the same verbs for model and tool results, in `vimseo.api`.
- The roundtrip table drives the API: if a cell of the table needs a different function
  per backend or a sentence of explanation, it is a simplification target.

### Key Design Decisions

- **Folder layout**: one new folder with 8 numbered examples vs. nested sub-folders. The
  gallery discovers one level only (`gallery_conf.py`) → one folder, files numbered
  `plot_01_roundtrip`, `plot_02..04` basic, `plot_05..08` detailed; the old examples are
  moved, not duplicated (`13_tool_result_management/` removed, `plot_03` of
  `02_integrated_models` moved).
- **What the "3 small examples" cover**: three axes are possible (save / load /
  visualize, or model / tool / both linked, or Directory / MLflow / CLI). → One per verb
  family across both result kinds: (a) save and find (where results go, how to list
  them), (b) load (by identifier, by URI, from a tool result to its model results),
  (c) visualize (Python, CLI, dashboards). This keeps each example short and
  backend-agnostic. To be confirmed by the reviewers.
- **ModelResult figures**: draw from `ModelResult.plots` in `_create_figures`, reusing the
  plotting already used by `IntegratedModel.plot_results`, vs. keeping figures on the
  model. → Implement `ModelResult._create_figures`: it gives the symmetric
  `result.visualize()` and removes the need for the model.
- **Public loading verbs**: keep `load_tool_result(uri)` and `load_model_results(run_ids)`
  (SPEC-007) and add the missing search entry for model results, vs. a single generic
  `load_result(uri)` dispatching on the kind. → Keep two explicit functions named after
  what they return, plus symmetric search functions; a generic dispatcher hides what is
  returned and complicates typing. A model result URI scheme (`run:{run_id}`) is a
  candidate for symmetry with `tool-run:`; left as a decision for the canvas.
- **JobBundle ideas**: adopt the *entry point from a location* (open an archive from its
  settings) and *export to Dataset/DataFrame* of a list of model results; postpone the
  verbs filter/diff/variations (they need a collection class, larger scope).
- **CLI**: keep `visualize_tool_result` but document one command per need in a table of
  the first example; consider a single `vimseo` entry point later (out of scope).

### Alternatives Considered

- Keep the examples where they are and only rewrite them: rejected, the reviewer asks for
  a dedicated folder and a progressive reading order.
- A facade class `ResultStore` wrapping both archives: rejected for now, it adds a third
  vocabulary next to the two archive managers; to revisit after the symmetric API.
- Expose `JobBundle` publicly: rejected (SPEC-009: untested, directory-only, mutating).

## Risk & Gap Analysis

### Requirement Ambiguities

- **Content of the 3 small examples**: the requirement does not say which axis; a
  proposal is made (save/find, load, visualize), to be validated.
- **"Simplification"**: the scope of API changes is open; the analysis limits it to
  symmetry (ModelResult figures, model results search/load) and naming; anything larger
  (facade, single CLI) is out of scope.
- **Fate of the existing examples**: moved vs. kept for links; the mkdocs nav and external
  links to `13_tool_result_management` must be updated.
- **Language and audience**: usage-oriented means no internal details (no run tree, no
  MLflow tag mapping) in the first four examples; those go to the four detailed ones.

### Edge Cases

- MLflow examples need the `mlflow` extra: the core-profile doc build must skip or
  guard them.
- The basic examples use one backend: they must state that the code is identical with
  the other one, and ideally be checked with both in a test.
- Repeated runs of the examples: archives must be cleaned at start (as today).
- A model result loaded from an archive written before `ModelResult.plots` existed has no
  plots: `visualize()` must return no figure without failing.

### Technical Risks

- **ModelResult figures**: `IntegratedModel.plot_results` may depend on model state (load
  case, scalar names); the shared plotting code must work from the `ModelResult` alone.
  Mitigation: reuse `superpose_curves` with the `CurveSet`/`Plot` stored in the result.
- **Doc build time**: 8 examples running simulations and MLflow; keep models analytical
  and samples small.
- **Breaking links**: moving examples changes the generated URLs.

### Acceptance Criteria Coverage

| AC# | Description | Addressable? | Gaps/Notes |
|-----|-------------|--------------|------------|
| 1 | Dedicated data management example folder | Yes | One gallery level only; numbered files |
| 2 | First example: stripped-down roundtrip with an API comparison table | Yes | Table: rows = verbs, columns = model/tool × Directory/MLflow |
| 3 | 3 small basic roundtrip examples | Partial | Axis to be validated (proposal: save/find, load, visualize) |
| 4 | 4 examples: model/tool × Directory/MLflow | Yes | Content moved from plot_03 and 13_tool_result_management |
| 5 | `load_tool_result` next to `get_tool_result`; `model_results` naming | Yes | Also in SPEC-007 iteration 1 docstrings |
| 6 | Simplify the technical roundtrip | Partial | Limited to symmetry: `ModelResult.visualize()`, model results search/load in `vimseo.api`, naming; facade/CLI unification out of scope |
