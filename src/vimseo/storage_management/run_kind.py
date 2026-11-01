# Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""The kinds and the statuses of the runs of an archive.

A study holds the simulations and the analysis node runs. In an MLflow archive, they are runs of
the experiment of the study, told apart by the tags defined here. The statuses are the
same for the simulations and the analysis node runs, in both archives.

This module imports nothing from MLflow, so that it is available without the ``mlflow``
extra.
"""

from __future__ import annotations

KIND_TAG = "vimseo.kind"
"""The tag of an MLflow run giving the kind of the run."""

SIMULATION = "simulation"
"""The kind of the run of a simulation."""

ANALYSIS_NODE_RUN = "analysis_node_run"
"""The kind of the run of an analysis node."""

MODEL_TAG = "vimseo.model"
"""The tag of the run of a simulation giving the name of its model."""

LOAD_CASE_TAG = "vimseo.load_case"
"""The tag of the run of a simulation giving the name of its load case."""

RUN_ID_TAG = "vimseo.run_id"
"""The tag of the run of a simulation giving its ``run_id``."""

STUDY_TAG = "vimseo.study_name"
"""The tag of a run giving its study."""

RUNNING = "RUNNING"
"""The status of a run which has started and has not ended, or was interrupted."""

FINISHED = "FINISHED"
"""The status of a run whose result was published."""

FAILED = "FAILED"
"""The status of a run which raised."""
