#!/usr/bin/env bash

PROJECT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

UTCNOW="$(date --utc +'%Y%m%d-%H%M%S')"
UNPACKED_DIR="build/unpacked-$UTCNOW"

source cpython_helpers.sh


&>/dev/null pushd $PROJECT_DIR

if [ -z "$PYTHON_312" ]; then
    exe_file=build/PYTHON_312
    find-cpython 3.12 "$exe_file"
    if [ -e "$exe_file" ]; then
        PYTHON_312=$(cat "$exe_file")
    fi
    if [ -z "$PYTHON_312" ]; then
        echo "falling back to a locally built python${version}..."
        ensure-cpython-installed 3.12 build "$exe_file"
        if [ -e "$exe_file" ]; then
            PYTHON_312=$(cat "$exe_file")
        fi
        if [ -z "$PYTHON_312" ]; then
            1>&2 echo 'Please set $PYTHON_312'
            exit 1
        fi
    fi
fi


echo "building extension modules with $("$PYTHON_312" -V)"
venv_root=build/venv_312
#"$PYTHON_312" -m venv --clear $venv_root
venv_exe=$venv_root/bin/python3.12

(set -x
"$venv_exe" -m pip install --upgrade pip
"$venv_exe" -m pip install --upgrade setuptools
"$venv_exe" -m pip install --upgrade wheel
"$venv_exe" -m pip install --upgrade build
"$venv_exe" -P -m build --no-isolation
)
#interpreters_3_12-0.0.1.1.tar.gz
#interpreters_3_12-0.0.1.1-cp312-cp312-linux_x86_64.whl

# XXX This must be done using Python 3.12.
#mkdir $UNPACKED_DIR
#tar -C $UNPACKED_DIR -xzf "$(ls dist/*.tar.gz)"
#&>/dev/null pushd $UNPACKED_DIR
#(set -x
#"$venv_exe" -c 'import _interpreters'
#"$venv_exe" -c 'import _interpchannels'
#"$venv_exe" -c 'import _interpqueues'
#)
#&>/dev/null popd
#rm -r $UNPACKED_DIR

&>/dev/null popd


# vim: set filetype=sh :
