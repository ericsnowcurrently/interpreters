#!/usr/bin/env bash

MAIN_VERSION='3.14'


# project tree

UPSTREAM_ROOT="src-upstream"
PENDING_ROOT="src-upstream-pending"
CUSTOM_ROOT='src-custom'
SOURCE_ROOT='src'
ROOT_312='3.12'

CUSTOM_FILES=(
interpreters_backport/__init__.py
interpreters_backport/concurrent/__init__.py
interpreters_backport/concurrent/futures/__init__.py
interpreters_experimental/__init__.py
interpreters_experimental/interpreters/__init__.py

shim-compatible-includes.h
shim-new-stuff.h
runtimebackports.c
3.12/Objects/typeobject.c
)

DUMMY_FILES=(
Include/internal/pycore_abstract.h
Include/internal/pycore_ceval.h
Include/internal/pycore_initconfig.h
Include/internal/pycore_modsupport.h
Include/internal/pycore_namespace.h
Include/internal/pycore_pybuffer.h
Include/internal/pycore_pyerrors.h
Include/internal/pycore_pylifecycle.h
Include/internal/pycore_pystate.h
Include/internal/pycore_weakref.h
)

PENDING_FILES=(
Include/internal/pycore_crossinterp.h
Include/internal/pycore_crossinterp_data_registry.h
Python/crossinterp.c
Python/crossinterp_data_lookup.h
Python/crossinterp_exceptions.h

Modules/_interpretersmodule.c
Modules/_interpqueuesmodule.c
Modules/_interpchannelsmodule.c
Modules/_interpreters_common.h

Python/parking_lot.c
)

UPSTREAM_FILES=(
interpreters/__init__.py
interpreters/channels.py
interpreters/queues.py
interpreters/_crossinterp.py
concurrent/futures/interpreter.py
concurrent/futures/thread.py

Modules/_interpretersmodule.c
Modules/_interpqueuesmodule.c
Modules/_interpchannelsmodule.c
Modules/_interpreters_common.h

Include/internal/pycore_crossinterp.h
Include/internal/pycore_crossinterp_data_registry.h
Python/crossinterp.c
Python/crossinterp_data_lookup.h
Python/crossinterp_exceptions.h

Python/interpconfig.c
Python/config_common.h

Include/lock.h
Include/cpython/lock.h
Include/pyatomic.h
Include/cpython/pyatomic.h
Include/cpython/pyatomic_gcc.h
Include/cpython/pyatomic_msc.h
Include/cpython/pyatomic_std.h
Include/internal/pycore_llist.h
Include/internal/pycore_lock.h
Include/internal/pycore_parking_lot.h
Include/internal/pycore_semaphore.h
Python/lock.c
Python/parking_lot.c

3.12:Include/internal/pycore_asdl.h
3.12:Include/internal/pycore_ast.h
3.12:Include/internal/pycore_ast_state.h
3.12:Include/internal/pycore_atexit.h
3.12:Include/internal/pycore_atomic.h
3.12:Include/internal/pycore_bitutils.h
3.12:Include/internal/pycore_ceval_state.h
3.12:Include/internal/pycore_code.h
3.12:Include/internal/pycore_condvar.h
3.12:Include/internal/pycore_context.h
3.12:Include/internal/pycore_dict_state.h
3.12:Include/internal/pycore_dtoa.h
3.12:Include/internal/pycore_exceptions.h
3.12:Include/internal/pycore_faulthandler.h
3.12:Include/internal/pycore_fileutils.h
3.12:Include/internal/pycore_floatobject.h
3.12:Include/internal/pycore_frame.h
3.12:Include/internal/pycore_function.h
3.12:Include/internal/pycore_genobject.h
3.12:Include/internal/pycore_gc.h
3.12:Include/internal/pycore_gil.h
3.12:Include/internal/pycore_global_objects.h
3.12:Include/internal/pycore_global_strings.h
3.12:Include/internal/pycore_hamt.h
3.12:Include/internal/pycore_hashtable.h
3.12:Include/internal/pycore_import.h
3.12:Include/internal/pycore_initconfig.h
3.12:Include/internal/pycore_instruments.h
3.12:Include/internal/pycore_interp.h
3.12:Include/internal/pycore_list.h
3.12:Include/internal/pycore_moduleobject.h
3.12:Include/internal/pycore_object_state.h
3.12:Include/internal/pycore_obmalloc.h
3.12:Include/internal/pycore_parser.h
3.12:Include/internal/pycore_pyarena.h
3.12:Include/internal/pycore_pyhash.h
3.12:Include/internal/pycore_pymath.h
3.12:Include/internal/pycore_pymem.h
3.12:Include/internal/pycore_pythread.h
3.12:Include/internal/pycore_runtime.h
3.12:Include/internal/pycore_signal.h
3.12:Include/internal/pycore_time.h
3.12:Include/internal/pycore_tracemalloc.h
3.12:Include/internal/pycore_tuple.h
3.12:Include/internal/pycore_typeobject.h
3.12:Include/internal/pycore_ucnhash.h
3.12:Include/internal/pycore_unicodeobject.h
3.12:Include/internal/pycore_warnings.h
#3.12:Include/internal/pycore_weakref.h

#3.12:Objects/typeobject.c
3.12:Include/internal/pycore_call.h
3.12:Include/internal/pycore_dict.h
3.12:Include/internal/pycore_long.h
3.12:Include/internal/pycore_memoryobject.h
3.12:Include/internal/pycore_object.h
)

