# bash script helpers


#######################################
# general

function log() {
    1>&2 echo $@
}

function run() {
    log "+ $@"
    1>&2 "$@"
}

function utcnow() {
    date --utc +'%Y%m%d-%H%M%S'
}


#######################################
# Python version

function match-cpython-version() {
    local verstr=
    local quiet=false
    local bugfix=true
    for arg in "$@"; do
        case "$arg" in
            "")
                log "got unexpected empty arg"
                return 1
                ;;
            --quiet|-q)
                quiet=true
                ;;
            --show-feature|-F)
                bugfix=false
                ;;
            *)
                if [ -z "$verstr" ]; then
                    verstr=$arg
                else
                    log "got unsupported arg $arg"
                    return 1
                fi
        esac
    done

    local regex='\b\d+\.\d+(.\d+)?\b'
    if ! $bugfix; then
        regex='\b\d+\.\d+(?=.\d+)?\b'
    fi

    local found=
    if [ -z "$verstr" -o "$verstr" = '-' ]; then
        log "+ grep -o -P $regex"
        found=$(grep -o -P "$regex")
    else
        log "+ echo $verstr | grep -o -P $regex"
        found=$(echo "$verstr" | grep -o -P "$regex")
    fi
    if [ $? -ne 0 ]; then
        return 1
    fi
    if [ "$(echo "$found" | wc -l)" -gt 1 ]; then
        log "ambiguous multi-line verstr arg"
        return 1
    fi

    if ! $quiet; then
        echo "$found"
    fi
    return 0
}

function get-cpython-version() {
    local python=$1
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    fi

    local verstr=$(2>&1 "$python" --version)
    echo "$verstr" | grep -o -P '(?<=^Python )\d+\.\d+.\d+$'
}

function resolve-cpython-version() {
    local version=$1
    local python=$2

    if [ -z "$python" ]; then
        if [ -z "$version" ]; then
            log "missing version arg"
            return 1
        fi

        if [ -e "$version" ]; then
            python=version
            version=
        fi
    fi

    if [ -z "$version" ]; then
        get-cpython-version "$python"
        return $?
    fi

    local actual=$(match-cpython-version -F "$version")
    if [ -z "$actual" ]; then
        log "bad version arg $version"
        return 1
    fi
    version=$actual

    if [ -n "$python" ]; then
        local actualversion=$(get-cpython-version "$python")
        if [ -n "$actualversion" -a "$actualversion" != "$version" ]; then
            log "version mismatch ($version != $actualversion)"
            return 1
        fi
    fi

    echo "$version"
    return 0
}


#######################################
# $PATH

function check-python-on-path() {
    local executable=$1
    local version=$2
    local found=

    log "looking for ${executable} on \$PATH..."
    found=$(which "$executable")
    if [ -z "$found" ]; then
        log "...not found"
        return 1
    else
        log "...checking version..."
        local verstr=$(2>&1 "$found" --version)
        if echo $verstr | grep -P "^Python ${version}(\.\d+)?$"; then
            log "...okay"
        else
            log "...wrong version ($verstr)"
            return 1
        fi
    fi
    echo "$found"
    return 0
}

function find-cpython-on-path() {
    local version=$1
    local found=

    if [ -e "$version" ]; then
        log 'find-cpython: missing version arg'
        return 1
    fi

    found=$(check-python-on-path python${version} $version)
    if [ -z "$found" ]; then
        found=$(check-python-on-path python3 $version)
        if [ -z "$found" ]; then
            found=$(check-python-on-path python $version)
            if [ -z "$found" ]; then
                log "Python $version not found"
                return 1
            fi
        fi
    fi
    echo $found
    return 0
}


#######################################
# git data

function match-git-branch() {
    local branch=$1

    if git check-ref-format --allow-onelevel "$branch"; then
        echo $branch
        return 0
    fi
    # XXX Extract from text?
    log "invalid branch name $branch"
    return 1
}

function match-git-revision() {
    local grepargs='-o'
    local quiet=false
    local strict=false
    while [ 1 -eq 1 ]; do
        if [ "$1" = '-q' ]; then
#            grepargs="$grepargs -q"
            quiet=true
        elif [ "$1" = '--strict' ]; then
            strict=true
        else
            break
        fi
        shift
    done
    local rev=$1

    local regex='\b([a-f0-9]{6,40}|[A-F0-9]{6,40})\b'
    if $strict; then
        regex='\b([a-f0-9]{40}|[A-F0-9]{40})\b'
    fi
    grepargs="$grepargs -P"
    if [ -z "$rev" -o "$rev" = '-' ]; then
        grep $grepargs "$regex"
    else
        echo $rev | grep $grepargs "$regex"
    fi
}


#######################################
# remote repo

