#!/bin/bash

set -e
source ./scripts/add_path.sh
python -c 'from rdkit import Chem; print(Chem.MolFromSmiles("c1ccccc1"))'

if [[ -n "$COVERAGE" ]]; then
    python -m mordred.tests -v --with-coverage
else
    python -m mordred.tests -v
fi

echo "test README.rst" >&2
python -m doctest README.rst

for example in `find examples -name '*.py'`; do
    echo "test $example" >&2
    PYTHONPATH=. python $example > /dev/null
done
