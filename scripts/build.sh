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

for tarball in dist/*.tar.gz; do
    echo
    echo '#----------'
    "$PYTHON" scripts/test.py "$tarball"
done
