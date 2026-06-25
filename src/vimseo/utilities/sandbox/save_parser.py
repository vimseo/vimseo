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

from __future__ import annotations

# def get_archive_jobs(root_archive: Path | str) -> dict:
#     """Parse an archive dir to return a list of all the job results found."""
#     target_file_name = "results.json"
#
#     target_files = []
#     for root, _, files in os.walk(root_archive):
#         if target_file_name in files:
#             target_files.append(Path(root) / target_file_name)
#
#     results = [json.load(open(f)) for f in target_files]
#
#     return results


# def classify(input: dict) -> dict:
#
#     models = list({job["metadata"]["model"] for job in input})
#     load_cases = list({job["metadata"]["load_case"] for job in input})
#
#     collect_model = {}  # {m:[] for m in models}
#     for model in models:
#         collect_model[model] = {}
#
#         for load_case in load_cases:
#             collect_load_case = []
#             for job in input:
#                 if (
#                     job["metadata"]["model"] == model
#                     and job["metadata"]["load_case"] == load_case
#                 ):
#                     collect_load_case.append(job)
#
#             # # filter empty load_case collection
#             # collect_load_case = {k:v for k,v in collect_load_case.items() if len(
#             v)>0}
#
#             # capitalize collection of load_cases for the current model
#             if len(collect_load_case) > 0:
#                 collect_model[model].update(
#                     {load_case: differentiate(collect_load_case)}
#                 )

#
#     return collect_model
#
#
# def differentiate(job_results: list) -> list:

#     job_results = job_results.copy()
#
#     # all_keys = []
#     # for job in job_results:
#     #     all_keys += job["inputs"]
#     # all_keys = list(set(all_keys))
#
#     keys_to_keep = []
#     for k in job_results[0]["inputs"].keys():
#         vals = [j["inputs"][k] for j in job_results]
#         if len(set(vals)) > 1:
#             keys_to_keep.append(k)
#
#     inputs_differentiated = [
#         {k: v for k, v in j["inputs"].items() if k in keys_to_keep} for j in
#         job_results
#     ]
#     # for job in job_results:
#     #     job.pop("outputs")
#     #     job["metadata"] = {k:v for k,v in job["metadata"].items() if k in ["model",
#     #     "load_case"]}
#     #
#     #     for k in keys_to_remove:
#     #         job["inputs"].pop(k)
#
#     return inputs_differentiated


def see1(input: dict, indent=0):

    recursive = see1

    if isinstance(input, dict):
        # print("check dico")
        if "inputs" in input:
            print(" " * indent + str(input))
        else:
            for k, v in input.items():
                if isinstance(v, dict):
                    if "inputs" in v:
                        print(" " * indent + str(v))
                    else:
                        print(" " * indent + "*" + k)
                        recursive(v, indent + 4)
                elif isinstance(v, list):
                    # TODO Factorise with above
                    print(" " * indent + "*" + k)
                    recursive(v, indent + 4)
                else:
                    print(" " * indent + "*" + k + "=" + str(v))

    elif isinstance(input, list):
        for i in range(len(input)):
            print(
                " " * (indent + 4),
                f"item {i}/{len(input)}",
            )
            recursive(input[i], indent + 8)
    else:
        print(" " * (indent + 4), input)


def see2(input: dict, indent=0) -> str:

    recursive = see2
    toggle = False

    if isinstance(input, dict):
        print(" " * indent, "gate A - dico ", list(input.keys())) if toggle else None
        if "inputs" in input:
            (
                print(" " * indent, "gate 1 - dico[input] => direct str")
                if toggle
                else None
            )
            return " " * indent + str(input) + "\n"
        (
            print(" " * indent, "gate 2 - dico generic ", list(input.keys()))
            if toggle
            else None
        )
        for k, v in input.items():
            cat = ""
            if isinstance(v, dict):
                (
                    print(
                        "_" * 4,
                        " " * indent,
                        "gate 2.1   content is dict ",
                        list(input.keys()),
                    )
                    if toggle
                    else None
                )
                if "inputs" in v:
                    (
                        print("_" * 8, " " * indent, "gate 2.1.1 - str direct")
                        if toggle
                        else None
                    )
                    cat += " " * indent + str(v) + "\n"
                else:
                    (
                        print("_" * 8, " " * indent, "gate 2.1.2  - recursive on ", k)
                        if toggle
                        else None
                    )
                    cat += " " * indent + "*" + k + recursive(v, indent + 4) + "\n"
            elif isinstance(v, list):
                (
                    print("_" * 4, " " * indent, "gate 2.2   content is list ", len(v))
                    if toggle
                    else None
                )
                cat += " " * indent + "*" + k + recursive(v, indent + 4) + "\n"
            else:
                (
                    print(
                        "_" * 4,
                        " " * indent,
                        "gate 2.3    content is else: ",
                        type(v),
                        v,
                    )
                    if toggle
                    else None
                )
                cat += " " * indent + "*" + k + "=" + str(v) + "\n"

        return cat

    if isinstance(input, list):
        print(" " * indent, "gate B _ list") if toggle else None
        cat = ""
        for i in range(len(input)):
            cat += (
                " " * (indent + 4)
                + f"item {i}/{len(input)}"
                + recursive(input[i], indent + 8)
                + "\n"
            )
        return cat
    print(" " * indent, "gate C else: ", type(input)) if toggle else None
    return " " * (indent + 4) + recursive(input) + "\n"
