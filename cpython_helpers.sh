
CPYTHON_UPSTREAM=https://github.com/python/cpython
CPYTHON_SRC=cpython
CPYTHON_BUILD=cpython_312_build
CPYTHON_INSTALL=cpython_312_install

function find-cpython() {
    local version=$1
    local outfile=$2
    local found=

    if [ -e "$version" ]; then
        1>&2 echo 'find-cpython: missing version arg'
        return
    fi

    echo "looking for python${version} on \$PATH..."
    # XXX Find it.

    if [ -n "$found" ]; then
        echo "found: $found"
    else
        echo "python${version} not found"
    fi
    if [ -n "$outfile" ]; then
        echo -n $found > "$outfile"
    else
        # The caller can capture the last line.
        echo $found
    fi
}

function ensure-cpython-source() {
    local version=$1
    local srcdir=$2
    if [ -e $srcdir ]; then
        echo "found local clone: $srcdir"
        echo "updating..."
        (set -x
        git -c $srcdir checkout $version
        git -c $srcdir pull
        )
    else
        echo "cloning CPython locally..."
        (set -x
        git clone --branch $version $CPYTHON_UPSTREAM $srcdir
        git -c $srcdir checkout $version
        )
    fi
}

function build-cpython() {
    local srcdir=$(realpath $1)
    local builddir=$2
    local installdir=$3

    mkdir -p "$builddir"
    &>/dev/null pushd $builddir
    if [ -z "$BUILD_DEBUG" ]; then
        echo "building..."
        (set -x
        $srcdir/configure \
            --with-system-ffi \
            --prefix=$installdir
        )
    else
        echo "building (debug)..."
        (set -x
        $srcdir/configure \
            --with-system-ffi \
            --with-pydebug \
            CFLAGS=-O0 \
            --prefix=$installdir
        )
    fi
    (set -x
    make -j8
    )
    &>/dev/null popd
}

function ensure-cpython-installed() {
    local version=$1
    local workdir=$(realpath $2)
    local outfile=$3
    local installdir=$workdir/cpython_${version}_install
    local executable="$installdir/bin/python${version}"

    mkdir -p $workdir
    if [ -e $executable ]; then
        echo "found locally built: $executable"
    else
        local srcdir=$workdir/cpython
        local builddir=$workdir/cpython_${version}

        ensure-cpython-source $version "$srcdir"

        build-cpython "$srcdir" "$builddir" "$installdir"

        echo "installing..."
        &>/dev/null pushd $builddir
        (set -x
        make install
        )
        &>/dev/null popd
    fi
    if [ -n "$outfile" ]; then
        mkdir -p $(dirname $outfile)
        echo -n $executable > "$outfile"
    else
        # The caller can capture the last line.
        echo $executable
    fi
}
