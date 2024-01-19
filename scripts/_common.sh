
if [ -z "$_scripts_common_sh" ]; then
_scripts_common_sh=1


test -n "$SCRIPTS_DIR" || (1>&2 echo '$SCRIPTS_DIR not set' && exit 1)
source $SCRIPTS_DIR/_utils.sh
source $SCRIPTS_DIR/_cpython.sh


#######################################
# "matching" venvs

function resolve-matching-base-venv() {
    local workdir=$1
    local version=$2
    if [ -z "$version" ]; then
        log "missing version arg"
        return 1
    fi

    local base="venv_${version//./}"
    if [ -n "$workdir" ]; then
        base="$workdir/$base"
    fi
    echo "$base"
    return 0
}

function resolve-matching-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    version=$(resolve-python-version "$version" "$python")
    local revision=$4
    revision=$(cpython-resolve-revision "$revision" "$python")

    local base=$(resolve-matching-base-venv "$workdir" $version)
    local venvroot=

    # a system-installed Python
    local spython=
	if [ -n "$python" ]; then
	    spython=$(echo "$python" | grep -P -q '^python(\d+?)?(?=\.exe$|$)')
	fi
    if [ -n "$spython" ]; then
        # The revision, if any, is ignored.
        venvroot="${base}_${spython}"
    # a Python with an unknown revision
    elif [ -z "$revision" ]; then
        venvroot=$base
    # a Python with a known revision
    else
        venvroot="${base}_${revision}"
    fi

    echo "$venvroot"
    return 0
}

function find-matching-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    local revision=$4

    if [ -z "$workdir" ]; then
        log "missing workdir arg"
        return 1
    fi
    version=$(resolve-python-version "$version" "$python")
    if [ -z "$version" ]; then
        return 1
    fi

    local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
    if [ -z "$venvroot" ]; then
        return 1
    fi

    if [ ! -e "$venvroot" ]; then
        return 0
    elif ! cpython-validate-venv "$venvroot" "$python" "$version" "$revision"; then
        return 1
    fi

    resolve-venv-python "$venvroot" "$version"
}

function _set-base-matching-venv() {
    local venvroot=$1
    local workdir=$2
    local version=$3

    local link=$(resolve-matching-base-venv "$workdir" $version)
    if [ -z "$link" ]; then
        return 1
    fi
    if [ "$link" = "$venvroot" ]; then
        if [ ! -d "$venvroot" ]; then
            (set -x
            rm "$link"
            )
        fi
        return 0
    fi

    if [ -d "$link" ]; then
        (set -x
        rm -r "$link"
        )
    elif [ -e "$link" ]; then
        (set -x
        rm "$link"
        )
    fi
    (set -x
    ln -s "$venvroot" "$link"
    )
}

function bind-matching-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    local revision=$4

    local venvexe=$(find-matching-venv "$workdir" "$python" "$version" "$revision")
    if [ $? -ne 0 ]; then
        return 0
    elif [ -z "$venvexe" ]; then
        return 1
    fi

    local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
    if ! _set-base-matching-venv "$venvroot" "$workdir" "$version"; then
        return 1
    fi
    echo "$venvexe"
    return 0
}

function create-matching-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    local revision=$4

    if [ -z "$workdir" ]; then
        log "missing workdir arg"
        return 1
    fi
    version=$(resolve-python-version "$version" "$python")
    if [ -z "$version" ]; then
        return 1
    fi

    local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
    if [ -z "$venvroot" ]; then
        return 1
    fi

    if [ -e "$venvroot" ]; then
        log "venv already exists: $venvroot"
        cpython-validate-venv "$venvroot" "$python" "$version" "$revision"
        return 1
    fi

    if ! create-venv "$venvroot" "$python" "$version"; then
        return 1
    fi

    if ! _set-base-matching-venv "$venvroot" "$workdir" "$version"; then
        return 1
    fi

    resolve-venv-python "$venvroot" "$version"
}

function clear-matching-venv() {
    local workdir=$1
    local python=$2
    local version=$3
    local revision=$4

    local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
    if [ -z "$venvroot" ]; then
        return 1
    fi

    if [ ! -e "$venvroot" ]; then
        log "clear: no venv at $venvroot" 
    elif ! &>/dev/null cpython-validate-venv "$venvroot" "$python" "$version" "$revision"; then
        log "clear: invalid venv at $venvroot" 
        if [ -d "$venvroot" ]; then
            rm -r "$venvroot"
        else
            rm -e "$venvroot"
        fi
    else
        (set -x
        "$python" -m venv --clear "$venvroot"
        )
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi

    return 0
}

