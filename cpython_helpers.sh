
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
# venv

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

	local venv_root="$workdir/venv_${version//./}"
	if [ ! -e "$venv_root" ]; then
	    (set -x
	    "$python" -m venv "$venv_root"
	    )
	else
	    (set -x
	    "$python" -m venv --clear "$venv_root"
	    )
	fi
    if [ $? -ne 0 ]; then
        return 1
    fi
	echo $venv_root/bin/python$version
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
