# bash script helpers

if [ -z "$_scripts_utils_sh" ]; then
_scripts_utils_sh=1


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

function abspath() {
    realpath --no-symlinks "$1"
}

function isabspath() {
    local filename=$1
    test "$(abspath "$filename")" = "$filename"
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
    while [ $# -gt 0 ]; do
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

    local matched=
    local regex='\b([a-f0-9]{6,40}|[A-F0-9]{6,40})\b'
    if $strict; then
        regex='\b([a-f0-9]{40}|[A-F0-9]{40})\b'
    fi
    grepargs="$grepargs -P"
    if [ -z "$rev" -o "$rev" = '-' ]; then
        matched=$(grep $grepargs "$regex")
    else
        matched=$(echo $rev | grep $grepargs "$regex")
    fi

    if [ -z "$matched" ]; then
        return 1
    fi
    if ! $quiet; then
        echo "$matched"
    fi
    return 0
}

function normalize-git-revision() {
    local revision=$1
    local look_up_revision=$2

    if [ -z "$revision" ]; then
        log "missing revision arg"
        return 1
    fi
    if [ "$(echo "$revision" | wc -l)" -gt 1 ]; then
        log "got multiline revision arg"
        return 1
    fi

    local matched=$(match-git-revision "$revision")
    if [ -z "$matched" ]; then
        log "revision arg must be a git revision, got '$revision'"
        return 1
    fi
    revision=$matched

    if ! match-git-revision -q --strict "$revision"; then
        if [ -z "$look_up_revision" ]; then
            log "revision arg must be a full 80-byte revision, got '$revision'"
            return 1
        fi
        local actual=$("$look_up_revision" "$revision")
        if [ -z "$actual" ]; then
            log "revision $revision not found"
            return 1
        fi
        if ! match-git-revision -q --strict "$actual"; then
            log "resolved $revision to a bad revision ($actual)"
            return 1
        fi
        revision=$actual
    fi
    revsion=${revision^^}  # upper-case

    echo "$revision"
    return 0
}


#######################################
# remote repo

GH_API=https://api.github.com/repos

function gh-normalize-revision() {
    local org=$1
    local repo=$2
    local ref=$3

    # XXX A temporary hack to work around rate limiting
    if [ "$ref" = 'bd9ea91e5f' ]; then
        echo 'BD9EA91E5F7ACE12FE26584F4B130141C62D5BA3'
        return 0
    fi

    #log "+ curl -s $GH_API/$org/$repo/commits/$ref | jq --raw-output .sha"
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
# Python version

function match-python-version() {
    local verstr=
    local quiet=false
    local bugfix=false
    local arg=
    for arg in "$@"; do
        case "$arg" in
            "")
                log "got unexpected empty arg"
                return 1
                ;;
            --quiet|-q)
                quiet=true
                ;;
            --with-bugfix|-B)
                bugfix=true
                ;;
            --without-bugfix)
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
        #log "+ grep -o -P '$regex'"
        found=$(grep -o -P "$regex")
    else
        #log "+ echo $verstr | grep -o -P '$regex'"
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

function get-python-version() {
    local python=$1
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    elif [ ! -e "$python" ]; then
        log "bad python arg '$python'"
        return 1
    fi

    local verstr=$(2>&1 "$python" --version)
    match-python-version -B "$verstr"
}

function resolve-python-version() {
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
    elif [ ! -e "$python" ]; then
        log "bad python arg '$python'"
        return 1
    fi

    if [ -z "$version" ]; then
        get-python-version "$python"
        return
    fi

    local actual=$(match-python-version -B "$version")
    if [ -z "$actual" ]; then
        log "bad version arg $version"
        return 1
    fi
    version=$actual

    if [ -n "$python" ]; then
        local actualversion=$(get-python-version "$python")
        if [ "$(match-python-version "$version")" = "$version" ]; then
            # Chop off any bugfix version.
            actualversion=$(match-python-version "$actualversion")
        fi
        if [ -n "$actualversion" -a "$actualversion" != "$version" ]; then
            log "version mismatch ($version != $actualversion)"
            return 1
        fi
    fi

    echo "$version"
    return 0
}


