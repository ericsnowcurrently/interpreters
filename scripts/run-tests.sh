#!/usr/bin/env bash

SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$(dirname "$SCRIPTS_DIR")


function log() {
    1>&2 echo "$@"
}

function err() {
    log "ERROR: $@"
}

function fail() {
    err "$@"
    exit 1
}

function abspath() {
    realpath --no-symlinks "$1"
}

function makedirs() {
    local dirname=$1

    if [ -d "$dirname" ]; then
        return 0
    elif [ -e "$dirname" ]; then
        fail "$dirname exists but isn't a directory"
    else
        (set -x
        1>&2 mkdir -p "$dirname"
        )
    fi
}

function is-venv() {
    local python=$1

    if [ ! -L "$python" ]; then
        return 1
    fi
    local parent=$(dirname "$python")
    if [ "$(basename "$parent")" != 'bin' ]; then
        return 1
    fi
    if "$python" -c 'import sys; sys.exit(sys.base_prefix != sys.prefix)'; then
        return 1
    fi
    return 0
}


#######################################
# sub-scripts

function create-test-venv() {
    local venvsdir=$1
    local python=$2

    set -e

    makedirs "$venvsdir"

    local venvroot="$venvsdir/venv_test"
    local venvexe="$venvroot/bin/python3.12"

    if [ -d "$venvroot" ]; then
        # XXX Just make sure it's valid?
        (set -x
        rm -r "$venvroot"
        )
    elif [ -e "$venvroot" ]; then
        (set -x
        rm "$venvroot"
        )
    fi

    (set -x
    1>&2 "$python" -m venv "$venvroot"
    1>&2 "$venvexe" -m pip install --upgrade pip
    )

    log
    log "venv created: $venvroot"
    log "venv python: $venvexe"

    echo "$venvexe"
}


#######################################
# the script

python=
install=true

function parse-cli() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --install)
                install=true
                ;;
            --no-install)
                install=false
                ;;
            --*|-*)
                log "unsupported option '$1'"
                ;;
            *)
                if [ -z "$python" ]; then
                    python=$1
                    if [ -z "$python" ]; then
                        fail "missing python arg"
                    fi
                else
                    fail "unsupported arg '$1'"
                fi
                ;;
        esac
        shift
    done
}

function main() {
    local python=$1
    local install=$2

    if [ -z "$python" ]; then
        fail "missing python arg"
    elif [ ! -e "$python" ]; then
        fail "bad python arg $python"
    else
        python=$(abspath "$python")
    fi
    if [ -z "$install" ]; then
        install=true
    fi

    set -e

    &>/dev/null pushd $PROJECT_DIR

    local workdir=$(abspath "$PROJECT_DIR/build")

    local venvexe=
    if is-venv "$python"; then
        venvexe=$python
    else
        echo
        echo "###################################################"
        echo "# preparing the test venv"
        echo "###################################################"
        echo

        venvexe=$(create-test-venv "$workdir" "$python")
    fi

    if [ -z "$install" ] || $install; then
        echo
        echo "###################################################"
        echo "# installing the package"
        echo "###################################################"
        echo

        local tarball=$(ls dist/interpreters_3_12-*.tar.gz)
        if [ -z "$tarball" ]; then
            fail "package not built yet"
        fi

        (set -x
        1>&2 "$venvexe" -m pip install --force-reinstall "$tarball"
        )
    fi

    echo
    echo "###################################################"
    echo "# running the tests"
    echo "###################################################"
    echo

    local topdir="$PROJECT_DIR/src"
    (set -x
    "$venvexe" -m unittest discover $topdir/tests/test_interpreters --top-level $topdir
    )

    &>/dev/null popd
}

parse-cli "$@"
main "$python" $install


# vim: set filetype=sh :
