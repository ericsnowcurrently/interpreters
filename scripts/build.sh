#!/usr/bin/env bash

set -e


SCRIPTS_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$(dirname "$SCRIPTS_DIR")


function log() {
    1>&2 echo "$@"
}

function fail() {
    1>&2 echo "ERROR: $@"
    exit 1
}

function check-python-version() {
    local python=$1
    local expected=$2

    local version=$("$python" --version | grep -o -P '\b\d+\.\d+\b')
    if [ -z "$version" ]; then
        log "could not get version from $("$python" --version)"
        log "  (proceeding as though it matched)"
        return 0
    elif [ "$version" != "$expected" ]; then
        log "version mismatch ($version != $expected)"
        return 1
    fi
    return 0
}


#######################################
# sub-scripts

function ensure-cpython() {
    local python=$1
    local workdir=$2

    # Make sure $python is valid.
    if [ -z "$python" ]; then
        # XXX Look for it on $PATH?
        # XXX Look for a built one?
        # XXX Build it.
        fail "not implemented"
    elif [ ! -e "$python" ]; then
        fail "bad python arg '$python'"
    else
        if ! check-python-version "$python" 3.12; then
            exit 1
        fi
    fi

    echo "$python"
}

function ensure-venv() {
    local venvsdir=$1
    local python=$2

    mkdir -p "$venvsdir"

    local venvroot=$venvsdir/venv_build
    local venvexe="$venvroot/bin/python3.12"

    (set -x
    1>&2 "$python" -m venv "$venvroot"
    1>&2 "$venvexe" -m pip install --upgrade pip
    )

    log
    log "venv created: $venvroot"
    log "venv python: $venvexe"

    echo "$venvexe"
}

function prep-build-venv() {
    local venvexe=$1

    (set -x
    "$venvexe" -m pip install --upgrade setuptools
    "$venvexe" -m pip install --upgrade wheel
    "$venvexe" -m pip install --upgrade build
    )
}

function build-package() {
    local venvexe=$1

    local distdir="$PROJECT_DIR/dist"

    &>/dev/null pushd $PROJECT_DIR

    (set -x
    1>&2 "$venvexe" -P -m build --no-isolation
    )
    #interpreters_3_12-0.0.1.1.tar.gz
    #interpreters_3_12-0.0.1.1-cp312-cp312-linux_x86_64.whl
    tarball=$(ls $distdir/interpreters_3_12-*.tar.gz)
    wheel=$(ls $distdir/interpreters_3_12-*.whl)

    &>/dev/null popd

    if [ -z "$tarball" ]; then
        fail "dist tarball not created in $distdir"
    fi

    log
    log "extensions built"
    log "tarball: $tarball"
    log "wheel:   $wheel"

    #echo '{ "tarball": "'$tarball'", "wheel": "'$wheel'" }'
    echo '{'
    echo '  "tarball": "'$tarball'",'
    echo '  "wheel": "'$wheel'"'
    echo '}'
}

function check-built-modules() {
    local venvexe=$1
    local tarball=$2

    (set -x
    "$venvexe" -m pip install "$tarball"
    "$venvexe" -c 'import _interpreters'
    "$venvexe" -c 'import _interpchannels'
    "$venvexe" -c 'import _interpqueues'
    )
}


#######################################
# the script

python=

function parse-cli() {
    local ci=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --ci)
                ci=true
                ;;
            --*|-*)
                fail "unsupported option '$1'"
                ;;
            '')
                fail "got empty arg"
                ;;
            *)
                if [ -z "$python" ]; then
                    python=$(realpath --no-symlinks "$1")
                else
                    fail "unsupported arg '$1'"
                fi
                ;;
        esac
        shift
    done

    # Validate the args.
    if [ -z "$python" ]; then
        if $ci; then
            fail 'missing python arg'
        fi
    fi
}


function main() {
    local python=$1

    local workdir=$(realpath "$PROJECT_DIR/build")

    python=$(ensure-cpython "$python" "$workdir")

    # Do the build.

    echo
    echo "###################################################"
    echo "# creating the build venv"
    echo "###################################################"
    echo

    local venvexe=$(ensure-venv "$workdir" "$python")


    echo
    echo "###################################################"
    echo "# preparing the build venv"
    echo "###################################################"
    echo

    prep-build-venv "$venvexe"


    echo
    echo "###################################################"
    echo "# building the extension modules"
    echo "###################################################"
    echo

    local tarball=$(build-package "$venvexe" | jq --raw-output .tarball)


    echo
    echo "###################################################"
    echo "# checking the extension modules"
    echo "###################################################"
    echo

    check-built-modules "$venvexe" "$tarball"
}

parse-cli "$@"
main "$python"


# vim: set filetype=sh :
