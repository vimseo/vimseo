<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Changelog fragments

Each pull request that changes the public API of vimseo (adds, removes, renames, or
changes the signature of a class, method, function, or attribute of `src/vimseo/`
that has no leading `_`) must add one file here, describing the change for the
changelog. At release time, `towncrier build --version X.Y.Z` compiles all fragments
into `CHANGELOG.md` and deletes them.

## Naming

`+<short-slug>.<type>.md`, for example `+base-analysis-node-protected-api.changed.md`.

- The `+` prefix marks an "orphan" fragment, not tied to a GitHub issue/PR number
  (a fragment is written in the same PR that makes the change, before the PR number
  is known). It is not rendered as a link in the generated changelog.
- `<type>` is one of: `added`, `changed`, `deprecated`, `removed`, `fixed`, `security`
  (see the legend at the top of `CHANGELOG.md`).
- **A file named only by its type (`changed.md`) is silently dropped by towncrier.**
  Always include the `+<slug>` part.

## Content

Plain Markdown, one or a few sentences, written as a changelog entry (what changed,
for whom, and how to adapt if needed) -- not a commit message or an implementation
note.

## Preview

```bash
towncrier build --draft --version <next-version>
```

This prints the compiled changelog section without writing or deleting anything.
