#!/usr/bin/env bash
# A script to create an Anaconda environment with gemseo and plugins.
# The environment will be named gemseo-<gemseo version>-py-<python version>
#
# This is a basic variant of install.sh: it only creates the environment and
# installs gemseo and its pip plugins. It does NOT build pyoptsparse, inject
# SNOPT sources, or run the test suites.

# Bash safeguards.
set -eo pipefail

# Redirect trace output (set -x) to a log file instead of mixing with stderr.
log_file="install-basic-$(date +%Y%m%d-%H%M%S).log"
exec {BASH_XTRACEFD}>"$log_file"
set -x
echo "Trace output is being logged to $log_file"

###############################################################################
# Functions
###############################################################################

# Cleanup on failure: remove partially created conda environment.
cleanup() {
  local exit_code=$?
  if [ $exit_code -ne 0 ] && [ -n "${env_path:-}" ] && [ -d "$env_path" ]; then
    echo "Error occurred (exit code $exit_code). Removing partial environment: $env_path"
    conda env remove --prefix "$env_path" --yes 2>/dev/null || rm -rf "$env_path"
  fi
}

# Define the usage message
usage() {
  echo "Usage: $0 --index-url-private <url> --index-url-public <url> --index-username <user> --index-password <pass> --python-version <version> --constraints <constraints> --requirements <requirements> --target-path <path>"
  echo "Options accept both '--opt value' and '--opt=value' forms."
  echo "Private-index credentials may also be set via INDEX_USERNAME and INDEX_PASSWORD."
}

# Toggle xtrace without logging the toggle itself, used to keep credentials out
# of the trace log.
xtrace_off() { { set +x; } 2>/dev/null; }
xtrace_on() { { set -x; } 2>/dev/null; }

