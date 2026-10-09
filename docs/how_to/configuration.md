<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

## How to configure VIMSEO with a `.env` file

**VIMSEO**'s global configuration can be overridden with environment variables, or
with a `.env` file placed in the directory from which **VIMSEO** is run. Every
setting is exposed as an environment variable prefixed with `VIMSEO_`; nested
settings are reached with a double underscore (`__`) as separator. Process
environment variables take precedence over the `.env` file.

Here is a full example, covering every available setting:

```dotenv
--8<-- "docs/user_guide/vimseo.env"
```

**Parameters:**

| Environment variable | Description | Default |
|---|---|---|
| `VIMSEO_LOGGING` | Logging verbosity (e.g. `"info"`, `"debug"`) | `"info"` |
| `VIMSEO_SOLVERS__<name>__JOB_EXECUTOR` | The job executor used by the solver `<name>` (must be a registered job executor class, e.g. `"InteractiveAbaqus"`) | `None` |
| `VIMSEO_SOLVERS__<name>__COMMAND_RUN` | The command used by the solver `<name>` to run a job | `""` |
| `VIMSEO_SOLVERS__<name>__COMMAND_PRE` | The command used by the solver `<name>` for its pre-processing step | `""` |
| `VIMSEO_SOLVERS__<name>__COMMAND_POST` | The command used by the solver `<name>` for its post-processing step | `""` |
| `VIMSEO_ROOT_DIRECTORY` | The root directory where tool results are written | `""` |
| `VIMSEO_WORKING_DIRECTORY` | The working directory where tool results are written. If empty, results are exported to unique directories created under the root directory; if set, results are exported under this path | `""` |
| `VIMSEO_RUN_ARCHIVE_MANAGER` | The archive manager backend of the simulations (e.g. `"DirectoryArchive"`, `"MlflowArchive"`) | `"DirectoryArchive"` |
| `VIMSEO_DATABASE__MODE` | The database mode, `"Local"` or `"Team"` | `"Local"` |
| `VIMSEO_DATABASE__LOCAL_URI` | The URI of the local MLflow tracking server | `""` |
| `VIMSEO_DATABASE__TEAM_URI` | The URI of the team's shared MLflow tracking server | `"https://mlflow.irt-aese.local/"` |
| `VIMSEO_DATABASE__USERNAME` | The username used to authenticate against the MLflow tracking server | `""` |
| `VIMSEO_DATABASE__PASSWORD` | The password used to authenticate against the MLflow tracking server | `""` |
| `VIMSEO_DATABASE__EXPERIMENT_NAME` | The MLflow experiment name | `""` |
| `VIMSEO_DATABASE__USE_INSECURE_TLS` | Whether to skip TLS certificate verification | `False` |
| `VIMSEO_DATABASE__SSL_CERTIFICATE_FILE` | Path to a custom SSL certificate file | `""` |

> **Note:** `solvers` is a mapping from solver name to its configuration, so
> `<name>` above can be any key you choose (e.g. `dummy`, `abaqus`). The default
> configuration already defines a `dummy` and an `abaqus` solver; setting
> `VIMSEO_SOLVERS__<name>__...` for a new name adds a new solver entry.
