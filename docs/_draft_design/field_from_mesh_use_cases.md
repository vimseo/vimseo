<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# `Field.from_mesh` — use cases (draft notes)

Illustrative snippets, **not tested**. They assume the signature
`from_mesh(cls, mesh: Mesh, path: Path | str = "") -> Field`.

## 1. In-memory transformation before wrapping

A Tecplot file whose coordinate variables are not named `X`/`Y`/`Z`: the header is
patched in memory, then parsed.

```python
text = _rename_header_variables(Path(file_path).read_text(), variable_name_aliases)
mesh = read(StringIO(text), file_format=_FORMAT)      # never touches disk again
self.result.field = MeshField.from_mesh(mesh, file_path)
```

`Field.load(path)` cannot produce this mesh — it would re-read the unpatched file and
fail on `CoordinateX`. The alternative is to give `Field.load` `file_format` and
`variable_name_aliases` parameters, i.e. leak Tecplot concerns into `Field`.

## 2. One file, several fields

Multi-zone Tecplot or multi-block CGNS: one path, several meshes.

```python
def _split_zones(mesh: Mesh) -> Iterable[Mesh]:
    """Yield one single-block mesh per cell block."""
    for cell_block in mesh.cells:
        yield Mesh(
            points=mesh.points,
            cells=[cell_block],
            point_data=mesh.point_data,
        )


mesh = read(file_path, file_format=_FORMAT)
self.result.fields = [
    MeshField.from_mesh(zone, file_path) for zone in _split_zones(mesh)
]
```

`load(path)` has one return value, so this is unreachable through it. It also requires
a result class holding a list of fields rather than a single one.

## 3. Mesh with no file behind it

A mesh handed over in memory — from a running solver's Python API, from a coupling
step, or converted from pyvista / VTK objects.

```python
mesh = Mesh(
    points=solver.node_coordinates(),
    cells=[("triangle", solver.connectivity())],
    point_data={"pressure": solver.field("P"), "mach": solver.field("M")},
)
field = MeshField.from_mesh(mesh)   # path stays "" — nothing was ever written
```

Inventing a path here would put a false value in the provenance metadata.

## 4. Transient files — read the geometry once, not once per step

```python
with TimeSeriesReader(file_path) as reader:
    points, cells = reader.read_points_cells()
    fields = []
    for k in range(reader.num_steps):
        time, point_data, cell_data = reader.read_data(k)
        fields.append(
            MeshField.from_mesh(
                Mesh(points, cells, point_data=point_data, cell_data=cell_data),
                file_path,
            )
        )
```

Through `load`, each step reopens and re-parses the whole file, and the geometry is
duplicated N times.

## 5. Derived fields

Transform an existing field and rewrap it, keeping the source path as provenance.

```python
def restrict_to_cell_type(field: Field, cell_type: str) -> Field:
    """Return the field restricted to the cells of a given type."""
    mesh = Mesh(
        points=field.mesh_points,
        cells=[b for b in field.mesh_cells if b.type == cell_type],
        point_data=field.point_data,
    )
    return Field.from_mesh(mesh, field.path)


wall = restrict_to_cell_type(field, "quad")
```

The result is a genuine `Field`, usable by everything downstream, but was never a file.
Same shape for slicing, interpolation onto another mesh, or unit conversion.

## 6. Tests without fixture files

In-memory meshes make tests of `Field` and of everything downstream hermetic, and put
the expected values in the test rather than in a fixture file.

```python
@pytest.fixture
def unit_square_field() -> Field:
    """A two-triangle unit square with a linear pressure field."""
    return Field.from_mesh(
        Mesh(
            points=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            cells=[("triangle", [[0, 1, 2], [0, 2, 3]])],
            point_data={"pressure": [0.0, 1.0, 2.0, 1.0]},
        )
    )


def test_point_variable_names(unit_square_field):
    assert unit_square_field.point_variable_names == ["pressure"]
```
