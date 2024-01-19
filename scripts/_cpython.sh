
if [ -z "$_scripts_cpython_sh" ]; then
_scripts_cpython_sh=1


test -n "$SCRIPTS_DIR" || (1>&2 echo '$SCRIPTS_DIR not set' && exit 1)
source $SCRIPTS_DIR/_utils.sh


#######################################
# git revisions

function _cpython-look-up-revision() {
    local ref=$1

    # Look up the full revision.
    local rev=$(gh-look-up-revision python cpython "$ref")
    if [ -z "$rev" ]; then
        log "unknown ref $ref"
        return 1
    fi

    echo "$rev"
    return 0
}

function cpython-normalize-revision() {
    local rev=$1

    normalize-git-revision "$rev" _cpython-look-up-revision
}

function cpython-get-revision() {
    local python=$1
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    elif [ ! -e "$python" ]; then
        log "bad python arg '$python'"
        return 1
    fi

    local verstr=$("$python" -VV)
    local rev=$(match-git-revision "$verstr")
    if [ -z "$rev" ]; then
        log "could not determine revision"
        return 1
    fi
    normalize-git-revision "$rev" _cpython-look-up-revision
}

function cpython-resolve-revision() {
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
        cpython-get-revision "$python"
        return
    elif [ -z "$python" ]; then
        cpython-normalize-revision "$revision"
        return
    fi

    revision=$(cpython-normalize-revision "$revision")
    if [ -z "$revision" ]; then
        return 1
    fi
    local actual=$(cpython-get-revision "$python")
    if [ -z "$actual" ]; then
        log "actual revision not known (ignoring)"
    elif [ "$actual" != "$revision" ]; then
        log "revision mismatch ($revision != $actual)"
        return 1
    fi

    echo "$revision"
    return 0
}


#######################################
# venv

function _cpython-validate-venv-revision() {
    local venvexe=$1
    local revision=$2
    local python=$3

    if [ -z "$revision" -a -n "$python" ]; then
        revision=$(cpython-get-revision "$python")
        if [ -z "$revision" ]; then
            log "actual revision not known (ignoring)"
            return 0
        fi
    else
        revision=$(cpython-resolve-revision "$revision" "$python")
        if [ -z "$revision" ]; then
            return 1
        fi
    fi

    local actualrev=$("cpython-get-revision" "$venvexe")
    if [ -z "$actualrev" ]; then
        log "actual revision not known (ignoring)"
    elif [ "$actualrev" != "$revision" ]; then
        log "revision mismatch ($actualrev != $revision)"
        return 1
    fi

    return 0
}

function cpython-validate-venv() {
    local venvroot=$1
    local python=$2
    local version=$3
    local revision=$4

    if ! validate-venv "$venvroot" "$python" "$version"; then
        return 1
    fi

    # Check the revision.
    if [ -n "$python" -o -n "$revision" ]; then
        local venvexe=$(resolve-venv-python "$venvroot" "$version")
        if [ -z "$venvexe" ]; then
            return 1
        fi
        if ! _cpython-validate-venv-revision "$venvexe" "$revision" "$python"; then
            return 1
        fi
    fi

    return 0
}

function cpython-ensure-venv() {
    local venvroot=$1
    local python=$2
    local version=$3
    local revision=$4

    if ! ensure-venv "$venvroot" "$python" "$version"; then
        return 1;
    fi

    # Check the revision.
    if [ -n "$revision" -o -n "$python" ]; then
        local venvexe=$(resolve-venv-python "$venvroot" "$version")
        if [ -z "$venvexe" ]; then
            return 1
        fi
        if ! _cpython-validate-venv-revision "$venvexe" "$revision" "$python"; then
            return 1
        fi
    fi

    return 0
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


# END $_scripts_cpython_sh
fi

# vim: set filetype=sh :
