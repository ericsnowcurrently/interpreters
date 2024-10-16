#!/usr/bin/env bash

MAIN_VERSION='3.14'


# project tree

UPSTREAM_ROOT="src-upstream"
CUSTOM_ROOT='src-custom'
SOURCE_ROOT='src'

CUSTOM_FILES=(
interpreters_backport/__init__.py
interpreters_backport/concurrent/__init__.py
interpreters_backport/concurrent/futures/__init__.py
interpreters_experimental/__init__.py
interpreters_experimental/interpreters/__init__.py
)

UPSTREAM_FILES=(
interpreters/__init__.py
interpreters/channels.py
interpreters/queues.py
interpreters/_crossinterp.py
concurrent/futures/interpreter.py
concurrent/futures/thread.py
)


# Parse the CLI.

req_ref=$1
dryrun=
shift
if [ "$req_ref" = '--dry-run' ]; then
    dryrun=$req_ref
    req_ref=$1
    shift
elif [ "$1" = '--dry-run' ]; then
    dryrun=$1
    shift
fi
if [ "$req_ref" = '--' ]; then
    req_ref=''
elif [ "$1" = '--' ]; then
    shift
fi


# Gather metadata.

if [ ! -e $UPSTREAM_ROOT/CPYTHON_BRANCH ]; then
    last_branch=$(2>/dev/null git show HEAD:$UPSTREAM_ROOT/CPYTHON_BRANCH)
else
    last_branch=$(cat $UPSTREAM_ROOT/CPYTHON_BRANCH)
fi
last_branch=$(python3 -c "print('$last_branch'.strip(), end='')")

if [ ! -e $UPSTREAM_ROOT/CPYTHON_VERSION ]; then
    last_version=$(2>/dev/null git show HEAD:$UPSTREAM_ROOT/CPYTHON_VERSION)
else
    last_version=$(cat $UPSTREAM_ROOT/CPYTHON_VERSION)
fi
last_version=$(python3 -c "print('$last_version'.strip(), end='')")

if [ ! -e $UPSTREAM_ROOT/CPYTHON_REVISION ]; then
    last_revision=$(2>/dev/null git show HEAD:$UPSTREAM_ROOT/CPYTHON_REVISION)
else
    last_revision=$(cat $UPSTREAM_ROOT/CPYTHON_REVISION)
fi
last_revision=$(python3 -c "print('$last_revision'.strip(), end='')")


# Normalize the request.

indirect=
case "$req_ref" in :) indirect=$req_ref;; esac

branch=
version=
requested=$req_ref
if [ -z "$requested" -o "$requested" == $MAIN_VERSION ]; then
    requested='main'
fi
if [ "$requested" == 'main' ]; then
    branch=$requested
    version=$MAIN_VERSION
elif case "$requested" in 3.*) true;; *) false;; esac; then
    branch=$requested
    version=$requested
elif [ "$requested" = '.' ]; then
    requested=$last_branch
    if [ -n "$requested" ]; then
        branch=$requested
        version=$last_version
    else
        requested=$last_revision
    fi
elif [ "$requested" = '.branch' ]; then
    requested=$last_branch
    if [ -z "$requested" ]; then
        >&2 echo "ERROR: no last branch"
        exit 1
    fi
    branch=$requested
    version=$last_version
elif case "$requested" in .rev|.revision) true;; *) false;; esac; then
    requested=$last_revision
    branch=$last_branch
    if [ -z "$requested" ]; then
        >&2 echo "ERROR: no last revision"
        exit 1
    fi
fi

if [ -z "$version" -a -n "$branch" ]; then
    version=$branch
    if [ "$version" == 'main' ]; then
        version=$MAIN_VERSION
    fi
fi
if [ -z "$last_version" -a "$branch" = "$last_branch" ]; then
    last_version=$version
fi


# Resolve the revision.

revision=
function resolve-revision() {
    local ref=$1
    cmd="curl --fail --silent https://api.github.com/repos/python/cpython/commits/${ref}"
    echo "+ ${cmd} | jq -r .sha"
    revision=$($cmd | jq -r .sha)
    if [ $? -ne 0 ]; then
        revision=
    fi
}

resolve-revision "$requested"
#if [ -z "$revision" -a "$branch" = "$MAIN_VERSION" ]; then
#    resolve-revision main
#fi

refname=
if [ "$revision" != "$requested" ] && ! case "$revision" in $requested*) true;; *) false;; esac ; then
    # The requested ref was a branch or tag.
#    if [ -n "$indirect" -a "$requested" = "$last_branch" ]; then
#        if [ -n "$last_revision" -a "$revision" != "$last_revision" ]; then
#            fatal "revision for last branch '$last_branch' does not match last revision ($revision != $last_revision)"
#        fi
#    fi
    refname=$requested
#    if [ "$indirect" = ':LAST:' -a "$requested" = "$last_branch" ]; then
#        branch=$requested
#    fi
else
    # The requested ref was a commit hash.
    refname=
    if [ "$revision" = "$last_revision" ]; then
        if [ -z "$branch" ]; then
            branch=$last_branch
        fi
        if [ -z "$version" ]; then
            version=$last_version
        fi
    fi
fi


# Report.

