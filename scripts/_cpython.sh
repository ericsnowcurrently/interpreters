# CPython-specific helpers


function check-python-feature-version() {
    local python=$1
    local expected=$2

    if [ "$(echo "$expected" | grep -o -P '\b\d+\.\d+\b')" != "$expected" ]; then
        err "bad expected version $expected"
        return 1
    fi

    local version=$("$python" --version | grep -o -P '\b\d+\.\d+\b')
    if [ -z "$version" ]; then
        log "could not get version from $("$python" --version)"
        log "  (proceeding as though it matched)"
        return 0
    elif [ "$version" != "$expected" ]; then
        err "version mismatch ($version != $expected)"
        return 1
    fi
    return 0
}


function ensure-cpython-clone() {
    local reporoot=$1
    local ref=$2
    local remote=$3

    if [ -z "$reporoot" ]; then
        reporoot=$(abspath ./cpython)
    elif [ $(basename "$reporoot") = '..' ]; then
        err "cannot use parent directory for reporoot, got $reporoot"
        return 1
    fi
    if [ -z "$ref" -o "$ref" = 'HEAD' ]; then
        ref='main'
    fi
    local cpython_github='https://github.com/python/cpython'
    local url=
    local repo=
    if [ -z "$remote" ]; then
        url=$cpython_github
        repo=$cpython_github
    elif git check-ref-format --allow-onelevel "$remote"; then
        repo=$remote
    else
        url=$remote
        remote=
        repo=$url
    fi

    makedirs "$reporoot"
    if [ -e "$reporoot/.git/config" ]; then
        log "found local clone: $reporoot"
        # XXX Create the remote if missing?
    else
        if [ -z "$url" ]; then
            err "a remote name is useless if the clone doesn't exist, got $remote"
            return 1
        fi
        if ! makedirs "$reporoot"; then
            return 1
        fi
        (set -x
        git -C "$reporoot" init
        )
        if [ -z "$remote" ]; then
            (set -x
            git -C "$reporoot" remote add origin "$url"
            )
            if [ $? -ne 0 ]; then
                return 1
            fi
            (set -x
            git -C "$reporoot" remote add upstream "$url"
            )
            if [ $? -ne 0 ]; then
                return 1
            fi
        else
            (set -x
            git -C "$reporoot" remote add "$remote" "$url"
            )
            if [ $? -ne 0 ]; then
                return 1
            fi
        fi
    fi
    (set -x
    git -C "$reporoot" fetch "$repo" --depth 1 "$ref"
    )
    if [ $? -ne 0 ]; then
        return 1
    fi
    (set -x
    git -C "$reporoot" pull "$repo" "$ref"
    )
    if [ $? -ne 0 ]; then
        return 1
    fi
    (set -x
    git -C "$reporoot" checkout "$ref"
    )
    if [ $? -ne 0 ]; then
        return 1
    fi
    return 0
}

function build-cpython() {
    local srcdir=
    local prefix=
    local builddir=
    local debug=false
    local configargs=
    local step_configure=true
    local step_build=true
    while [ $# -gt 0 ]; do
        case "$1" in
            --configure-only)
                step_configure=true
                step_build=false
                ;;
            --build-only)
                step_configure=false
                step_build=true
                ;;
            --configure-and-build)
                step_configure=true
                step_build=true
                ;;
            --debug)
                debug=true
                ;;
            --no-debug)
                debug=false
                ;;
            --)
                # Everything after this is configure args.
                shift
                break
                ;;
            --*|-*)
                if [ -n "$prefix" ]; then
                    # It must be a configure arg.
                    break
                fi
                err "unsupported option '$1'"
                return 1
                ;;
            '')
                err "got empty arg"
                return 1
                ;;
            *)
                if [ -z "$srcdir" ]; then
                    srcdir=$(abspath "$1")
                elif [ -z "$prefix" ]; then
                    prefix=$(abspath "$1")
                elif [ -z "$builddir" ]; then
                    builddir=$(abspath "$1")
                else
                    # It must be a configure arg.
                    break
                fi
                ;;
        esac
        shift
    done

    if [ -z "$srcdir" ]; then
        err "missing srcdir arg"
        return 1
    elif [ ! -d "$srcdir" ]; then
        err "srcdir $srcdir does not exist"
    fi
    if [ -z "$prefix" ]; then
        err "missing prefix arg"
        return 1
    fi
    if [ -z "$builddir" ]; then
        builddir=$srcdir
    fi

    # Fill in the config args.
    configargs=(
        "--prefix=$prefix"
    )
    if ! $debug; then
        configargs+=( "$@" )
    else
        configargs+=(
            "--with-pydebug"
            "CFLAGS=-O0"
            "$@"
        )
    fi

    # Build!.
    local op='building'
    if $step_configure && ! $step_build; then
        op='configuring'
    fi
    if $debug; then
        op="$op (debug)"
    fi
    log "$op in $builddir..."
    if [ "$builddir" != "$srcdir" ]; then
        log "  (out-of-tree)"
    fi

    makedirs "$builddir"
    &>/dev/null pushd "$builddir"
    if $step_configure; then
        (set -x
        1>&2 "$srcdir/configure" "${configargs[@]}"
        )
        if [ $? -ne 0 ]; then
            &>/dev/null popd
            return 1
        fi
    fi
    if $step_build; then
        (set -x
        1>&2 make -j8
        )
        if [ $? -ne 0 ]; then
            &>/dev/null popd
            return 1
        fi
    fi
    &>/dev/null popd
    return $ec
}

function _install-built-cpython() {
    local builddir=$1
    local prefix=$2
    local version=$3

    if [ -z "$prefix" ]; then
        prefix=$(grep '^prefix=' "$builddir/python-config" | awk -F'"' '{print $2}')
    fi
    if [ -z "$version" ]; then
        version=$(grep '^VERSION=' "$builddir/python-config" | awk -F'"' '{print $2}')
    fi
    local python="$prefix/bin/python$version"

    makedirs "$prefix"
    &>/dev/null pushd "$builddir"
    (set -x
    1>&2 make install
    )
    if [ $? -ne 0 ]; then
        &>/dev/null popd
        return 1
    fi
    &>/dev/null popd
    if [ ! -e "$python" ]; then
        log "something went wrong ($python not found)"
        return 1
    fi
    echo "$python"
    return 0
}


# vim: set filetype=sh :
