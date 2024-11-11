

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


function compare-versions() {
    local ver1=$1
    local ver2=$2
#    if [ -z "$ver1" ]; then
#        if [ -z "$ver2" ]; then
#            return 0
#        else
#            return 1
#        fi
#    elif [ -z "$ver2" ]; then
#        return -1
#    fi
    python3 << EOF
import sys
ver1 = tuple(int(v) for v in '$ver1'.replace('.', ' ').split())
ver2 = tuple(int(v) for v in '$ver2'.replace('.', ' ').split())
if ver1 == ver2:
    sys.exit(0)
else:
    sys.exit(-1 if ver1 < ver2 else 1)
EOF
}


function get-py3-minor-version() {
    local python=$1
    if [ -z "$python" ]; then
        return 1
    fi
    "$python" -V | grep -o -P '(?<=^Python 3\.)\d+(?=\.)'
}

function find-python() {
    local version=$1
    local found=
    if [ -z "$version" -o "$version" = '3' ]; then
        found=$(which "python3")
        if [ $? -ne 0 ]; then
            return 1
        fi
    else
        local minor=$(echo "$version" | grep -o -P '(?<=^3\.)\d+$')
        if [ -z "$minor" ]; then
            error "$version is not a supported Python version"
            return 1
        fi
        found=$(which "python$version")
        if [ $? -ne 0 ]; then
            found=$(which 'python3')
            if [ $? -ne 0 ]; then
                return 1
            fi
            >&2 echo 'trying "python3" for python executable'
            if [ $(get-py3-minor-version "$found") -ne $minor ]; then
                error "python3 isn't version $version"
                return 1
            fi
        fi
    fi
    echo "$found"
    return 0
}


function get-package-version() {
    local projroot=$1
    if [ -z "$projroot" ]; then
        projroot='.'
    fi
    grep -o -P '(?<=^version = ")\d+\.\d+\.\d+(?=")' "$projroot/pyproject.toml"
}


function get-archive-version() {
    local archive=$1
    local version=$(echo "$archive" | grep -o -P '(?<=^$pkgname-)\d+\.\d+\.\d+(?=-)')
    if [ -z "$version" ]; then
        return 1
    fi
    echo "$version"
    return 0
}

function find-archives() {
    local distdir=$1
    local pkgname=$2
    local version=$3

    if [ "$version" = 'latest' ]; then
        fail 'not implemented'
        version=
        for archive in $(find "$distdir" -name $pkgname-\*.whl); do
            maybe_version=$(get-archive-version "$archive")
            if [ $? -ne 0 ]; then
                fail "no version found in $archive"
            fi
            compare-versions "$version" "$maybe_version"
            rc=$?
            if [ $rc -eq 0 ]; then
                echo "$archive"
#                archives+=("$archive")
            elif [ $rc -gt 0 ]; then
                echo "$archive"
#                archives=("$archive")
                version=$maybe_version
            fi
        done
        for archive in $(find "$distdir" -name $pkgname-\*.tar.gz); do
            maybe_version=$(get-archive-version "$archive")
            if [ $? -ne 0 ]; then
                fail "no version found in $archive"
            fi
            compare-versions "$version" "$maybe_version"
            rc=$?
            if [ $rc -eq 0 ]; then
                echo "$archive"
#                archives+=("$archive")
            elif [ $rc -gt 0 ]; then
                echo "$archive"
#                archives=("$archive")
                version=$maybe_version
            fi
        done
    elif [ -n "$version" ]; then
        for archive in $(set -x; find "$distdir" -name "$pkgname-$version-*.whl"); do
            echo "$archive"
#            archives+=("$archive")
        done
        for archive in $(find "$distdir" -name $pkgname-$version.tar.gz); do
            echo "$archive"
#            archives+=("$archive")
        done
    else
        for archive in $(find "$distdir" -name $pkgname-\*.whl); do
            echo "$archive"
#            archives+=("$archive")
        done
        for archive in $(find "$distdir" -name $pkgname-\*.tar.gz); do
            echo "$archive"
#            archives+=("$archive")
        done
    fi
}


# vim: set filetype=sh :
