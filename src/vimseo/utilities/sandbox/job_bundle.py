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

# from vimseo.utilities.tree_parser import tree_parser
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import shutil
from collections import UserList
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from gemseo.caches.hdf5_cache import HDF5Cache
from gemseo.datasets.dataset import Dataset

from vimseo.utilities.datasets import encode_vector

if TYPE_CHECKING:
    from collections.abc import Iterable

LOGGER = logging.getLogger(__name__)


class JobBundle(UserList):
    grouping_keys = ["metadata:model", "metadata:load_case"]

    def __init__(self, root_archive: Path | str | None = None) -> dict:
        super().__init__()
        if root_archive is not None:
            self.import_archive(root_archive)

    def build_cache(
        self,
        model_name: str,
        load_case_name: str,
        cache_file: Path | str = "tmp_archive_cache.hdf",
    ):
        msg = "This method is now deprecated => see new Model services"
        raise NotImplementedError(msg)

        """Create new cache based on the current job bundle.

        Implicitly deletes the old cache fiile with the same name to avoid possible
        deprecated values.
        """
        # TODO Sebastien review: this cache tolerence is important fow now: see issue
        #  #233. Layup is generaly defined as a list of integers by the user,
        #  but encoding/decoding gives float values. Layup showed this issue,
        #  but the problem is general.

        cache = HDF5Cache(hdf_file_path=cache_file, tolerance=0.00000001)
        if len(cache) > 0:
            # remove old cache (with possibly deprecated values) =>
            # warning it also removes the content of the file in memory
            cache.clear()
        for job in self:
            if (
                job["metadata"]["model"] == model_name
                and job["metadata"]["load_case"] == load_case_name
            ):
                inputs = {k: np.atleast_1d(v) for k, v in job["inputs"].items()}

                outputs = {k: np.atleast_1d(v) for k, v in job["outputs"].items()}
                jacobian = None
                cache[inputs] = (outputs, jacobian)

        if len(cache) == 0:
            msg = (
                f"No job matches model:{model_name} and load_case:{load_case_name} in "
                f"the bundle."
            )
            raise ValueError(msg)

        return cache

    def gets_variations(self, reference_input_key, delete_mono_groups=True):
        self._check_structure()

        # create a hash of the job inputs dict (except for the reference_input_key item)
        def get_hash(job):
            job_json = json.dumps(job, sort_keys=True)
            return hashlib.sha256(job_json.encode()).hexdigest()

        # map jobs ID to the hash of the same job inputs
        map_id_to_hash = {}
        for job in self:
            restrict = {
                k: v for k, v in job["inputs"].items() if k != reference_input_key
            }
            # print(job["ID"], get_hash(restrict))
            map_id_to_hash[job["ID"]] = get_hash(restrict)

        # revert the mapping : group the jobs by IDs by their hash key
        map_hash_to_ids = {}
        for id, hash in map_id_to_hash.items():
            if hash not in map_hash_to_ids:
                map_hash_to_ids[hash] = [id]
            else:
                map_hash_to_ids[hash].append(id)

        # print("\n\n", see3(map_hash_to_ids))

        # delete groups with only one job
        if delete_mono_groups:
            for hash in list(map_hash_to_ids.keys()):
                if len(map_hash_to_ids[hash]) < 2:
                    map_hash_to_ids.pop(hash)

        # List directly the job results instead of just their IDs
        map_hash_to_jobs = {h: [] for h in map_hash_to_ids}
        for hash, ids in map_hash_to_ids.items():
            for job in self:
                if job["ID"] in ids:
                    map_hash_to_jobs[hash].append(job.copy())

        # Differentiate the inputs between groups => what specific inputs
        # differentiate a group from another
        if len(map_hash_to_jobs) == 0:
            return {}
        job_ref = next(iter(map_hash_to_jobs.values()))[0]  # first job of first group
        differenciated_inputs_keys = []
        for hash in map_hash_to_jobs:  # for each group
            first_job_group = map_hash_to_jobs[hash][0]

            for k_ref, v_ref in job_ref["inputs"].items():
                if k_ref == reference_input_key:
                    # not interested in the reference_input_key
                    continue

                # search for inputs with diffrent values
                if k_ref in first_job_group["inputs"]:
                    if first_job_group["inputs"][k_ref] != v_ref:
                        differenciated_inputs_keys.append(k_ref)
        # save the differentiated keys in each job
        for jobs in map_hash_to_jobs.values():  # for each group
            for job in jobs:
                job["diff_inputs"] = {
                    k: job["inputs"][k] for k in differenciated_inputs_keys
                }

        return map_hash_to_jobs

    def remove_duplicate_jobs(self, delete_dirs=False):
        """Remove the duplicated job_results in the self list, based inputs values."""

        id_to_remove = []
        for i, job_i in enumerate(self):
            for _j, job_j in enumerate(self[(i + 1) :]):
                if job_i["inputs"] == job_j["inputs"]:
                    id_to_remove.append(job_j["ID"])
        id_to_remove = sorted(set(id_to_remove))  # order and remove duplicates

        # remove duplicate jobs
        for job in reversed(self):
            if job["ID"] in id_to_remove:
                # erase the corresponding archive dir
                if delete_dirs:
                    d = job["dir_archive_job"]
                    if d.exists():
                        print(f"Removing duplicate job_results directory: {d}")
                        shutil.rmtree(str(d))

                # remove this job results from self list
                self.remove(job)

    def _check_structure(self):
        """Checks whether the current data structure has the expected format."""

        if len(self) == 0:
            msg = "Empty job bundle"
            raise ValueError(msg)

        for i, job in enumerate(self):
            if not isinstance(job, dict):
                msg = (
                    f"Job tree is only expected to contain dict, but item {i} "
                    f"contains {type(job)} : {job} "
                )
                raise ValueError(msg)
            for k in ["inputs", "outputs", "metadata"]:
                if k not in job:
                    msg = (
                        f"Every job of the tree is expected to have an attribute {k}, "
                        f"but item {i} does not: {job} "
                    )
                    raise ValueError(msg)

    def import_archive(self, root_archive: Path | str) -> dict:

        if not Path(root_archive).is_dir():
            msg = "root_archive to be imported is not a directory: "
            raise ValueError(msg, root_archive)

        target_file_name = "results.json"

        target_files = []
        for root, _, files in os.walk(root_archive):
            if target_file_name in files:
                target_files.append(Path(root) / target_file_name)

        results = [{} for f in target_files]
        base_index = max([job["ID"] for job in self] + [0]) + 1
        for i, file in enumerate(target_files):
            # import json results data
            try:
                json_content = json.load(Path(file).open())
            except Exception as e:
                None
                msg = f"{e!s} \nError encountered while parsing file {file}"
                raise Exception(msg)

            # wrapp job results in the #i item of the bundle
            results[i] = {
                **json_content,
                "dir_archive_job": Path(file).parent,
                "ID": base_index + i,
            }

        # for r in results:
        #     if "layup" in r["inputs"].keys():
        #         r["inputs"]["layup"] = encode_vector(r["inputs"]["layup"])

        # cast list inputs (such as layup) into tuple, so has to be hashable
        for r in results:
            for k in r["inputs"]:
                if np.atleast_1d(r["inputs"][k]).size > 1:
                    r["inputs"][k] = tuple(r["inputs"][k])

        self.extend(results)

        self._check_structure()

    @staticmethod
    def _split_namespace(key):
        split = key.split(":")
        if len(split) != 2:
            msg = (
                f"keys are expected to be formatted like 'inputs:layup' but not: {key}"
            )
            raise ValueError(msg)

        k_group, k_individual = split
        return k_group, k_individual

    def filter(self, filters, keep=True):

        for i in reversed(range(len(self))):
            for k, v in filters.items():
                k_group, k_individual = self._split_namespace(k)
                if (self[i][k_group][k_individual] == v) is not keep:
                    self.pop(i)
                    break

    def report(
        self, by_group=False, differentiate_inputs=False, collapse_vectors=True
    ) -> str:
        # TODO remake solution with job["diff_inputs"] to visualize
        #  that data with the rest (notably the ID)

        """Prints listed jobs, according to group options."""

        # TODO major correct : the collapse_vector should only influence the
        #  plotting, and not destroy the actual values of the self list => work with
        #  temporary hard copy

        # def identity(*args, **kwargs):
        #     return (*args, kwargs)

        if len(self) == 0:
            msg = "Empty job bundle"
            raise ValueError(msg)

        def identity(*args, **kwargs):
            """Identity function: returns what is fed to it."""
            # TODO Sebastien review, how to do it simplier ?
            #   def identity(*args, **kwargs):
            #         #     return (*args, kwargs)
            #  does not work properly
            if args and kwargs:
                return (*args,), kwargs
            if args:
                return args[0] if len(args) == 1 else args
            if kwargs:
                return kwargs
            return None

        # Whether do differentiate the jobs to print
        diff = self._differentiate_list if differentiate_inputs else identity

        if by_group is False:
            print(self.report(diff(self), collapse_vectors=collapse_vectors))
        else:
            group_matrix = {}
            for group_name in self.grouping_keys:
                # list group items but remove duplicates and sort alphabetically
                k_group, k_individual = self._split_namespace(group_name)

                local_vals = [job[k_group][k_individual] for job in self]
                group_matrix[group_name] = sorted(set(local_vals.copy()))

            def dive_report(
                remaining_group_keys: list[str],
                remaining_group_vals: list[str],
                passed_groups: dict,
                indent=0,
            ):
                recursive_call = dive_report

                if len(remaining_group_keys) == 0:
                    # leaf => report corresponding jobs

                    # list the jobs abiding to passed_groups
                    jobs = []
                    for job in self:
                        job_is_ok = True
                        for k, v in passed_groups.items():
                            k_group, k_individual = self._split_namespace(k)
                            if job[k_group][k_individual] != v:
                                job_is_ok = False
                                break
                        if job_is_ok:
                            jobs.append(job)

                    # report the listed jobs
                    if len(jobs) > 0:
                        return see3(
                            diff(jobs),
                            indent=indent + 4,
                            collapse_vectors=collapse_vectors,
                        )
                    return None
                first_key = remaining_group_keys[0]
                first_vals = remaining_group_vals[0]
                cat = ""
                for group_val in first_vals:
                    new_passed_groups = passed_groups.copy()
                    new_passed_groups.update({first_key: group_val})

                    sub_tree_message = recursive_call(
                        remaining_group_keys[1:],
                        remaining_group_vals[1:],
                        new_passed_groups,
                        indent + 4,
                    )

                    if sub_tree_message is not None:
                        cat += " " * indent + f"{first_key} = {group_val}\n"
                        cat += sub_tree_message
                return cat

            print(
                dive_report(
                    list(group_matrix.keys()), list(group_matrix.values()), {}, 0
                )
            )

    def _form_groups(self):
        for k in self.grouping_keys:
            k_group, k_individual = self._split_namespace(k)
            if k_individual not in self[0][k_group]:
                msg = f"{k_individual} is not part of {k_group} keys"
                raise NotImplementedError(msg)

        for job in self:
            job["group"] = {
                k: job[self._split_namespace(k)[0]][self._split_namespace(k)[1]]
                for k in self.grouping_keys
            }

    @staticmethod
    def _differentiate_list(job_results: list[dict]) -> list:

        # checks if jobs can be differentiated
        if len(job_results) > 1:
            for i_job in range(1, len(job_results)):
                if (
                    job_results[i_job]["inputs"].keys()
                    != job_results[0]["inputs"].keys()
                ):
                    msg = (
                        "Jobs do not have consistent inputs keys to differenciate, "
                        "which is not supported. You probably tried to diff some jobs "
                        "with different model or load_case."
                    )
                    raise NotImplementedError(
                        msg,
                        i_job,
                        job_results[0]["inputs"].keys()
                        - job_results[i_job]["inputs"].keys(),
                    )

        keys_to_keep = []
        for k in job_results[0]["inputs"]:
            vals = [j["inputs"][k] for j in job_results]
            # print(k, vals)
            if len(set(vals)) > 1:
                keys_to_keep.append(k)

        return [
            {k: v for k, v in j["inputs"].items() if k in keys_to_keep}
            for j in job_results
        ]

    def to_csv(self, csv_name: str, curves_names: Iterable(str) = ()):

        def _get_output_curves_names(job):
            return [k for k, v in job["outputs"].items() if np.size(v) > 5]

        def _list_outputs_curves_names(curve_names, job):
            if len(curves_names) == 0:
                return _get_output_curves_names(job)
            return curves_names

        def copy(x):
            if "copy" in dir(x):
                return x.copy()
            return x

        inputs_differentiated = self._differentiate_list(self)
        # print("roro \n", see3(inputs_differentiated))

        headers = []
        columns = []

        for i, j in enumerate(self):
            # group j

            # side notes of group j
            headers.append(
                str({"diff_inputs": inputs_differentiated[i]})
            )  # main header of group j = differentiated inputs
            columns.append([
                {k: copy(v)} for k, v in j.items()
            ])  # side notes of group j

            # collapse output curves in the last side note
            for c in columns[-1]:
                c = c.copy()
                if "outputs" in c:
                    cc = c["outputs"]
                    for k_out in cc:
                        if np.size(cc[k_out]) > 1:
                            cc[k_out] = "collapsed"

            # useful headers and columns of the group j
            for out_name in _list_outputs_curves_names(curves_names, j):
                headers.append(out_name)
                columns.append(j["outputs"][out_name])

            headers.append("")
            columns.append(["", ""])

        # write csv
        f = Path(csv_name).open("w")
        f.writelines(h + " ; " for h in headers)
        f.write("\n")
        max_len = max(len(col) for col in columns)
        for i in range(max_len):
            for col in columns:
                if i < len(col):
                    text = str(col[i])
                    f.write(text)

                f.write(";")
            f.write("\n")
        f.close()

    def to_dataset(self) -> Dataset:
        """Returns IO dataset (GEMSEO like) from the current bundle results."""

        # consider a deep copy of self to avoid muting the original data in the
        # process, especially the layup input that needs to be encoded
        jobs = copy.deepcopy(self)

        # checks if bundle is empty
        if len(jobs) == 0:
            msg = "Empty list"
            raise ValueError(msg)
        first_job = jobs[0]
        # checks mono model/load_case in the bundle
        for job in jobs:
            if (
                jobs[0]["metadata"]["model"] != job["metadata"]["model"]
                or jobs[0]["metadata"]["load_case"] != job["metadata"]["load_case"]
            ):
                msg = (
                    "The list of jobs to cast into dataset contains different "
                    "model or load_case."
                )
                raise ValueError(msg)

        # checks rectangularity of data
        for group in ["inputs", "outputs"]:
            for job in jobs:
                if first_job[group].keys() != job[group].keys():
                    msg = (
                        f"Data not rectangular: Inconsistent keys between jobs, "
                        f"please check {group} : "
                        f"{set(first_job[group].keys()) ^ set(job[group].keys())}  , "
                        f"for job ID {job['ID']}"
                    )
                    raise ValueError(msg)
            for k in first_job[group]:
                for job in jobs:
                    if np.size(first_job[group][k]) != np.size(job[group][k]):
                        msg = (
                            f"Data not rectangular: job ID {job['ID']} has {group}:"
                            f"{k} of diffrent size than first job {first_job['ID']}  "
                        )
                        raise ValueError(msg)
        # Checks non-scalar inputs
        for j in jobs:
            # encode layup as string
            if "layup" in j["inputs"]:
                j["inputs"]["layup"] = encode_vector(np.array(j["inputs"]["layup"]))
            # checks if other unexpected non-scalar input
            for k, v in j["inputs"].items():
                if np.size(v) > 1:
                    msg = (
                        f"Non scalar input of job ID {job['ID']} => not supported for "
                        f"dataset: {k}:{v}"
                    )
                    raise ValueError(msg)

        # prepare dataset headers
        map_key_to_group = {}
        map_key_to_size = {}
        for group in ["inputs", "outputs"]:
            for k, v in first_job[group].items():
                map_key_to_group.update({k: group})
                map_key_to_size.update({k: np.size(v)})

        variable_names = list(first_job["inputs"].keys()) + list(
            first_job["outputs"].keys()
        )

        # data formatting for dataset creation
        data = []
        for j in jobs:
            inputs = list(j["inputs"].values())
            a = list(j["outputs"].values())
            b = []
            for v in a:
                if isinstance(v, list):
                    for v_ in v:
                        b.append(v_)
                else:
                    b.append(v)
            data.append(inputs + b)

        return Dataset.from_array(
            data=np.vstack(data),
            variable_names=variable_names,
            variable_names_to_group_names=map_key_to_group,
            variable_names_to_n_components=map_key_to_size,
        )


