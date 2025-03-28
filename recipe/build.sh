#!/bin/bash

export SPYDER_QT_BINDING=conda-forge
$PYTHON -m pip install . --no-deps --ignore-installed --no-cache-dir -vvv