GH_API=https://api.github.com/repos

function gh-normalize-revision() {
    local org=$1
    local repo=$2
    local ref=$3

    log "+ curl -s $GH_API/$org/$repo/commits/$ref | jq --raw-output .sha"
    local rev=$(curl -s $GH_API/$org/$repo/commits/$ref | jq --raw-output .sha)
    if [ -z "$rev" -o "$rev" = 'null' ]; then
        log "unknown revision $ref"
        return 1
    fi
    echo ${rev^^}  # upper-case
    return 0
}

function gh-look-up-revision() {
    local org=$1
    local repo=$2
    local ref=$3

    local rev=$(match-git-revision "$ref")
    if [ -n "$rev" ]; then
        ref=$rev
    else
        local branch=$(match-git-branch "$ref")
        if [ -z "$branch" ]; then
            log "invalid revision or branch $ref"
            return 1
        fi
        ref=branch
    fi

    rev=$(gh-normalize-revision "$org" "$repo" "$ref")
    if [ $? -ne 0 -o -z "$rev" ]; then
        log "revision or branch $ref not found"
        return 1
    fi

    echo "$rev"
    return 0
}


#######################################
# cpython git revisions

function _resolve-cpython-revision() {
    local ref=$1

    local rev=$(match-git-revision --strict "$ref")
    if [ -n "$rev" ]; then
        rev=${rev^^}  # upper-case
    else
        # Look up the full revision.
        rev=$(gh-look-up-revision python cpython "$ref")
        if [ -z "$rev" ]; then
            return 1
        fi
    fi
    echo "$rev"
    return 0
}

function normalize-cpython-revision() {
    local rev=$1
    if [ -z "$rev" ]; then
        log "missing revision arg"
        return 1
    fi
    if [ "$(echo "$rev" | wc -l)" -gt 1 ]; then
        log "got multiline rev arg"
        return 1
    fi

    local rev=$(match-git-revision "$rev")
    if [ -z "$rev" ]; then
        log "invalid revision $rev"
        return 1
    fi
    _resolve-cpython-revision $rev
}

function get-cpython-revision() {
    local python=$1

    local verstr=$("$python" -VV)
    local rev=$(match-git-revision "$verstr")
    if [ -z "$rev" ]; then
        log "could not determine revision"
        return 1
    fi
    _resolve-cpython-revision $rev
}

function resolve-cpython-revision() {
    local revision=$1
    local python=$2

    if [ -z "$python" ]; then
        if [ -z "$revision" ]; then
            log "missing revision arg"
            return 1
        fi

        if [ -e "$revision" ]; then
            python=revision
            revision=
        fi
    fi

    if [ -z "$revision" ]; then
        get-cpython-revision "$python"
        return
    fi

    local actual=$(match-git-revision "$revision")
    if [ -z "$actual" ]; then
        log "bad revision arg $revision"
        return 1
    fi
    revision=$actual

    if [ -n "$python" ]; then
        local actualrevision=$(get-cpython-revision "$python")
        if [ -n "$actualrevision" -a "$actualrevision" != "$revision" ]; then
            log "revision mismatch ($revision != $actualrevision)"
            return 1
        fi
    fi

    echo "$revision"
    return 0
}


#######################################
# venv

function resolve-venv-python() {
    local venvroot=$1
    local version=$2
    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    fi

    local venvexe="$(realpath "$venvroot")/bin/python"
    local exists=
    if [ -e "$venvexe" ]; then
        exists=$venvexe
    fi
    if [ -n "$version" ]; then
        venvexe="${venvexe}${version}"
        if [ -e "$venvexe" ]; then
            exists=$venvexe
        fi
    fi
    if [ -n "$exists" ]; then
        venvexe=$exists
    fi

    echo $venvexe
    return 0
}

function get-original-python-from-venv() {
    local venvroot=$1
    local version=$2

    local venvexe=$(resolve-venv-python "$venvroot" $version)
    if [ -z "$venvexe" -o ! -e "$venvexe" ]; then
        return 1
    fi
    # Follow the symlink.
    realpath "$venvexe"
}

