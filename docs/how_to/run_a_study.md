<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# Set-up a study {#run_study}

## Case of multiple layups

When running a study involving simulations of several layups, one
current limitation is that VIMSEO cannot process the
cache file if these layups have different lengths.
The simulations are correctly stored in the cache but trying
to convert the cache to a dataset or calling the executable `cache_viewer`
(see [handling_failed_simulations](#handling_failed_simulations)) to
visualize the cache entries will fail.

To overcome this issue, one approach is to prefix the cache file name by
the layup, which segregates the caches by layups. Thus, at model
instanciation, specify the `cache_file_path` like this:

```
from vimseo.api import create_model
from vimseo.utilities.database import encode

model_name = "OpfmCube"
load_case = "PST"
model = create_model(
    model_name, load_case,
    cache_file_path=f"layup{encode(layup)}_{model_name}_{load_case}_cache.hdf"
)
```

In addition, since the layup strongly controls the physics of the
laminate, it may be interesting to separate the tool results and the
individual simulations per layup. As a result, you may create the mode
like this:

```
from vimseo.api import create_model
from vimseo.utilities.database import encode

model_name = "OpfmCube"
load_case = "PST"
model = create_model(
    model_name, load_case,
    cache_file_path=f"layup{encode(layup)}_{model_name}_{load_case}_cache.hdf",
    root_directory=f"layup{layup}_{model_name}_{laod_case}_runs",
)
```

And create the tool like this:

```
from vimseo.tools.sensitivity.sensitivity import SensitivityTool

tool = SensitivityTool(root_directory=f"layup{layup}_{model_name}_{load_case}")
```

# Running simulations

## CALMIP

!!! note

    The generic project `a_project` used as example in the documentation
    should be replaced by `vimseo`, and `a_plugin` by the considered
    VIMSEO plugin (e.g. `vims_composites`).

VIMSEO is first installed on CALMIP.

!!! note

    The below procedure explains a user-mode installation, which means that
    VIMSEO sources are frozen in the environment.
    Modification of the sources do not modify the environment unless you
    re-install. For developers, you can also install VIMSEO in
    [developer-mode](http://docuserguides.ipf7135.irt-aese.local/user_guide/developer)

First load a Python environment (provided by conda on CALMIP), with a Python version
compatible with VIMSEO:

```
module load python/3.11.3
```

The easiest way is to install with pip:
[Create an empty python environment and activate](http://docuserguides.ipf7135.irt-aese.local/user_guide/installation/#installation)
and
[install](http://docuserguides.ipf7135.irt-aese.local/user_guide/installation/#install-with-pip).

If you work in a VIMSEO plugin, you also need to
[install](http://docuserguides.ipf7135.irt-aese.local/user_guide/installation/#install-a-plugin)
it.

!!! warning

    For the moment, the subroutine compilation does not work on CALMIP. So
    you can skip the subroutine installation `pip install src/extensions`.
    It means that the UnitCell models will not work. Since they are fast,
    they can be easily run on another machine.

!!! note

    Running `module load python/3.11.3` is only necessary at the generation
    of VIMSEO environment. Then, a `python` is available in
    this environment, so activating it is sufficient to have `python`. Once
    the environment is installed, to run simulations, we recommend the
    following procedure:

    - deactivate the `conda` base env which is automatically activated:
      `conda deactivate`
    - do not run `module load python/3.11.3` to avoid conflicts with
      VIMSEO environment
    - [activate](http://docuserguides.ipf7135.irt-aese.local/user_guide/installation.html#activate-the-environment)
      VIMSEO environment

Then, load the Abaqus module, necessary to execute Abaqus CAE in
interactive mode (used in the model pre and post processors):

```
module load abaqus/2022
```

Note that by default, Abaqus points to licence server
`27000@ica-abaqus.insa-toulouse.fr`. To use IRT licence server, you can
copy-paste the below instruction in a file `abaqus_v6.env` placed in
your home:

```
license_server_type=FLEXNET
abaquslm_license_file="27001@license-abaqus.pf.irt-saintexupery.com"
academic=RESEARCH
```

On CALMIP, it is recommended to store job outputs on `/tmpdir`, so you
may work in this directory, typically `/tmpdir/${USER}/my_wkdir`.

On a HPC cluster, you need to submit jobs through a job scheduler. So,
the run-processor of the wrapper must use a job executor which will
execute Abaqus through the job scheduler of the cluster. To do so, you
can override the configuration by placing a config file in your working
directory. Copy the below instruction in a file whose name ends with
`.config` in your working directory:

```
{
"N_CPUS": "",
"JOB_EXECUTOR": "SlurmAbaqus",
"CMD_ABAQUS_CAE": "abq2022hf1 cae noGUI={{abaqus_script}}",
"CMD_ABAQUS_RUN": "",
"LOGGER_MODE": "info",
"TEST_LOGGER_MODE": "info",
"ROOT_DIRECTORY": "",
"WORKING_DIRECTORY": "",
"VIMS_TEST_DIR": "/tmp/tests",
"CMD_ABAQUS_CAE_POST": ""
}
```

The pre and post processors always use an interactive job executor. The
command executed by these two processors are the above `CMD_ABAQUS_CAE`.
For a job executor of type `BaseJobScheduler`, as it is the case for the
`SlurmAbaqus` job executor, the Abaqus command executed through the job
scheduler is defined by the class attribute `_COMMAND_TEMPLATE` of the
job executor class. It is tested for Abaqus jobs submitted through the
Slurm job scheduler available on CALMIP, and in principle should not be
modified. You can still override this default command by specifying a
non-empty command in the configuration variable `CMD_ABAQUS_RUN`.

You can test that VIMSEO can submit a job by executing
the below script (to be copy-pasted in a `.py` file):

```
from vimseo.api import create_model
from vimseo.api import create_model, activate_logger, LOGGER_LEVELS

activate_logger(level=LOGGER_LEVELS["info"])

model = create_model("OpfmPlate", "PST", check_subprocess=True, directory_naming_method="NUMBERED")
model.cache = None
model.set_n_cpus(12)
print(model._run_processor.n_cpus)
model.execute()
print(model.get_output_data())
```

Another key point is to avoid that your VIMSEO Python
process being killed when your connexion to the cluster closes. There
are two possibilities:

- run you Python command in `nohup`:
  ```
  nohup python my_vims_script.py 2>&1 | tee out.txt &
  ```

- use ``tmux``, a terminal emulator.
  A command launched in ``tmux`` will persist after the connexion closes:

  ```
  tmux
  python my_vims_script.py 2>&1 | tee out.txt
  ```

  To reattach to the tmux session, first list the available sessions with ``tmux ls``,
  and attach to the desired session with ``tmux attach-session -t i`` where ``i``
  is the i-th session.

### Handling failed simulation {#handling_failed_simulations}

VIMSEO Abaqus wrapper allows to be tolerant to some
errors occurring during a model execution. The tolerance to error can be
controlled with argument `check_subprocess` at model creation:

- setting `check_subprocess` to `True` should normally raise a
  `CalledSubprocessError` error either if one of the subprocess of the
  pre, run and post processors fails, or if the outputs of the
  run-processor are not as expected by method
  `~.check_job_completion`{.interpreted-text role="meth"}. If the model is
  running by a scenario, the scenario should also fail. The failed model
  simulation is not stored in the model cache. So after debugging, if the
  same scenario is run again, the model should be fully re-executed.

- setting `check_subprocess` to `False` (default behaviour) makes the
  model more tolerant to errors. If one of the subprocess of the pre, run
  and post processors fails, or if the outputs of the run-processor are
  not as expected, `NaN` values are set to model outputs, the error code
  in the model output is set to one, and the model execution terminates
  without error. As a result, this simulation is stored in the cache. This
  may cause a problem when, after debugging, the user wants to re-execute
  the model (or the scenario executing the model), because the cache will
  be activated and will return the `NaN` outputs previously obtained. To
  enable full re-execution of the model, the cache entry corresponding to
  these inputs must be deleted from the cache.

To help the user manage the cache (which can be seen here as a database
of model executions), two executables are accessible from a terminal
where the environment in which VIMSEO is installed is
activated:

- `cache_viewer`. You may enter `cache_viewer -h` to get some
  help. It allows to visualize the cache content as a dataset, with some
  options to filter some entries.

- `cache_delete_entry`. You may enter
  `cache_delete_entry -h` to get some help. It allows to delete an entry,
  typically one having an error code to one and that you want to fully
  re-execute.

!!! warning

    At the moment, there is an assumption that the cache entry index and the
    index of the dataset row shown with `cache_viewer` are the same. This
    may be wrong if you remove another entry than the last ones. The problem
    is that you may try to delete non-existing entries when you will view
    the cache again, after having deleted entries. If `cache_delete_entry`
    bugs, you can also use the `hdfview` tool, which is a standard tool for
    `hdf5` file manipulation. `hdfview` allows to delete hdf groups and thus
    can be used in replacement of `cache_delete_entry`.

## Run Abaqus models using a Docker container

A Docker container where Abaqus is installed is available. In a terminal,
run:

```
docker login https://registry-elliot-fire.pf.irt-saintexupery.com/
```

with :

```
user: firetracker
password: 31onFire34
```

Then, pull the images:

```
docker pull registry-elliot-fire.pf.irt-saintexupery.com/abaqus:2022-int
docker pull registry-elliot-fire.pf.irt-saintexupery.com/abaqus:2022-ext
```

!!! warning

    The image is heavy, make sure you have at least 25 Go available on your disk.

The `2022-int` tag is configured to use the internal URL to licence
server, and the `2022-ext` is configured to use the external URL to
licence server.

### Run Abaqus model on Linux

Copy this code block in your `.bashrc` file:

```
export ABAQUS_DOCKER_IMAGE_NAME="registry-elliot-fire.pf.irt-saintexupery.com/abaqus:2022-int"
function abq_2022_docker() {
    local CURRENT_DIR
    CURRENT_DIR=$(pwd)
    docker run --rm -v "${CURRENT_DIR}":"${CURRENT_DIR}" --workdir "${CURRENT_DIR}" -it ${ABAQUS_DOCKER_IMAGE_NAME} abq2022 interactive $*
}
```

Then, source it:

```
source ~/.bashrc
```

You should now be able to call Abaqus in a shell by using the defined
function (`abq_2022_docker` here, it can be renamed as you wish).

### Run Abaqus model on Windows

You need to install `Docker Desktop`, which can be found on IRT
application portal (type ``Software center`` in the Windows search bar).

!!! note

    `Docker Desktop` requires the `Windows System Linux` (WSL).
    To install it, issue a ticket to the IT.
    You must also add your user to the Docker group,
    which should also be done through a ticket to the IT.

In Docker Desktop, in the Images tab, search for the above image and run
it. Make sure that the engine is running.

Then, copy the below code snippet in a `.bat` file (for example
`abq_2022_docker.bat`):

```
@echo off
setlocal
set ABAQUS_DOCKER_IMAGE_NAME=registry-vimseo.pf.irt-saintexupery.com/abaqus:2022-int
set CURRENT_DIR=%cd%
docker run --rm -v "%CURRENT_DIR%":"/workdir" --workdir "/workdir" %ABAQUS_DOCKER_IMAGE_NAME% abq2022 %*
REM setx PATH "%PATH%;C:\Scripts"
REM setx PATHEXT %PATHEXT%;.
endlocal
```

#### First interactive test

Before running VIMSEO Abaqus models, an interactive test in a terminal can
be done (git CMD or Powershell):

- Add the above `.bat` file to the `PATH` (in Windows menu, select
  `Modify environment variable for your account` and add the directory
  containing the `.bat` file to the `PATH` variable),

- modify the `.bat` file to add the `-it` option to `docker run`:
  ```
  docker run --rm -v "%CURRENT_DIR%":"/workdir" --workdir "/workdir" -it %ABAQUS_DOCKER_IMAGE_NAME% abq2022 %*
  ```

Then move to an existing VIMSEO job directory where an Abaqus was run, and
run the Abaqus command line as specified by VIMSEO Abaqus wrapper. For
instance, to run the pre-processing and run-processing for a model with
subroutines:

```
abq_2022_docker cae noGUI={{abaqus_script}}
abq_2022_docker interactive job={{job_name}} cpus={{n_cpus}} user=index_subroutines.f
```

#### VIMSEO model execution

To run a VIMSEO Abaqus model on Windows, use the following VIMSEO configuration:

```
"CMD_ABAQUS_CAE": "C:/Users/Public/docker_abaqus/abq_2022_docker.bat cae noGUI={{abaqus_script}}",
"CMD_ABAQUS_RUN": "C:/Users/Public/docker_abaqus/abq_2022_docker.bat job={{job_name}} cpus={{n_cpus}}{% if subroutine_names|length > 0 %} user={{subroutine_names[0]}}{% endif %} {% if is_implicit == False %}double=both {% endif %}inter",
```

(The path to the `.bat` is an example, but the idea is to use linux-like
path (`/`)).
Also, make sure that the `-it` option in the `docker run`
command of the `.bat` file is removed.
