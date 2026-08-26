<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

## How to write logs to a file with VIMSEO

To redirect VIMSEO logs to a file, use `activate_logger` with a timestamped filename to avoid overwriting previous runs.

```python
import logging
from datetime import datetime
from pathlib import Path
from vimseo.utilities.logger import activate_logger

# Define your working directory
working_directory = Path("path/to/output")
working_directory.mkdir(parents=True, exist_ok=True)

# Generate a unique timestamp down to the millisecond
now = datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M-%S-") + f"{now.microsecond // 1000:03d}"

# Activate the logger
activate_logger(
    level=logging.INFO,
    filename=working_directory / f"log_{timestamp}.txt",
    filemode="w",
)
```

This will create a log file such as `log_2026-06-11_14-32-45-123.txt` in the specified directory.

**Parameters:**

| Parameter | Description | Default |
|---|---|---|
| `logger_name` | Name of the logger to configure. If empty, configures the root logger | `""` |
| `level` | Logging verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"` | `logging.INFO` |
| `date_format` | Format of the date in log messages | `DEFAULT_DATE_FORMAT` |
| `message_format` | Format of log messages | `DEFAULT_MESSAGE_FORMAT` |
| `filename` | Path to the log file. If empty, logs to the console only | `""` |
| `filemode` | `"w"` to overwrite, `"a"` to append | `"a"` |

> **Note:** By default (`filename=""`), logs are printed to the console only. Providing a `filename` redirects output to the specified file.