function _validate-venv-python() {
    local venvexe=$1
    local python=$2
    local version=$3
    local revision=$4

    if [ -n "$python" ]; then
        #local actualexe=$(get-original-python-from-venv "$venvexe")
        local actualexe=$(realpath "$venvexe")
        local actualpython=$(realpath "$python")
        if [ "$actualexe" = "$actualpython" ]; then
            return 0
        fi

        version=$(resolve-cpython-version "$version" "$python")
        revision=$(resolve-cpython-revision "$revision" "$python")
    elif [ -n "$revision" ]; then
        revision=$(normalize-cpython-revision "$revision")
        if [ -z "$revision" ]; then
            return 1
        fi
    fi

    # Check the version.
    if [ -n "$version" ]; then
        local actualversion=$(get-cpython-version "$venvexe")
        if [ -z "$actualversion" ]; then
            log "actual version not known (ignoring)"
        elif [ "$actualversion" != "$version" ]; then
            log "version mismatch ($actualversion != $version)"
            return 1
        fi
    fi

    # Check the revision.
    if [ -n "$revision" ]; then
        local actualrev=$(get-cpython-revision "$venvexe")
        if [ -z "$actualrev" ]; then
            log "actual revision not known (ignoring)"
        elif [ "$actualrev" != "$revision" ]; then
            log "revision mismatch ($actualrev != $revision)"
            return 1
        fi
    fi

    return 0
}

function _validate-venv-other() {
    # XXX Check other stuff?
    return 0
}

function validate-venv() {
    local venvroot=$1
    local python=$2
    local version=$3
    local revision=$4

    if [ -n "$python" ]; then
        if match-cpython-version -q "$python"; then
            version=python
            revision=version
            python=
        fi
    fi

    if [ ! -d "$venvroot" ]; then
        log "expected directory at $venvroot"
        return 1
    fi

    local venvexe=$(resolve-venv-python "$venvroot" "$version")
    if [ -z "$venvexe" ]; then
        return 1
    fi

    # Check the executable.
    if ! _validate-venv-python "$venvexe" "$python" "$version" "$revision"; then
        return 1
    fi

    # Check everything else.
    if ! _validate-venv-other "$venvroot"; then
        return 1
    fi

    return 0
}

function ensure-venv() {
    local venvroot=$1
    local python=$2
    local version=$3
    local revision=$4
    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    fi
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    elif [ ! -e "$python" ]; then
        log "bad python arg"
        return 1
    fi

    if [ ! -e "$venvroot" ]; then
        log "creating new venv at $venvroot"
        (set -x
        "$python" -m venv "$venvroot"
        )
        return
    fi

    if [ ! -d "$venvroot" ]; then
        log "expected directory at $venvroot"
        return 1
    fi

    log "found existing venv at $venvroot"
    validate-venv "$venvroot" "$python" "$version" "$revision"

    return 0
}

function ensure-clean-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    local revision=$4
    if [ -z "$workdir" ]; then
        log "missing workdir arg"
        return 1
    fi
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    fi

    version=$(resolve-cpython-version "$version" "$python")
    if [ -z "$version" ]; then
        return 1
    fi

    local venvroot="$workdir/venv_${version//./}"
    local existing=false
    if [ -d "$venvroot" ]; then
        existing=true
    fi

    if ! ensure-venv "$venvroot" "$python" $version $revision; then
        return 1
    fi

    if existing; then
        (set -x
        "$python" -m venv --clear "$venvroot"
        )
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi

    resolve-venv-python "$venvroot" $version
}


#######################################
# local repo

CPYTHON_UPSTREAM=https://github.com/python/cpython

function ensure-cpython-source() {
    local version=$1
    local srcdir=$2
    if [ -e $srcdir ]; then
        log "found local clone: $srcdir"
        log "updating..."
        if ! run git -C "$srcdir" checkout $version; then
            return 1
        elif ! run git -C "$srcdir" pull; then
            return 1
        fi
    else
        log "cloning CPython locally..."
        if ! run git clone --branch $version $CPYTHON_UPSTREAM "$srcdir"; then
            return 1
        elif ! run git -C "$srcdir" checkout $version; then
            return 1
        fi
    fi
    return 0
}


#######################################
# custom build/install

function build-cpython() {
    local debug=$BUILD_DEBUG
    if [ "$1" = '--debug' ]; then
        debug=1
        shift
    elif [ "$1" = '--no-debug' ]; then
        debug=0
        shift
    elif [ -z "$debug" ]; then
        debug=0
    fi
    local srcdir=$1
    local builddir=$2
    local installdir=$3
    if [ -z "$installdir" ]; then
        log "missing installdir (arg #3)"
        return 1
    fi
    local exitcode=0

    local config_args=(
        "--prefix=$installdir"
    )
    if [ "$debug" -eq 0 ]; then
        log "building in $builddir..."
    else
        log "building (debug) in $builddir..."
        config_cmd+=(
            "--with-pydebug"
            "CFLAGS=-O0"
        )
    fi

    1>&2 mkdir -p "$builddir"
    &>/dev/null pushd "$builddir"
    if ! run $srcdir/configure ${config_args[@]}; then
        exitcode=1
    elif ! run make -j8; then
        exitcode=1
    fi
    &>/dev/null popd
    return $exitcode
}

