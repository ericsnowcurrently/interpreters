#!/usr/bin/env bash

set -e


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

function check-python-feature-version() {
    local python=$1
    local expected=$2

    if [ "$(echo "$expected" | grep -o -P '\b\d+\.\d+\b')" != "$expected" ]; then
        err "bad expected version $expected"
        return 1
    fi

    local version=$("$python" --version | grep -o -P '\b\d+\.\d+\b')
    if [ -z "$version" ]; then
        log "could not get version from $("$python" --version)"
        log "  (proceeding as though it matched)"
        return 0
    elif [ "$version" != "$expected" ]; then
        err "version mismatch ($version != $expected)"
        return 1
    fi
    return 0
}


#######################################
# sub-scripts

function ensure-cpython() {
    local python=$1
    shift
    local workdir=$1
    shift
    local debug=$1
    shift
    if [ -z "$debug" ]; then
        debug=false
    fi

    set -e

    # Make sure $python is valid.
    if [ -z "$python" ]; then
        # XXX Look for it on $PATH?
        # XXX Look for a locally-built cpython.
        # XXX Build cpython locally.
        fail "missing python arg"
    elif [ ! -e "$python" ]; then
        fail "bad python arg '$python'"
    else
        if ! check-python-feature-version "$python" 3.12; then
            exit 1
        fi
    fi

    echo "$python"
}

function ensure-venv() {
    local venvsdir=$1
    local python=$2

    set -e

    makedirs "$venvsdir"

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

    set -e

    (set -x
    1>&2 "$venvexe" -m pip install --upgrade setuptools
    1>&2 "$venvexe" -m pip install --upgrade wheel
    1>&2 "$venvexe" -m pip install --upgrade build
    )
}

function build-package() {
    local venvexe=$1
    local debug=$2
    if [ -z "$debug" ]; then
        debug=false
    fi
    # XXX Use $debug.

    local distdir="$PROJECT_DIR/dist"

    set -e

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

    set -e

    (set -x
    1>&2 "$venvexe" -m pip install "$tarball"
    "$venvexe" -c 'import _interpreters'
    "$venvexe" -c 'import _interpchannels'
    "$venvexe" -c 'import _interpqueues'
    "$venvexe" -c 'import interpreters'
    "$venvexe" -c 'import interpreters.queues'
    "$venvexe" -c 'import interpreters.channels'
    )
}


#######################################
# the script

python=
debug=false

function parse-cli() {
    local ci=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --ci)
                ci=true
                ;;
            --debug)
                debug=true
                ;;
            --no-debug)
                debug=false
                ;;
            --*|-*)
                fail "unsupported option '$1'"
                ;;
            '')
                fail "got empty arg"
                ;;
            *)
                if [ -z "$python" ]; then
                    python=$(abspath "$1")
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
    local debug=$2

    set -e

    local workdir=$(abspath "$PROJECT_DIR/build")

    python=$(ensure-cpython "$python" "$workdir" $debug)

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

    local tarball=$(build-package "$venvexe" $debug | jq --raw-output .tarball)


    echo
    echo "###################################################"
    echo "# checking the extension modules"
    echo "###################################################"
    echo

    check-built-modules "$venvexe" "$tarball"
}

parse-cli "$@"
main "$python" $debug


# vim: set filetype=sh :
