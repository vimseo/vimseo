<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

`IntegratedModel.set_n_cpus(n_cpus)` sets the number of CPUs of the job executor of the `run` component, keeping its other options, instead of `model.run.job_executor.set_options(...)` with the settings class of the executor. It is no longer deprecated, and no longer a no-op on a `PreRunPostModel`. It raises a `ValueError` when the run component has no job executor. `IntegratedModel.n_cpus` is the number of CPUs of this job executor, else 1.
