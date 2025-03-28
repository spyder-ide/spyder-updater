setlocal ENABLEDELAYEDEXPANSION

set SPYDER_QT_BINDING=conda-forge
%PYTHON% -m pip install . --no-deps --ignore-installed --no-cache-dir -vvv
if errorlevel 1 exit 1