SOURCE_FILES=(
Modules/_interpretersmodule.c
Modules/_interpqueuesmodule.c
Modules/_interpchannelsmodule.c
Modules/_interpreters_common.h

Python/crossinterp.c
Python/crossinterp_data_lookup.h
Python/crossinterp_exceptions.h

Python/interpconfig.c
Python/config_common.h

Python/lock.c
Python/parking_log.c

runtimebackports.c
3.12/Objects/typeobject.c
)

declare -rA FIXES=(
['interpreters_backport/interpreters/__init__.py']='
    add-fallback-import:_interpreters:interpreters_backport'
['interpreters_backport/interpreters/queues.py']='
    add-fallback-import:_interpqueues:interpreters_backport'
['interpreters_experimental/interpreters/channels.py']='
    add-fallback-import:_interpchannels:interpreters_experimental'

#['Python/parking_log.c']='
#    swap-bounded-literal:&tstate->state:_PyThreadState_GET_STATE(tstate);
#'

#['Include/internal/pycore_crossinterp.h']='
#    swap-bounded-literal:struct _xid {:struct _xid_new {;
#    #remove-macro:_PyCrossInterpreterData_INTERPID;
#    #remove-macro:_PyCrossInterpreterData_SET_FREE;
#    #remove-macro:_PyCrossInterpreterData_SET_NEW_OBJECT;
#    '
#['Include/internal/pycore_crossinterp_data_lookup.h']='
#    swap-bounded-literal:struct _xidregitem:struct _xidregitem_duplicate;
#    '

#['_interpretersmodule.c']='
#    swap-name:_PyInterpreterState_LookUpID:_PyInterpreterState_LookUpIDFixed'
#['crossinterp.c']='
#    swap-name:_PyInterpreterState_LookUpID:_PyInterpreterState_LookUpIDFixed'
#['']=''
)

test -n "
    @register('_interpretersmodule.c', '_xxsubinterpretersmodule.c')
    def fix__interpretersmodule_c(text):
        before, _, after = text.partition('module_clear(PyObject *mod)')
        before += 'module_clear(PyObject *mod)'
        text = before + after.replace(
            'module_state *state = get_module_state(mod);',
            textwrap.dedent('''\
            module_state *state = get_module_state(mod);

            PyInterpreterState *interp = PyInterpreterState_Get();
            PyStatus status = _PyXI_InitTypes(interp);
            if (PyStatus_Exception(status)) {
                _PyErr_SetFromPyStatus(status);
                return -1;
            }
            '''[4:]).rstrip(),
        )

        text = text.replace(
            'clear_module_state(state);',
            textwrap.dedent('''\
            clear_module_state(state);
            _PyXI_FiniTypes(PyInterpreterState_Get());
            '''[4:]).rstrip(),
            1,  # count
        )
        return text

    @register('pycore_crossinterp.h')
    def fix_pycore_crossinterp_h(text):
        # s/^struct _xid {/struct _xid_new {/
        text = text.replace('struct _xid {', 'struct _xid_new {')

        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterError;',
            textwrap.dedent('''\
            extern PyObject * _get_exctype(PyInterpreterState *, const char *);
            #define GET_EXC_TYPE(TYPE) \\
                _get_exctype(PyInterpreterState_Get(), #TYPE)
            #define PyExc_InterpreterError \\
                GET_EXC_TYPE(PyExc_InterpreterError)
            ''').rstrip(),
        )
        text = text.replace(
            'PyAPI_DATA(PyObject *) PyExc_InterpreterNotFoundError;',
            textwrap.dedent('''\
            #define PyExc_InterpreterNotFoundError \\
                GET_EXC_TYPE(PyExc_InterpreterNotFoundError)

            PyInterpreterState * _PyInterpreterState_LookUpIDFixed(int64_t);
            ''').rstrip(),
        )
        return text

    @register('pycore_typeobject.h')
    def fix_pycore_typeobject_h(text):
        text = text.replace(
            'PyAPI_FUNC(PyObject *) _PyType_GetModuleName(PyTypeObject *);',
            textwrap.dedent('''\
            #define _PyType_GetModuleName(cls) \\
                PyObject_GetAttrString((PyObject *)cls, '__module__')
            ''').rstrip(),
        )
        return text
