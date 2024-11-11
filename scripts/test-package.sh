#!/usr/bin/env bash

source scripts/bash-common.sh


# Parse command-line args.
distdir=
pkgname=
version=
dep_args=()
pythons=()
archives=()
while [ $# -gt 0 ]; do
    arg=$1
    shift
    case "$arg" in
        --distdir)
            if [ -n "$distdir" ]; then
                fail 'already got a distdir arg'
            fi
            distdir=$1
            shift
            ;;
        --package)
            if [ -n "$pkgname" ]; then
                fail 'already got a pkgname arg'
            fi
            pkgname=$1
            shift
            ;;
        --version)
            if [ -n "$version" ]; then
                fail 'already got a version arg'
            fi
            version=$1
            shift
            ;;
        --dependency) dep_args+=($arg "$1"); shift;;
        --python) pythons+=("$1"); shift;;
        -*) fail "unsupported option $arg";;
        *) archives+=("$arg");;
    esac
done
if [ -z "$distdir" ]; then
    distdir='dist'
fi
if [ -z "$pkgname" ]; then
    for archive in "${archives[@]}"; do
        pkgname=$(echo $(basename "$archive") | grep -o -P '^\w+(?=-)')
        if [ $? -eq 0 ]; then
            break
        fi
    done
    if [ -z "$pkgname" ]; then
        pkgname='???'
    fi
fi

# Resolve the archives.
if [ "${#archives[@]}" -eq 0 ]; then
    if [ -n "$pkgname" -a "$pkgname" != '???' ]; then
        for archive in $(find-archives "$pkgname" "$version" "$distdir"); do
            archives+=("$archive")
        done
    fi
    if [ "${#archives[@]}" -eq 0 ]; then
        fail 'no matching archives found'
    fi
fi

# Resolve the pythons.
if [ ${#pythons[@]} -eq 0 ]; then
    # XXX Derive from the wheel filenames.
    fail 'no pythons provided'
fi


# Run tests.
echo
echo '########################################'
echo "# testing package - $pkgname"
echo '########################################'
echo
numfailed=0
for archive in ${archives[@]}; do
    for python in ${pythons[@]}; do
        echo
        echo '########################################'
        echo '#-------------------'
        echo "# $archive"
        echo "# $python"
        echo '#-------------------'
        echo
        (set -x
        "$python" scripts/test-archive.py "${dep_args[@]}" "$archive"
        )
        if [ $? != 0 ]; then
            ((numfailed+=1))
        fi
    done
done
exit $numfailed