#function _ensure-matching-venv() {
#    local workdir=$1
#    local python=$2
#    local version=$3
#    local revision=$4
#    local clean=$5
#    if [ -z "$workdir" ]; then
#        log "missing workdir arg"
#        return 1
#    fi
#    if [ -z "$python" ]; then
#        log "missing python arg"
#        return 1
#    elif [ ! -e "$python" ]; then
#        log "bad python arg"
#        return 1
#    fi
#
#    version=$(resolve-python-version "$version" "$python")
#    if [ -z "$version" ]; then
#        return 1
#    fi
#
#    local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
#    local existing=false
#    if [ -L "$venvroot" ]; then
#        rm "$venvroot"
#    elif [ -d "$venvroot" ]; then
#        existing=true
#    fi
#
#    if ! ensure-venv "$venvroot" "$python" $version $revision; then
#        return 1
#    fi
#
#    if [ -n "$clean" ]; then
#        if $existing; then
#            (set -x
#            "$python" -m venv --clear "$venvroot"
#            )
#            if [ $? -ne 0 ]; then
#                return 1
#            fi
#        fi
#    fi
#
#    local link=$(resolve-matching-base-venv "$workdir" $version)
#    if [ "$venvroot" != "$link" ]; then
#        (set -x
#        rm -rf "$link"
#        ln -s "$venvroot" "$link"
#        )
#    fi
#
#    resolve-venv-python "$venvroot" $version
#}
#
#function ensure-matching-venv() {
#    local workdir=$1
#    local python=$2
#    local version=$3
#    local revision=$4
#    if [ -z "$workdir" ]; then
#        log "missing workdir arg"
#        return 1
#    fi
#    if [ -z "$python" ]; then
#        log "missing python arg"
#        return 1
#    elif [ ! -e "$python" ]; then
#        log "bad python arg"
#        return 1
#    fi
#
#    _ensure-matching-venv "$workdir" "$python" "$version" "$revision"
#}
#
#function ensure-clean-matching-venv() {
#    local workdir=$1
#    local python=$2
#    local version=$3
#    local revision=$4
#    if [ -z "$workdir" ]; then
#        log "missing workdir arg"
#        return 1
#    fi
#    if [ -z "$python" ]; then
#        log "missing python arg"
#        return 1
#    fi
#
#    _ensure-matching-venv "$workdir" "$python" "$version" "$revision" --clean
#}


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
    local workdir=$1
    local version=$2
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
    local workdir=$2
    local version=$1

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
# mini-scripts

function script-find-cpython() {
    local python=$1
    local workdir=$2
    local version=$3

    log
    log "###################################################"
    log "# making sure \$PYTHON_312 is set"
    log "###################################################"
    log

    if [ -n "$workdir" ]; then
        if ! isabspath "$workdir"; then
            log "got relative path for workdir: $workdir"
            exit 1
        fi
    fi
    if [ -n "$version" ]; then
        version=$(match-python-version --without-bugfix "$version")
        if [ -z "$version" ]; then
            exit 1
        fi
    fi

    if [ -z "$python" ]; then
        log "\$PYTHON_312 is not set; looking for it"
        if [ -z "$version" ]; then
            log "missing version arg"
            exit 1
        fi
        python=$(find-python-on-path $version)
        if [ -z "$python" -a -n "$workdir" ]; then
            log "falling back to a locally built python${version}..."
            workdir=$(abspath "$workdir")
            python=$(find-local-cpython "$workdir" $version)
            if [ -n "$python" ]; then
                log "...found locally built: $python"
            else
                log "...not found"
            fi
        fi
    elif [ -n "$version" ]; then
        log "\$PYTHON_312 is set"
        local actual=$(get-python-version "$python")
        if [ -z "$actual" ]; then
            exit 1
        elif [ "$actual" != "$version" ]; then
            log "version mismatch with '$python' ($version != $actual)"
            exit 1
        fi
    fi

    if [ "$(basename "$python")" = "$python" ]; then
        python=$(which "$python")
    fi

    echo "$python"
}

function script-ensure-cpython() {
    local python=$1
    local workdir=$2
    local version=$3
    local revision=$4

    python=$(script-find-cpython "$python" "$workdir" "$version" "$revision")
    if [ -n "$python" ]; then
        echo "$python"
        return 0
    fi

    log
    log "###################################################"
    log "# \$PYTHON_312 not found; building it"
    log "###################################################"
    log

    if ! build-and-install-local-cpython $workdir $version; then
        exit 1
    fi
    return 0
}

