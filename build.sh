#!/usr/bin/env bash

PROJECT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
workdir=$(realpath "$PROJECT_DIR/build")


&>/dev/null pushd $PROJECT_DIR

if [ -z "$PYTHON_312" ]; then
    source cpython_helpers.sh

    PYTHON_312=$(ensure-cpython 3.12 "$workdir")
    if [ -z "$PYTHON_312" ]; then
        log 'Please set $PYTHON_312'
        exit 1
    fi
else
    if [ "$(basename "$PYTHON_312")" = "$PYTHON_312" ]; then
        PYTHON_312=$(which "$PYTHON_312")
    fi
fi


echo
echo "###################################################"
echo "# building the extension modules"
echo "# (using $("$PYTHON_312" -V))"
echo "# ($PYTHON_312)"
echo "###################################################"
echo

set -e

venv_exe=$(ensure-clean-venv "$workdir" "$PYTHON_312" 3.12 $PYTHON_312_REVISION)

(set -x
"$venv_exe" -m pip install --upgrade pip
"$venv_exe" -m pip install --upgrade setuptools
"$venv_exe" -m pip install --upgrade wheel
"$venv_exe" -m pip install --upgrade build
"$venv_exe" -P -m build --no-isolation
)

echo "###################################################"
echo "# checking the extension modules"
echo "###################################################"
echo

#interpreters_3_12-0.0.1.1.tar.gz
#interpreters_3_12-0.0.1.1-cp312-cp312-linux_x86_64.whl
DIST_TARBALL=$(ls dist/interpreters_3_12-*.tar.gz)
DIST_WHEEL=$(ls dist/interpreters_3_12-*.whl)

(set -x
"$venv_exe" -m pip install $DIST_TARBALL
"$venv_exe" -c 'import _interpreters'
"$venv_exe" -c 'import _interpchannels'
"$venv_exe" -c 'import _interpqueues'
# XXX Do not bother uninstalling?
"$venv_exe" -m pip uninstall interpreters_3_12
)

&>/dev/null popd


# vim: set filetype=sh :
