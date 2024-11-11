#!/usr/bin/env bash


source scripts/bash-common.sh

function is-py-312() {
    local python=$1
    local minor=$(get-py3-minor-version "$python")
    if [ $? -ne 0 ]; then
        return 1
    fi
    test "$minor" -eq 12
}

function find-py-312() {
    local py312=$(which 'python3.12')
    if [ $? -eq 0 ]; then
        if ! is-py-312 "$py312"; then
            fail "$py312 isn't version 3.12"
            return 1
        fi
    else
        py312=$(which 'python3')
        if [ $? -ne 0 ]; then
            return 1
        fi
        >&2 echo 'trying "python3" for python executable'
        if ! is-py-312 "$py312"; then
            error "python3 isn't version 3.12"
            return 1
        fi
    fi
    echo "$py312"
}

function is-supported-test-python() {
    local python=$1
    set -o pipefail
#    minor=$("$python" -V | grep -o -P '(?<=^Python 3\.)\d+(?=\.)')
    minor=$(get-py3-minor-version "$python")
    rc=$?
    set +o pipefail
    if [ -n "$minor" -a "$minor" -lt 12 ]; then
        error "Python less that 3.12 not supported, got $python"
        return 1
    elif [ $rc -ne 0 ]; then
        error "bad Python executable $python"
        return 1
    fi
    return 0
}


VERSION=$(get-package-version)

python=$PYTHON
python312=
test_pythons=()
build_extensions=
build_pure=

# Parse the command-line.
while [ $# -gt 0 ]; do
    arg=$1
    shift
    if [ -z "$arg" ]; then
        continue
    fi
    case "$arg" in
        --pure) build_pure=$arg;;
        --ext) build_extensions=$arg;;
        -*) fail "unsupported opt $arg";;
        *)
            if is-supported-test-python "$arg"; then
                test_pythons+=("$arg")
            fi
            ;;
    esac
done


# Resolve $python, $python312, and $test_pythons.

if [ -z "$python312" ]; then
    if [ -n "$python" ]; then
        if is-py-312 "$python"; then
            python312=$python
        fi
    else
        for maybe in "${test_pythons[@]}"; do
            if is-py-312 "$maybe"; then
                python312=$maybe
                break
            fi
        done
        if [ -z "$python312" ]; then
            python312=$(find-py-312)
            if [ $? -ne 0 ]; then
                error "failed to discover a Python 3.12 executable"
                python312=
            fi
        fi
    fi
elif ! is-py-312 "$python312"; then
    fail "$python312 isn't version 3.12"
fi

if [ -z "$python" ]; then
    if [ -n "$python312" ]; then
        python=$python312
    else
        for maybe in "${test_pythons[@]}"; do
            # Use the first one.
            python=$maybe
        done
        if [ -z "$python" ]; then
            python='python3'
            if ! which python3 &>/dev/null; then
                fail "could not find a python 3 executable"
            fi
        fi
    fi
fi

orig_build_extensions=$build_extensions
if [ -z "$build_extensions" ]; then
    if [ -n "$build_pure" ]; then
        python312=
    elif [ -n "$python312" ]; then
        build_extensions='--ext'
    fi
elif [ -z "$python312" ]; then
    exit 1
fi
if [ -z "$build_pure" ]; then
    if [ -n "$orig_build_extensions" ]; then
        python=
    elif [ -n "$python" ]; then
        build_pure='--pure'
    fi
elif [ -z "$python" ]; then
    exit 1
fi

if [ -n "$python" ] && ! [[ " ${test_pythons[*]} " =~ [[:space:]]${python}[[:space:]] ]]; then
    if is-supported-test-python "$python"; then
        test_pythons+=("$python")
    fi
fi
if [ -n "$python312" ] && ! [[ " ${test_pythons[*]} " =~ [[:space:]]${python312}[[:space:]] ]]; then
    if is-supported-test-python "$python312"; then
        test_pythons+=("$python312")
    fi
