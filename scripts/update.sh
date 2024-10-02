#!/usr/bin/env bash

ref="$1"
if [ -z "$ref" ]; then
    ref='main'
fi


# Get the revision.

cmd="curl --silent https://api.github.com/repos/python/cpython/commits/${ref}"
echo "+ ${cmd} | jq -r .sha"
revision=$($cmd | jq -r .sha)

echo
echo "####################"
echo "# Updating from upstream CPython"
echo "# ref:      ${ref}"
echo "# revision: ${revision}"
echo "####################"
echo

if [ -z "$revision" ]; then
    echo "ERROR: failed to get revision"
    exit 1
fi


# Download the files.

CPYTHON_DOWNLOAD="https://raw.githubusercontent.com/python/cpython/${revision}"
PY_FILES=(
interpreters/__init__.py
interpreters/channels.py
interpreters/queues.py
interpreters/_crossinterp.py
)

echo "# clearing old files"
rm -rf src/*
mkdir src/interpreters

echo "# downloading from upstream"
for relfile in "${PY_FILES[@]}"; do
    (set -x
    curl -o "src/${relfile}" "${CPYTHON_DOWNLOAD}/Lib/test/support/${relfile}"
    )
done

echo $revision > src/CPYTHON_REVISION
if [ "${ref}" = "${revision}" ]; then
    rm -f src/CPYTHON_BRANCH
else
    echo $ref > src/CPYTHON_BRANCH
fi


# Update the repo.

git add -u src
2>/dev/null git add src/CPYTHON_BRANCH