def see3(input: dict, indent=0, collapse_vectors=False) -> str:
    """Prints encapsulated dict and list into a readable format."""

    recursive = see3

    toggle = False

    if isinstance(input, dict):
        print(" " * indent, "gate dico", list(input.keys())) if toggle else None

        cat = ""

        for k, v in input.items():
            if k in ["inputs", "outputs", "metadata"]:
                if collapse_vectors:
                    # collapse the output vectors for lisibility
                    if k == "outputs":
                        for kk, vv in v.items():
                            if isinstance(vv, list) and len(vv) > 1:
                                v[kk] = ["collapsed"]

                cat += f"{' ' * indent}* {k} = {v}\n"
            elif isinstance(v, (list, dict)):
                cat += f"{' ' * indent}* {k} ="
                cat += "\n" + recursive(v, indent + 4, collapse_vectors)  # +"\n"
            else:
                cat += f"{' ' * indent}* {k} ="
                cat += f" {v}\n"
        return cat

    if isinstance(input, list):
        print(" " * indent, "gate list ", len(input)) if toggle else None

        cat = ""
        for i in range(len(input)):
            info = (
                f"  ID #{input[i]['ID']}"
                if isinstance(input[i], dict) and "ID" in input[i]
                else "   yoyo"
            )
            cat += " " * (indent + 4) + f"item {i}/{len(input)}" + info
            cat += "\n"
            cat += recursive(input[i], indent + 8, collapse_vectors) + "\n"
        return cat
    print(" " * indent, "gate else: ", type(input), input) if toggle else None
    return " " * (indent + 4) + str(input)  # +"\n"