function _script-ensure-venv() {
    local build=false
    local clear=false
    while [ $# -gt 0 ]; do
        case "$1" in
            --build)
                build=true
                ;;
            --clear)
                clear=true
                ;;
            *)
                break
                ;;
        esac
        shift
    done
    local python=$1
    local workdir=$2
    local version=$3
    local revision=$(cpython-get-revision "$python")

    log
    log "###################################################"
    if $build; then
        log "# setting up the build venv"
    else
        log "# setting up the venv"
    fi
    log "# (using $("$python" -V))"
    log "# ($python)"
    if [ -n "$revision" ]; then
        log "# (revision $revision)"
    else
        log "# (revision unknown)"
    fi
    log "###################################################"
    log

    local found=$(bind-matching-venv "$workdir" "$python" "$version" "$revision")
    if [ $? -ne 0 ]; then
        found=
        local venvroot=$(resolve-matching-venv "$workdir" "$python" "$version" "$revision")
        if [ -z "$venvroot" ]; then
            exit 1
        fi
        if &>/dev/null cpython-validate-venv "$venvroot" "$python" "$version" "$revision"; then
            exit 1
        fi
        if ! clear-matching-venv "$workdir" "$python" "$version" "$revision"; then
            exit 1
        fi
    fi

    local venvexe=
    if [ -n "$found" ]; then
        if clear && ! clear-matching-venv "$workdir" "$python" "$version" "$revision"; then
            exit 1
        fi
        venvexe=$found
    else
        venvexe=$(create-matching-venv "$workdir" "$python" "$version" "$revision")
        if [ -z "$venvexe" ]; then
            exit 1
        fi
    fi

    local link=$(resolve-matching-base-venv "$workdir" "$version")
    local linkexe=$(resolve-venv-python "$link" "$version")
    if [ "$venvexe" != "$linkexe" ]; then
        log "using symlink $linkexe"
        log "..to $venvexe"
        venvexe=$linkexe
    fi

    log "'$venvexe'"
}

function script-ensure-venv() {
    clear_arg=''
    if [ "$1" = '--clear' ]; then
        clear_arg=$1
        shift
    fi
    local python=$1
    local workdir=$2
    local version=$3

    local venvexe=$(_script-ensure-venv $clear_arg "$python" "$workdir" "$version")
    if [ -z "$venvexe" ]; then
        exit 1
    fi

    (set -x
    "$venvexe" -m pip install --upgrade pip
    )

    echo "$venvexe"

    #_script-ensure-venv $clear_arg "$python" "$workdir" "$version"
}

function script-ensure-build-venv() {
    local python=$1
    local workdir=$2
    local version=$3

    local venvexe=$(_script-ensure-venv --build --clear "$python" "$workdir" "$version")
    if [ -z "$venvexe" ]; then
        exit 1
    fi
    log "$venvexe"
    exit

    (set -x
    "$venvexe" -m pip install --upgrade pip
    )
    (set -x
    "$venvexe" -m pip install --upgrade setuptools
    "$venvexe" -m pip install --upgrade wheel
    "$venvexe" -m pip install --upgrade build
    )

    echo "$venvexe"
}

function script-build-package() {
    local venvexe=$1

    echo
    echo "###################################################"
    echo "# building the extension modules"
    echo "###################################################"
    echo

    (set -x
    "$venvexe" -P -m build --no-isolation
    )

    #interpreters_3_12-0.0.1.1.tar.gz
    #interpreters_3_12-0.0.1.1-cp312-cp312-linux_x86_64.whl
    local tarball=$(ls dist/interpreters_3_12-*.tar.gz)
    local wheel=$(ls dist/interpreters_3_12-*.whl)

    echo "$tarball"
}

function script-check-built-modules() {
    local venvexe=$1
    local tarball=$2

    echo
    echo "###################################################"
    echo "# checking the extension modules"
    echo "###################################################"
    echo

    (set -x
    "$venv_exe" -m pip install $DIST_TARBALL
    "$venv_exe" -c 'import _interpreters'
    "$venv_exe" -c 'import _interpchannels'
    "$venv_exe" -c 'import _interpqueues'
    # XXX Do not bother uninstalling?
    #"$venv_exe" -m pip uninstall --yes interpreters_3_12
    )
}


# END $_scripts_common_sh
fi

# vim: set filetype=sh :