"

# helpers

function warn() {
    >&2 echo "WARNING: $@"
}

function error() {
    >&2 echo "ERROR: $@"
}

function fail() {
    error "$@"
    exit 1
}

function value-in-array() {
    local value=$1
    shift
    local array=("$@")
    if [[ " ${array[*]} " =~ [[:space:]]${value}[[:space:]] ]]; then
        return 0;
    else
        return 1;
    fi
}

function clear-unknown-files() {
    local rootdir=$1
    shift
    local known=("$@")

    if [ -z "$rootdir" ]; then
        fail "missing rootdir arg"
    fi

    echo "-- $rootdir --"
    if [ -z "$known" ]; then
        rm -rf "$rootdir"/*
        return
    fi

    &>/dev/null pushd "$rootdir"
    local subdirs=()
    local relfile=
    for relfile in $(find . | sort --reverse); do
        relfile="${relfile:2}"
        if [ -d "$relfile" ]; then
            subdirs+=("$relfile")
        elif ! value-in-array "$relfile" "${known[@]}"; then
            echo "deleting unknown file ($rootdir/$relfile)"
            rm "$relfile"
        fi
    done
    for subdir in "${subdirs[@]}"; do
        rmdir --ignore-fail-on-non-empty "$subdir"
    done
    &>/dev/null popd
}


# Parse the CLI.

USAGE="update.sh [--dry-run] [--api|--local] [--pending REPO] [ref]"
HELP="USAGE: $USAGE"

req_ref=
pending_repo=
download_mode=
dryrun=

function parse-cli() {
    while [ $# -gt 0 ]; do
        local arg=$1
        shift
        case $arg in
            --help|-h)
                echo "$HELP"
                exit 0
                ;;
            --pending)
                pending_repo=$1
                shift
                ;;
            --api) download_mode='api';;
            --local) download_mode='local';;
            --dry-run) dryrun=$arg;;
            --) break;;
            --*)
                fail "unsupported option $arg"
                ;;
            *)
                if [ -z "$req_ref" ]; then
                    req_ref=$arg
                else
                    fail "unsupported arg $arg"
                fi
                ;;
        esac
    done
#    req_ref=$1
#    shift
#    if [ "$req_ref" = '--dry-run' ]; then
#        dryrun=$req_ref
#        req_ref=$1
#        shift
#    elif [ "$1" = '--dry-run' ]; then
#        dryrun=$1
#        shift
#    fi
#    if [ "$req_ref" = '--' ]; then
#        req_ref=''
#    elif [ "$1" = '--' ]; then
#        shift
#    fi
}

parse-cli "$@"


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
        fail "no last branch"
    fi
    branch=$requested
    version=$last_version
elif case "$requested" in .rev|.revision) true;; *) false;; esac; then
    requested=$last_revision
    branch=$last_branch
    if [ -z "$requested" ]; then
        fail "no last revision"
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
if [ ${#PENDING_FILES[@]} -gt 0 ]; then
    if [ -n "$pending_repo" ]; then
        echo "# pending:  $pending_repo"
    else
        echo "# pending:  ???"
    fi
fi
echo "####################"
echo

if [ -z "$revision" ]; then
    fail "failed to get revision"
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
clear-unknown-files "$SOURCE_ROOT"
clear-unknown-files "$ROOT_312/$SOURCE_ROOT"
clear-unknown-files "$UPSTREAM_ROOT"
clear-unknown-files "$PENDING_ROOT" "${PENDING_FILES[@]}"


# Download the files.

downloaded=()
pending=()

CPYTHON_UPSTREAM='https://github.com/python/cpython'
CPYTHON_DOWNLOAD='https://raw.githubusercontent.com/python/cpython'
CPYTHON_REPO='build/cpython-local'

function refresh-local-repo() {
    if [ -e "$CPYTHON_REPO" ]; then
        (set -x
        git -C "$CPYTHON_REPO" fetch --tags origin
        )
    else
        mkdir -p $(dirname "$CPYTHON_REPO")
        (set -x
        git clone "$CPYTHON_UPSTREAM" "$CPYTHON_REPO"
        )
    fi
}

function resolve-upstream() {
    local relfile=$1
    local upstream=$relfile
    if case "$upstream" in 3.12:*) true;; *) false;; esac; then
        upstream=${upstream#*:}
    fi
    # This special case goes away for the main branch once PEP 734 is done.
    if case "$upstream" in interpreters/*) true;; *) false;; esac; then
        upstream="test/support/$upstream"
    fi
    if case "$upstream" in *.py) true;; *) false;; esac; then
        upstream="Lib/$upstream"
    fi
    echo "$upstream"
}

function download-file-gh-api() {
    local upstream=$1
    local outfile=$2
    local ref=$3
    local url="${CPYTHON_DOWNLOAD}/$ref/$upstream"

    (set -x
    curl --fail -o "$outfile" "$url"
    )
}

function download-file-local() {
    local upstream=$1
    local outfile=$2
    local ref=$3

    (set -x
    git -C "$CPYTHON_REPO" show "$ref:$upstream" > "$outfile"
    )
}

function download-file-default() {
    download-file-local "$@"
    # XXX Fall back to the API?
}

function download-files() {
    local revision=$1
    local mode=$2

    local do_download=
    case "$mode" in
        "") do_download=download-file-default;;
        api) do_download=download-file-gh-api;;
        local)
            refresh-local-repo
            do_download=download-file-local
            ;;
        *) fail "unsupported download mode $mode";;
    esac

    local relfile=
    for relfile in "${UPSTREAM_FILES[@]}"; do
        local upstream=$(resolve-upstream $relfile)
        local outfile="$UPSTREAM_ROOT/$upstream"
        local ref=$revision
        if case "$relfile" in 3.12:*) true;; *) false;; esac; then
            outfile="$UPSTREAM_ROOT/3.12/$upstream"
            ref='origin/3.12'
        fi
        local pending=false
        if value-in-array "$upstream" "${PENDING_FILES[@]}"; then
            pending=true
        fi

        echo "# ++ $relfile"
        echo "# ++++++++++++++++++++++++++++++++++++++"

        local rc=0
        if $pending && [ -n "$pending_repo" ]; then
            echo "# pending; skipping download"
            outfile='<pending>'
        else
            mkdir -p $(dirname $outfile)
            $do_download "$upstream" "$outfile" "$ref"
            rc=$?
            if [ $rc -ne 0 ] && $pending; then
                warn "pending file is not upstream yet"
                rc=0
                outfile='<pending>'
            fi
        fi

        echo "# ++++++++++++++++++++++++++++++++++++++"
        if [ $rc -ne 0 ]; then
            echo
            fail 'download failed'
        fi

        downloaded+=("$outfile")
    done
}

echo "# downloading from upstream"
download-files "$revision" "$download_mode"

echo
echo "# updating metadata"
echo -n $revision > $UPSTREAM_ROOT/CPYTHON_REVISION
echo -n "$branch" > $UPSTREAM_ROOT/CPYTHON_BRANCH
echo -n "$version" > $UPSTREAM_ROOT/CPYTHON_VERSION

function copy-pending-files() {
    local reporoot=$1

    local relfile=
    for relfile in "${PENDING_FILES[@]}"; do
        local upstream="$reporoot/$relfile"
        local outfile="$PENDING_ROOT/$relfile"
        mkdir -p $(dirname $outfile)
        (set -x
        cp "$upstream" "$outfile"
        )
        pending+=("$outfile")
    done
}

if [ ${#PENDING_FILES[@]} -gt 0 ]; then
    echo
    echo '# "downloading" pending upstream files'
    if [ -z "$pending_repo" ]; then
        warn "no pending repo provided; using upstream as-is"
    else
        copy-pending-files "$pending_repo"
    fi
fi


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


# Create dummy files.

echo
echo '# creating dummy files'
for relfile in "${DUMMY_FILES[@]}"; do
    dest="$SOURCE_ROOT/$relfile"
    mkdir -p $(dirname $dest)
    (set -x
    touch "$dest"
    )
done


# Apply upstream files.

function resolve-upstream-copy() {
    local src=$1
    local destroot=$2
    local relfile=$3
    local dest=
    if case "$src" in */channels.py) true;; *) false;; esac; then
        dest="interpreters_experimental/$relfile"
    elif case "$src" in *.py) true;; *) false;; esac; then
        dest="interpreters_backport/$relfile"
    elif value-in-array "$relfile" "${SOURCE_FILES[@]}"; then
        if case "$src" in */Modules/*) true;; *) false;; esac; then
            dest=$(basename ${relfile})
        else
            dest=$relfile
        fi
    elif case "$src" in */Modules/*) true;; *) false;; esac; then
#        dest="$(basename ${relfile})"
        fail "$src should have already been handled"
    elif case "$src" in */Python/crossinterp*) true;; *) false;; esac; then
