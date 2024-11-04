#!/usr/bin/env bash


function error() {
    >&2 echo "ERROR: $@"
}

function fail() {
    error "$@"
    exit 1
}

function is-py-312() {
    local python=$1
    if case $("$python" -V) in Python\ 3.12.*) true;; *) false;; esac then
        return 0
    else
        return 1
    fi
}


python312=$PYTHON
test_pythons=()
mode=

# Parse the command-line.
while [ $# -gt 0 ]; do
    arg=$1
    shift
    if [ -z "$arg" ]; then
        continue
    fi
    case "$arg" in
        --sdist) mode='sdist';;
        --bdist) mode='bdist';;
        --wheel) mode='wheel';;
        --default) mode=;;
        --312|--3.12) python312=$arg;;
        -*) fail "unsupported opt $arg";;
        *) test_pythons+=("$arg");;
    esac
done
if [ -z "$sdist" -a "$bdist" -a -z "$wheel" ]; then
    sdist='--sdist'
    bdist='--bdist'
    wheel='--wheel'
fi


# Resolve $python312 and $test_pythons.
if [ -z "$python312" ]; then
    for python in ${test_pythons[@]}; do
        if is-py-312 "$python"; then
            python312=$python
            break
        fi
    done
    if [ -z "$python312" ]; then
        python312=$(which 'python3.12')
        if [ $? -ne 0 ]; then
            python312=$(which 'python3')
            if [ $? -ne 0 ]; then
                fail "failed to discover a Python executable"
            fi
            echo "trying python3"
        fi
        if ! is-py-312 "$python312"; then
            fail "$python312 isn't version 3.12"
        fi
    fi
else
    if ! is-py-312 "$python312"; then
        fail "$python312 isn't version 3.12"
    fi
fi

if ! [[ " ${test_pythons[*]} " =~ [[:space:]]${python312}[[:space:]] ]]; then
    test_pythons+=("$python312")
fi


set -e


# Set up the tools.

# XXX venv?

for python in ${test_pythons[@]}; do
    echo
    (set -x
    "$python" -m pip install --upgrade pip
    "$python" -m pip install --user --upgrade setuptools
    "$python" -m pip install --user --upgrade wheel
    "$python" -m pip install --user --upgrade build
    )
done


# Build!

echo
echo '####################'
echo '# building'
echo '####################'
echo

build_args=('--no-isolation')
case "$mode" in
    "") ;;
    sdist) build_args+=('--sdist');;
    bdist) fail 'bdist not supported?';;
    wheel) build_args+=('--wheel');;
    *) fail "unsupported mode ($mode)";;
esac

set +e
(set -x
rm -rf dist/*.tar.gz
rm -rf dist/*.tar.whl
)

&>/dev/null pushd 3.12
(set -x
"$python312" -m build "${build_args[@]}"
)
rc=$?
&>/dev/null popd
set -e
if [ $rc -ne 0 ]; then
    exit 1
fi

(set -x
mv 3.12/dist/* dist/
)

echo
echo '####################'
echo '# testing'
echo '####################'

for python in ${test_pythons[@]}; do
    for tarball in $(find dist -name \*.tar.gz); do
        echo
        echo '#----------'
        echo "# $tarball"
        echo
        "$python" scripts/test.py "$tarball"
    done
    
    if is-py-312 "$python"; then
        for wheel in dist/*.whl; do
            echo
            echo '#----------'
            echo "# $wheel"
            echo
            "$python" scripts/test.py "$wheel"
        done
    fi
done