fi


set -e


# Set up the tools.

# XXX venv?

if [ -n "$python" ]; then
    echo
    (set -x
    "$python" -m pip install --upgrade pip
    "$python" -m pip install --user --upgrade setuptools
    "$python" -m pip install --user --upgrade wheel
    "$python" -m pip install --user --upgrade build
    )
fi
if [ -n "$python312" -a "$python312" != "$python" ]; then
    echo
    (set -x
    "$python312" -m pip install --upgrade pip
    "$python312" -m pip install --user --upgrade setuptools
    "$python312" -m pip install --user --upgrade wheel
    "$python312" -m pip install --user --upgrade build
    )
fi

(set -x
rm -rf dist/*.tar.gz
rm -rf dist/*.whl
rm -rf backport_3.12/dist/*.tar.gz
rm -rf backport_3.12/dist/*.whl
)
    

# Build!

echo
echo '##############################'
echo '# building interpreters_734'
echo '##############################'
echo

if [ -z "$build_pure" ]; then
    error "not building this package"
else
    build_args=()
    
    (set -x
    "$python" -m build "${build_args[@]}"
    )
    if [ $? -ne 0 ]; then
        exit 1
    fi

    interpreters_734_wheel=$(ls dist/*.whl)
    interpreters_734_tarball=$(ls dist/*.tar.gz)
fi


echo
echo '##############################'
echo '# building interpreters-3-12'
echo '##############################'
echo

if [ -z "$build_extensions" ]; then
    error "not building this package"
else
    build_args=('--no-isolation')
    
    set +e
    (set -x
    &>/dev/null pushd 'backport_3.12'
    "$python312" -m build "${build_args[@]}"
    )
    rc=$?
    (set -x
    &>/dev/null popd
    )
    set -e
    if [ $rc -ne 0 ]; then
        exit 1
    fi

    interpreters_3_12_wheel=$(ls backport_3.12/dist/*.whl)
    interpreters_3_12_tarball=$(ls backport_3.12/dist/*.tar.gz)
fi


# Run tests.

set +e

echo
echo '####################'
echo '# running tests'
echo '####################'
echo

if [ -z "$build_extensions" -a -z "$build_pure" ]; then
    error 'no builds to test'
    exit 0
fi

numfailed=0
if [ -n "$build_extensions" ]; then
    python_args=()
    for python in ${test_pythons[@]}; do
        if ! is-py-312 "$python"; then
            continue
        fi
        python_args+=(--python "$python")
    done
#    (set -x
    scripts/test-package.sh \
        "${python_args[@]}" \
        "$interpreters_3_12_wheel" "$interpreters_3_12_tarball"
#    )
    subnumfailed=$?
    ((numfailed+=$subnumfailed))
fi
if [ -n "$build_pure" ]; then
    python_args=()
    for python in ${test_pythons[@]}; do
        if is-py-312 "$python"; then
            continue
        fi
        python_args+=(--python "$python")
    done
    if [ ${#python_args[@]} -gt 0 ]; then
#        (set -x
        scripts/test-package.sh \
            "${python_args[@]}" \
            "$interpreters_734_wheel" "$interpreters_734_tarball"
#        )
        subnumfailed=$?
        ((numfailed+=$subnumfailed))
    fi

    python_args=()
    for python in ${test_pythons[@]}; do
        if ! is-py-312 "$python"; then
            continue
        fi
        python_args+=(--python "$python")
    done
    if [ ${#python_args[@]} -gt 0 ]; then
#        (set -x
        scripts/test-package.sh \
            "${python_args[@]}" \
            --dependency "$interpreters_3_12_wheel" \
            "$interpreters_734_wheel" "$interpreters_734_tarball"
#        )
        subnumfailed=$?
        ((numfailed+=$subnumfailed))
    fi
fi

if [ $numfailed -gt 0 ]; then
    echo
    fail "$numfailed test failures"
fi
