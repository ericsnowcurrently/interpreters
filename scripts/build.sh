#!/usr/bin/env bash

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$(dirname "$SCRIPTS_DIR")
workdir=$(realpath "$PROJECT_DIR/build")


source $SCRIPTS_DIR/_utils.sh
source $SCRIPTS_DIR/_cpython.sh
source $SCRIPTS_DIR/_common.sh


&>/dev/null pushd $PROJECT_DIR

set -e

PYTHON_312=$(script-ensure-cpython "$PYTHON_312" "$workdir" 3.12)

venv_exe=$(script-ensure-build-venv "$PYTHON_312" "$workdir" 3.12)

tarball=$(script-build-package "$venv_exe")

script-check-built-modules "$venv_exe" "$tarball"

&>/dev/null popd


# vim: set filetype=sh :
