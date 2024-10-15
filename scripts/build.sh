#!/usr/bin/env bash

if [ -z "$PYTHON" ]; then
    PYTHON=python3
fi

(set -x
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install --user --upgrade build
)

echo
echo '####################'
echo '# building'
echo '####################'
echo

(set -x
rm -rf dist/*.tar.gz
"$PYTHON" -m build --sdist
)

echo
echo '####################'
echo '# testing'
echo '####################'

venvroot=".venv-$PYTHON"
venvexe="$venvroot/bin/python3"
if [ ! -e "$venvroot" ]; then
    echo
    (set -x
    "$PYTHON" -m venv "$venvroot"
    )
else
    echo
    (set -x
    "$venvexe" -m pip install --upgrade pip
    )
fi

for tarball in dist/*.tar.gz; do
    pkgname=$($PYTHON -c "print('$(basename "$tarball")'[:-13])")
    version=$($PYTHON -c "print('$(basename "$tarball")'[-12:-7])")
    echo
    echo '#----------'
    echo "# testing $tarball"
    echo "# ($pkgname -- $version)"
    echo
    case "$pkgname" in 
        interpreters_pep_734)
            ;;
        *) >&2 echo "ERROR: unsupported package $tarball"; exit 1;;
    esac
    (set -x
    "$venvexe" -m pip uninstall --yes "$pkgname"
    "$venvexe" -m pip install "$tarball"
    )
    
    echo
    (set -x
    "$venvexe" scripts/test-installed.py
    )
    if [ $? -eq 0 ]; then
        echo '# passed!'
    else
        echo '# failed!'
    fi
done
