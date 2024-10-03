#!/usr/bin/env bash


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
req_files=("$@")


# Gather metadata.

if [ ! -e src/CPYTHON_BRANCH ]; then
    last_branch=$(git show HEAD:src/CPYTHON_BRANCH)
else
    last_branch=$(cat src/CPYTHON_BRANCH)
fi
last_branch=$(python3 -c "print('$last_branch'.strip(), end='')")

if [ ! -e src/CPYTHON_REVISION ]; then
    last_revision=$(git show HEAD:src/CPYTHON_REVISION)
else
    last_revision=$(cat src/CPYTHON_REVISION)
fi
last_revision=$(python3 -c "print('$last_revision'.strip(), end='')")


# Normalize the request.

indirect=
case "$req_ref" in :) indirect=$req_ref;; esac

branch=
requested=$req_ref
if [ -z "$requested" ]; then
    requested='main'
    branch=$requested
elif case "$requested" in 3.*) true;; *) false;; esac; then
    branch=$requested
elif [ "$requested" = ':LAST:' ]; then
    requested=$last_branch
    if [ -n "$requested" ]; then
        branch=$requested
    else
        requested=$last_revision
    fi
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

DEV_VERSION=3.14
resolve-revision "$requested"
if [ -z "$revision" -a "$branch" = "$DEV_VERSION" ]; then
    resolve-revision main
fi

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
    if [ -z "$branch" -a "$revision" = "$last_revision" ]; then
        branch=$last_branch
    fi
fi


# Resolve the files.

FILES=(
interpreters/__init__.py
interpreters/channels.py
interpreters/queues.py
)

files=("${req_files[@]}")
files_label="${files[@]}"
if [ -z "$files" ]; then
    files=(${FILES[@]})
    files_label='all'
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
elif [ "$requested" = "$last_branch" ]; then
    echo "# branch:   ${branch}  (last)"
else
    echo "# branch:   ${branch}"
fi
echo "# files:    $files_label"
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


# Download the files.

CPYTHON_DOWNLOAD="https://raw.githubusercontent.com/python/cpython/${revision}"
DOWNLOAD_DIR=downloads

interp_loc=
case "$branch" in
    #main) interp_loc='public';;
    #3.26) interp_loc='public';;
    main) interp_loc='private-public';;
    3.14) interp_loc='private-public';;
    3.13) interp_loc='private';;
    3.*) echo "ERROR: unsupported branch $branch"; exit 1;;
    "") interp_loc='';;
    *) echo "ERROR: unsupported branch $branch"; exit 1;;
esac

echo "# clearing old files"
rm -rf src/*
for relfile in "${files[@]}"; do
    mkdir -p $(dirname src/$relfile)
done

function download-file() {
    local relfile=$1
    shift
    local locs=("$@")
    if [ ${#locs[@]} -eq 0 ]; then
        locs=('')
    fi

    if case "$relfile" in *.py) true;; *) false;; esac; then
        baseurl="${CPYTHON_DOWNLOAD}/Lib"
    else
        baseurl="${CPYTHON_DOWNLOAD}"
    fi

    echo "# ++ $relfile"
    echo "# ++++++++++++++++++++++++++++++++++++++"

    rc=0
    for loc in "${locs[@]}"; do
        if [ $rc -ne 0 ]; then
            echo '# falling back to alternate location'
        fi

        if [ -z "$loc" ]; then
            target="${baseurl}/${relfile}"
        else
            target="${baseurl}/${loc}/${relfile}"
        fi
        (set -x
        curl --fail -o "src/${relfile}" "${target}"
        )
        rc=$?
        if [ $rc -eq 0 ]; then
            break
        fi
    done

    echo "# ++++++++++++++++++++++++++++++++++++++"

    if [ $rc -ne 0 ]; then
        echo
        >&2 echo 'ERROR: download failed'
        exit 1
    fi
}


echo "# downloading from upstream"
for relfile in "${files[@]}"; do
    if [ "$(dirname $relfile)" = 'interpreters' ]; then
        echo
        case "$interp_loc" in
            public) download-file "$relfile";;
            private) download-file "$relfile" 'test/support';;
            public-private) download-file "$relfile" '' 'test/support';;
            private-public) download-file "$relfile" 'test/support' '';;
            *) echo "#### unreachable ($interp_loc) ####"
        esac
    else
        download-file "$relfile"
    fi
done


# Update the metadata.

echo "# updating metadata"
echo -n $revision > src/CPYTHON_REVISION
echo -n "$branch" > src/CPYTHON_BRANCH


# Update the repo.

git add src
2>/dev/null git add src/CPYTHON_BRANCH