#        dest="$(basename ${relfile})"
        fail "$src should have already been handled"
    elif case "$src" in */Include/*) true;; *) false;; esac; then
        dest=$relfile
    elif case "$src" in *.c|*.h) true;; *) false;; esac; then
        dest=$relfile
    else
        fail "unsupported upstream file $src"
    fi
    echo "$destroot/$dest"
}

echo
echo "# copying upstream files"
for i in ${!downloaded[@]}; do
    src=${downloaded[i]}
    upstream=${UPSTREAM_FILES[$i]}
    if [ "$src" = '<pending>' ]; then
        echo "# pending: $upstream"
        continue
    fi
    if case "$upstream" in 3.12:*) true;; *) false;; esac; then
        upstream="3.12/${upstream#*:}"
    fi
    dest=$(resolve-upstream-copy "$src" "$SOURCE_ROOT" "$upstream")
    mkdir -p $(dirname $dest)
    (set -x
    cp -r "$src" "$dest"
    )
done

if [ ${#pending[@]} -gt 0 ]; then
    echo
    echo "# copying pending upstream files"
    for i in ${!pending[@]}; do
        src=${pending[i]}
        relfile=${PENDING_FILES[$i]}
        dest=$(resolve-upstream-copy "$src" "$SOURCE_ROOT" "$relfile")
        mkdir -p $(dirname $dest)
        (set -x
        cp -r "$src" "$dest"
        )
    done
fi

echo
echo "# Applying fixes to copied upstream files"
for relfile in ${!FIXES[@]}; do
    (set -x
    python3 scripts/fix-source.py "${FIXES[$relfile]}" "$SOURCE_ROOT/$relfile"
    )
done


# Move files into the 3.12/src tree.

function fix-up-source-trees() {
    local rootdir=$SOURCE_ROOT
    local destdir="$ROOT_312/$SOURCE_ROOT"

    &>/dev/null pushd "$rootdir"
    local subdirs=()
    local relfile=
    for relfile in $(find . | sort --reverse); do
        relfile="${relfile:2}"
        if [ -z "$relfile" ]; then
            continue
        fi
        if [ -d "$relfile" ]; then
            subdirs+=("$relfile")
        else
            local dest="../$destdir/$relfile"
            mkdir -p $(dirname "$dest")
            if case "$relfile" in *.py) true;; *) false;; esac; then
                (set -x
                cp "$relfile" "$dest"
                )
            else
                (set -x
                mv "$relfile" "$dest"
                )
            fi
        fi
    done
    for subdir in "${subdirs[@]}"; do
        rmdir --ignore-fail-on-non-empty "$subdir"
    done
    &>/dev/null popd
}

echo
echo "# Fixing up source trees"
fix-up-source-trees


# Update the repo.

git add $SOURCE_ROOT
git add "$ROOT_312/$SOURCE_ROOT"
git add $UPSTREAM_ROOT
git add $PENDING_ROOT
