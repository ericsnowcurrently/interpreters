#!/usr/bin/env bash

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$(dirname "$SCRIPTS_DIR")
workdir=$(realpath "$PROJECT_DIR/build")


&>/dev/null pushd $PROJECT_DIR

source $SCRIPTS_DIR/_utils.sh

if [ -z "$PYTHON_312" ]; then
    echo "###################################################"
    echo "# \$PYTHON_312 not set; finding/building it"
    echo "###################################################"
    echo

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
PYTHON_312_REVISION=$(get-cpython-revision "$PYTHON_312")


echo
echo "###################################################"
echo "# setting up the build venv"
echo "# (using $("$PYTHON_312" -V))"
echo "# ($PYTHON_312)"
if [ -n "$PYTHON_312_REVISION" ]; then
    echo "# (revision $PYTHON_312_REVISION)"
else
    echo "# (revision unknown)"
fi
echo "###################################################"
echo

set -e

venv_exe=$(ensure-clean-matching-venv "$workdir" "$PYTHON_312" 3.12 $PYTHON_312_REVISION)
link=$(resolve-matching-base-venv "$workdir" 3.12)
if [ "$venv_exe" != "$link" ]; then
    echo "using symlink to $venv_exe"
    venv_exe=$(resolve-venv-python "$link" 3.12)
fi

(set -x
"$venv_exe" -m pip install --upgrade pip
"$venv_exe" -m pip install --upgrade setuptools
"$venv_exe" -m pip install --upgrade wheel
"$venv_exe" -m pip install --upgrade build
)


echo
echo "###################################################"
echo "# building the extension modules"
echo "###################################################"
echo

(set -x
"$venv_exe" -P -m build --no-isolation
)


echo
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
#"$venv_exe" -m pip uninstall --yes interpreters_3_12
)

&>/dev/null popd


# vim: set filetype=sh :