#######################################
# installed Python

function _check-python-on-path() {
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

function find-python-on-path() {
    local version=$1
    local found=

    if [ -z "$version" ]; then
        log 'find-python-on-path: missing version arg'
        return 1
    fi

    found=$(_check-python-on-path python${version} $version)
    if [ -z "$found" ]; then
        found=$(_check-python-on-path python3 $version)
        if [ -z "$found" ]; then
            found=$(_check-python-on-path python $version)
            if [ -z "$found" ]; then
                log "Python $version not found on \$PATH"
                return 1
            fi
        fi
    fi
    log "Python $version found on \$PATH at $found"
    echo "$found"
    return 0
}


#######################################
# venv

function resolve-venv-root() {
    local venvexe=$1

    local bindir=$(dirname "$venvexe")
    if [ "$(basename "$bindir")" != 'bin' ]; then
        log "bad venvexe arg"
        return 1
    fi
    dirname "$bindir"
}

function resolve-venv-python() {
    local venvroot=$1
    local version=$2
    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    fi

    local venvexe="$(abspath "$venvroot")/bin/python"
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
    if [ -z "$venvexe" ]; then
        log "missing venvexe arg"
        return 1
    elif [ ! -e "$venvexe" ]; then
        log "bad venvexe arg '$venvexe'"
        return 1
    fi
    local python=$2
    local version=$3

    if [ -n "$python" ]; then
        #local actualexe=$(get-original-python-from-venv "$venvexe")
        local actualexe=$(realpath "$venvexe")
        local actualpython=$(realpath "$python")
        if [ "$actualexe" = "$actualpython" ]; then
            return 0
        fi

        version=$(resolve-python-version "$version" "$python")
    fi

    # Check the version.
    if [ -n "$version" ]; then
        local actualversion=$(get-python-version "$venvexe")
        if [ -z "$actualversion" ]; then
            log "actual version not known (ignoring)"
        elif [ "$actualversion" != "$version" ]; then
            log "version mismatch ($actualversion != $version)"
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
    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    else
        venvroot=$(abspath "$venvroot")
    fi

    if [ -n "$python" ]; then
        if match-python-version -q "$python"; then
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
    if ! _validate-venv-python "$venvexe" "$python" "$version"; then
        return 1
    fi

    # Check everything else.
    if ! _validate-venv-other "$venvroot"; then
        return 1
    fi

    return 0
}

function _create-venv() {
    local venvroot=$1
    local python=$2
    local version=$3

    log "creating new venv at $venvroot"
    (set -x
    "$python" -m venv "$venvroot"
    )
    #local venvexe=$(resolve-venv-python "$venvroot" "$version")
    #(set -x
    #"$venvexe" -m pip install --upgrade pip
    #)
}

function create-venv() {
    local venvroot=$1
    local python=$2
    local version=$3

    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    else
        venvroot=$(abspath "$venvroot")
    fi
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    elif [ ! -e "$python" ]; then
        log "bad python arg"
        return 1
    fi

    _create-venv "$venvroot" "$python" "$version"
}

function ensure-venv() {
    local venvroot=$1
    local python=$2
    local version=$3

    if [ -z "$venvroot" ]; then
        log "missing venvroot arg"
        return 1
    else
        venvroot=$(abspath "$venvroot")
    fi
    if [ -z "$python" ]; then
        log "missing python arg"
        return 1
    elif [ ! -e "$python" ]; then
        log "bad python arg"
        return 1
    fi

    if [ ! -e "$venvroot" ]; then
        _create-venv "$venvroot" "$python" "$version"
        return
    fi

    if [ ! -d "$venvroot" ]; then
        log "expected directory at $venvroot"
        return 1
    fi

    log "found existing venv at $venvroot"
    validate-venv "$venvroot" "$python" "$version"

    #local venvexe=$(resolve-venv-python "$venvroot" "$version")
    #(set -x
    #"$venvexe" -m pip install --upgrade pip
    #)
}


# END $_scripts_utils_sh
fi

# vim: set filetype=sh :