echo
echo "####################"
echo "# Updating from upstream CPython"
echo "# ref:      ${requested}"
if [ -z "$revision" ]; then
    echo "# revision: LOOKUP FAILED"
elif [ "$revision" = "$last_revision" ]; then
    echo "# revision: ${revision}  (last)"
else
    echo "# revision: ${revision}"
fi
if [ -z "$branch" ]; then
    echo "# branch:   ???"
elif [ "$branch" = "$last_branch" ]; then
    echo "# branch:   ${branch}  (last)"
else
    echo "# branch:   ${branch}"
fi
if [ -z "$version" ]; then
    echo "# version:  ???"
elif [ "$version" = "$last_version" ]; then
    echo "# version:  ${version}  (last)"
else
    echo "# version:  $version"
fi
echo "####################"
echo

if [ -z "$revision" ]; then
    >&2 echo "ERROR: failed to get revision"
    exit 1
fi

if [ -n "$dryrun" ]; then
    if [ "$revision" == "$last_revision" ]; then
        >&2 echo 'up-to-date'
        exit 0
    else
        >&2 echo out-of-date
        exit 1
    fi
fi


# prep

echo "# clearing old files"
rm -rf $SOURCE_ROOT/*
rm -rf $UPSTREAM_ROOT/*


# Download the files.

CPYTHON_DOWNLOAD="https://raw.githubusercontent.com/python/cpython/${revision}"

function resolve-upstream() {
    local relfile=$1
    local upstream=$relfile
    # This special case goes away for the main branch once PEP 734 is done.
    if case "$upstream" in interpreters/*) true;; *) false;; esac; then
        upstream="test/support/$upstream"
    fi
    if case "$upstream" in *.py) true;; *) false;; esac; then
        upstream="Lib/$upstream"
    fi
    echo "$upstream"
}

echo "# downloading from upstream"
downloaded=()
for relfile in "${UPSTREAM_FILES[@]}"; do
    upstream=$(resolve-upstream $relfile)
    outfile="$UPSTREAM_ROOT/$upstream"
    url="${CPYTHON_DOWNLOAD}/$upstream"
    echo "# ++ $relfile"
    echo "# ++++++++++++++++++++++++++++++++++++++"
    mkdir -p $(dirname $outfile)
    (set -x
    curl --fail -o "$outfile" "$url"
    )
    rc=$?
    echo "# ++++++++++++++++++++++++++++++++++++++"
    if [ $rc -ne 0 ]; then
        echo
        >&2 echo 'ERROR: download failed'
        exit 1
    fi
    downloaded+=("$outfile")
done

echo
echo "# updating metadata"
echo -n $revision > $UPSTREAM_ROOT/CPYTHON_REVISION
echo -n "$branch" > $UPSTREAM_ROOT/CPYTHON_BRANCH
echo -n "$version" > $UPSTREAM_ROOT/CPYTHON_VERSION


# Apply custom files.

echo
echo "# copying custom files"
for relfile in "${CUSTOM_FILES[@]}"; do
    src="$CUSTOM_ROOT/$relfile"
    dest="$SOURCE_ROOT/$relfile"
    mkdir -p $(dirname $dest)
    (set -x
    cp -r "$src" "$dest"
    )
done

echo
echo "# writing the exported metadata"
meta_branch=$branch
if [ -z "$meta_branch" ]; then
    meta_branch='None  # unknown'
fi
if [ -z "$version" ]; then
    meta_version='None  # unknown'
else
    readarray -d '.' -t parts <<< "$version."
    meta_version="(${parts[0]}, ${parts[1]})"
fi
cat > "$SOURCE_ROOT/interpreters_backport/metadata.py" << EOF
# Generated from $UPSTREAM_ROOT/CPYTHON_REVISION:
UPSTREAM_REVISION = '$revision'
# Generated from $UPSTREAM_ROOT/CPYTHON_BRANCH:
UPSTREAM_BRANCH = $meta_branch
# Generated from $UPSTREAM_ROOT/CPYTHON_VERSION:
UPSTREAM_VERSION = $meta_version
EOF


# Apply upstream files.

echo
echo "# copying upstream files"
for i in ${!downloaded[@]}; do
    src=${downloaded[i]}
    if case "$src" in *channels.py) true;; *) false;; esac; then
        dest="$SOURCE_ROOT/interpreters_experimental/${UPSTREAM_FILES[$i]}"
    else
        dest="$SOURCE_ROOT/interpreters_backport/${UPSTREAM_FILES[$i]}"
    fi
    mkdir -p $(dirname $dest)
    (set -x
    cp -r "$src" "$dest"
    )
done

#echo
#echo "# Applying fixes to copied upstream files"
#sed -i 's/from . import _crossinterp/from interpreters_backport.interpreters import _crossinterp/' \
#    "$SOURCE_ROOT/interpreters_experimental/interpreters/channels.py"
#sed -i 's/from ._crossinterp /from interpreters_backport.interpreters._crossinterp /' \
#    "$SOURCE_ROOT/interpreters_experimental/interpreters/channels.py"


# Update the repo.

git add $SOURCE_ROOT
git add $UPSTREAM_ROOT
#2>/dev/null git add $SOURCE_ROOT/CPYTHON_BRANCH