# Percent-encode a string so credentials can be embedded in an index URL even
# when they contain reserved characters (e.g. '@' in an email-like username).
urlencode() {
  local s="$1" out="" c i
  for ((i = 0; i < ${#s}; i++)); do
    c="${s:i:1}"
    case "$c" in
    [a-zA-Z0-9.~_-]) out+="$c" ;;
    *) printf -v c '%%%02X' "'$c"; out+="$c" ;;
    esac
  done
  printf '%s' "$out"
}

configure_repositories() {
  # Configuration for pip.
  export PIP_CERT=/projects/NEXTAIR/irt/conf/cert.pem
  # When credentials are provided, embed them (percent-encoded) into
  # index_url_private so every private-index fetch (pip, uv) authenticates.
  # Done with xtrace off to keep the password out of the trace log.
  if [ -n "$index_username" ]; then
    xtrace_off
    local enc_user enc_pass
    enc_user=$(urlencode "$index_username")
    enc_pass=$(urlencode "$index_password")
    index_url_private="${index_url_private/:\/\//://$enc_user:$enc_pass@}"
    xtrace_on
  fi
  # For private packages, use the main index to ensure those packages are picked first.
  export PIP_INDEX_URL="$index_url_private"
  # For public packages, this one needs no credentials but it has corrupted packages (graphviz).
  export PIP_EXTRA_INDEX_URL="$index_url_public"
  # Use a local cache directory to avoid reproducibility issues.
  export PIP_CACHE_DIR=$(pwd)/.cache/pip

  # Configuration for uv.
  # Private index first: uv's default first-index strategy stops at the first
  # index that has a package, so private packages must take precedence over
  # their possibly-corrupted public counterparts.
  export UV_INDEX="$PIP_INDEX_URL $PIP_EXTRA_INDEX_URL"
  export UV_NATIVE_TLS=true
  # Avoid using locally stored credentials to avoid reproducibility issues.
  export UV_CREDENTIALS_DIR=$(pwd)/.uv/credentials
  # Use a local cache directory to avoid reproducibility issues.
  export UV_CACHE_DIR=$(pwd)/.cache/uv

  # Write the package constraints to a temporary file.
  constraints_path=$(mktemp)
  echo "$constraints" | tr ' ' '\n' >"$constraints_path"

  # Write the package requirements to a temporary file.
  requirements_path=$(mktemp)
  echo "$requirements" | tr ' ' '\n' >"$requirements_path"

  # Remove the temporary constraint/requirement files on exit.
  trap 'rm -f "${constraints_path:-}" "${requirements_path:-}"' EXIT
}

setup_environment() {
  echo "
###############################################################################
# Creating anaconda environment
###############################################################################
"

  # Activate conda (assuming it's installed and available in the system's PATH)
  if ! command -v conda &>/dev/null; then
    echo "Error: Conda is not found."
    exit 1
  fi

  # Create a new environment with the given Python version.
  # The environment lives at target_path; its name is that path's last segment.
  env_path="$target_path"
  env_name=$(basename "$env_path")
  echo "Creating the environment named $env_name in $env_path"
  conda create --prefix "$env_path" --yes python="$python_version"

  # Activate the new environment
  eval "$(command conda 'shell.bash' 'hook' 2>/dev/null)"
  conda activate "$env_path"

  # Check activation
  if [ "$CONDA_PREFIX" != "$env_path" ]; then
    echo "Error: Anaconda environment not activated."
    exit 1
  fi

  # We will use uv instead of pip to install packages in the final environment.
  # because uv is a much better dependency resolver than pip
  # when it comes to take into account several package constraints.
  pip install uv
}

install_packages() {
  echo "
###############################################################################
# Installing gemseo and plugins
###############################################################################
"

  # Install the dot executable necessary to graphviz
  # since it is not part of the pip installed graphviz package.
  # It is embedded in the graphviz Anaconda package.
  # Also install pdflatex that is needed to create xdsm pdf files.
  conda install --yes graphviz pdflatex

  # Install all the pip packages alltogether,
  # the dependencies are usually better handled like this.
  uv pip install \
    --constraints "$constraints_path" \
    --requirement "$requirements_path"
}

###############################################################################
# Argument parsing
###############################################################################

# Set default values from environment variables (if set) or use hardcoded defaults
index_url_private="${INDEX_URL_PRIVATE}"
index_url_public="${INDEX_URL_PUBLIC}"
index_username="${INDEX_USERNAME}"
index_password="${INDEX_PASSWORD}"
python_version="${PYTHON_VERSION:-3.13}"
constraints="${CONSTRAINTS:-numpy<2.3 contourpy<1.3.3 graphviz<0.21 minisom<2.3.6}"
requirements="${REQUIREMENTS:-gemseo[all]==6.3.1 gemseo-private-members-plugins==5.0.4 gemseo-multi-fidelity==0.0.1}"
target_path="${TARGET_PATH:-/tmp}"

# Exit with a clear message when an option is missing its value.
require_value() {
  # $1 = option name, $2 = number of args still available ($#).
  if [ "$2" -lt 2 ]; then
    echo "Error: option '$1' requires a value." >&2
    usage
    exit 1
  fi
}

# Parse the CLI arguments. Both "--opt value" and "--opt=value" are accepted.
while [ $# -gt 0 ]; do
  # Normalize "--opt=value" into the positional pair "--opt" "value".
  if [[ "$1" == --*=* ]]; then
    set -- "${1%%=*}" "${1#*=}" "${@:2}"
  fi

  case "$1" in
  --index-url-public)
    require_value "$1" "$#"
    index_url_public="$2"
    shift 2
    ;;
  --index-url-private)
    require_value "$1" "$#"
    index_url_private="$2"
    shift 2
    ;;
  --index-username)
    require_value "$1" "$#"
    index_username="$2"
    shift 2
    ;;
  --index-password)
    require_value "$1" "$#"
    xtrace_off
    index_password="$2"
    xtrace_on
    shift 2
    ;;
  --python-version)
    require_value "$1" "$#"
    python_version="$2"
    shift 2
    ;;
  --constraints)
    require_value "$1" "$#"
    constraints="$2"
    shift 2
    ;;
  --requirements)
    require_value "$1" "$#"
    requirements="$2"
    shift 2
    ;;
  --target-path)
    require_value "$1" "$#"
    target_path="$2"
    shift 2
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "Error: unknown option '$1'." >&2
    usage
    exit 1
    ;;
  esac
done

# Check if all required arguments are provided
if [ -z "$index_url_private" ] || [ -z "$index_url_public" ]; then
  usage
  exit 1
fi

# Credentials are optional, but a username and password go together.
if { [ -n "$index_username" ] && [ -z "$index_password" ]; } ||
  { [ -z "$index_username" ] && [ -n "$index_password" ]; }; then
  echo "Error: --index-username and --index-password must be provided together." >&2
  usage
  exit 1
fi

echo "Index URL for private packages: $index_url_private"
echo "Index URL for public packages: $index_url_public"
echo "Private-index credentials: $([ -n "$index_username" ] && echo "provided (user $index_username)" || echo "none")"
echo "Python version: $python_version"
echo "Constraints: $constraints"
echo "Requirements: $requirements"
echo "Target path: $target_path"

###############################################################################
# Main
###############################################################################

# Cleanup the env if something goes wrong.
#trap cleanup EXIT

configure_repositories
setup_environment
install_packages
