#!/bin/bash
set -e

while getopts "i:c:p:rs" option; do
    case "$option" in
        (i) install_file=$OPTARG ;;
        (c) conda=$OPTARG ;;
        (p) prefix=$OPTARG ;;
        (r) rebuild=true ;;
        (s) start_spyder=true ;;
    esac
done
shift $(($OPTIND - 1))

wait_for_spyder_quit(){
    while [[ $(pgrep spyder 2> /dev/null) ]]; do
        echo "Waiting for Spyder to quit..."
        sleep 1
    done

    echo "Spyder has quit."
}

update_spyder(){
    pushd $(dirname $install_file)

    # Determine OS type
    [[ "$OSTYPE" = "darwin"* ]] && os=osx || os=linux
    [[ "$(arch)" = "arm64" ]] && os=${os}-arm64 || os=${os}-64

    echo "Updating Spyder base environment..."
    $conda update --name base --yes --quiet --file "conda-base-${os}.lock"

    if [[ -n "$rebuild" ]]; then
        echo "Rebuilding Spyder runtime environment..."
        $conda remove --prefix $prefix --all --yes --quiet
        mkdir -p $prefix/Menu
        touch $prefix/Menu/conda-based-app
        conda_cmd=create
    else
        echo "Updating Spyder runtime environment..."
        conda_cmd=update
    fi
    $conda $conda_cmd --prefix $prefix --yes --quiet --file "conda-runtime-${os}.lock"

    echo "Cleaning packages and temporary files..."
    $conda clean --yes --quiet --packages --tempfiles $prefix
}

launch_spyder(){
    root=$(dirname $conda)
    pythonexe=$root/python
    menuinst=$root/menuinst_cli.py
    mode=$([[ -e "${prefix}/.nonadmin" ]] && echo "user" || echo "system")
    shortcut_path=$($pythonexe $menuinst shortcut --mode=$mode)

    if [[ "$OSTYPE" = "darwin"* ]]; then
        open -a "$shortcut_path"
    elif [[ -n "$(which gtk-launch)" ]]; then
        gtk-launch $(basename ${shortcut_path%.*})
    else
        nohup $prefix/bin/spyder &>/dev/null &
    fi
}

wait_for_spyder_quit
update_spyder
if [[ "$start_spyder" == "true" ]]; then
    launch_spyder
fi