function version-from-built-cpython() {
    local builddir=$1
    grep '^VERSION=' "$builddir/python-config" | awk -F'"' '{print $2}'
}

function installdir-from-built=cpython() {
    local builddir=$1
    grep '^prefix=' "$builddir/python-config" | awk -F'"' '{print $2}'
}

function resolve-installed-cpython() {
    local installdir=$1
    local version=$2
    echo "$installdir/bin/python${version}"
}

function install-built-cpython() {
    local builddir=$1
    local installdir=$2
    local version=$3
    if [ -z "$installdir" ]; then
        installdir=$(installdir-from-built-cpython "$builddir")
        if [ -z "$installdir" ]; then
            log "could not determine installdir (did you already build?)"
            return 1
        fi
    fi
    if [ -z "$version" ]; then
        version=$(version-from-built-cpython "$builddir")
        if [ -z "$version" ]; then
            log "could not determine version (did you already build?)"
            return 1
        fi
    fi
    local executable=$(resolve-installed-cpython "$installdir" $version)

    log "installing..."
    &>/dev/null pushd "$builddir"
    if ! run make install; then
        &>/dev/null popd
        return 1
    elif [ ! -e "$executable" ]; then
        log "something went wrong ($exectuable not found)"
        &>/dev/null popd
        return 1
    fi
    &>/dev/null popd
    echo "$executable"
    return 0
}


#######################################
# local build project

function resolve-projroot() {
    local workdir=$1
    if [ -z "$workdir" ]; then
        workdir="."
    fi
    echo "$1/cpython"
}

function resolve-local-srcdir() {
    # We expect .../cpython
    local projdir=$1
    echo "$projdir/source"
}

function resolve-local-builddir() {
    local version=$1
    # We expect .../cpython
    local projdir=$2
    echo "$projdir/build_${version}"
}

function resolve-local-installdir() {
    local version=$1
    # We expect .../cpython
    local projdir=$2
    echo "$projdir/installed_${version}"
}

function version-from-local-dir() {
    local name=$(basename "$1")
    echo $name | grep -P -o '(?<=^build_|^install_)\d+\.\d+'
}

function prep-local-project() {
    local version=$1
    # We expect .../cpython
    local projdir=$2
    local srcdir=$(resolve-local-srcdir "$projdir")
    if [ -z "$srcdir" ]; then
        return 1
    fi

    1>&2 mkdir -p "$projdir"
    ensure-cpython-source $version "$srcdir"
}

function build-local-cpython() {
    local version=$1
    # We expect .../cpython
    local projdir=$2
    local srcdir=$(resolve-local-srcdir "$projdir")
    local builddir=$(resolve-local-builddir $version "$projdir")
    local installdir=$(resolve-local-installdir $version "$projdir")
    if [ -z "$srcdir" -o -z "$builddir" -o -z "$installdir" ]; then
        return 1
    fi

    build-cpython "$srcdir" "$builddir" "$installdir"
}

function install-local-cpython() {
    local version=$1
    # We expect .../cpython
    local projdir=$2
    local builddir=$(resolve-local-builddir $version "$projdir")
    local installdir=$(resolve-local-installdir $version "$projdir")
    if [ -z "$builddir" -o -z "$installdir" ]; then
        return 1
    fi

    install-built-cpython "$builddir" "$installdir" $version
}

function find-local-cpython() {
    local version=$1
    local workdir=$2
    local projdir=$(resolve-projroot "$workdir")
    local installdir=$(resolve-local-installdir $version "$projdir")
    local executable=$(resolve-installed-cpython "$installdir" $version)
    if [ -z "$projdir" -o -z "$installdir" -o -z "$executable" ]; then
        return 1
    fi

    if [ ! -e $executable ]; then
        return 1
    fi
    echo $executable
    return 0
}

function build-and-install-local-cpython() {
    local version=$1
    local workdir=$2
    local projdir=$(resolve-projroot "$workdir")
    if [ -z "$projdir" ]; then
        return 1
    fi

    if ! prep-local-project $version "$projdir"; then
        return 1;
    elif ! build-local-cpython $version "$projdir"; then
        return 1
    fi
    install-local-cpython $version "$projdir"
}


#######################################

function ensure-cpython() {
    local version=$1
    local workdir=$(realpath $2)
    local found=

    found=$(find-cpython-on-path $version)
    if [ -z "$found" ]; then
        log "falling back to a locally built python${version}..."
        found=$(find-local-cpython $version "$workdir")
        if [ -n "$found" ]; then
            log "found locally built: $found"
        else
            found=$(build-and-install-local-cpython $version $workdir)
            if [ -z "$found" ]; then
                return 1
            fi
        fi
    fi
    if [ -z "$found" ]; then
        return 1
    fi
    echo $found
    return 0
}
