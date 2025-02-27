# Copyright © Spyder Updater Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main script to display the updater UI and call its OS specific scripts."""

# Standard library imports
import argparse
import json
from pathlib import Path
import sys

# Third-party imports
from qtpy.QtGui import QIcon

# Local imports
# TODO: Use absolute imports here
from updater import Updater
from utils import UpdaterApplication, validate_schema


def main(argv):
    """Run updater."""
    # Parser instance
    parser = argparse.ArgumentParser(usage="update-spyder [options]")

    # Arguments
    parser.add_argument(
        '--update-info-file',
        nargs="?",
        dest="file",
        type=argparse.FileType(),
        help="Path to file that has the info to update Spyder"
    )

    # Get info from update file
    args = parser.parse_args(argv[1:])
    update_info = json.loads(args.file.read())

    # Validate that info conforms to our schema
    if validate_schema(update_info):
        # Create application
        app = UpdaterApplication(
            # These arguments are necessary to set the app name for Gnome
            ['Spyder update', '--no-sandbox'],
            update_info=update_info
        )

        # Set the app name for KDE
        app.setApplicationName('Spyder update')

        # Set icon
        icon = QIcon(str(Path(__file__).parent / "assets" / "spyder.svg"))
        app.setWindowIcon(icon)

        # Instantiate updater and start installation
        updater = Updater(update_info)
        updater.start_install()
        updater.show()

        # Start the Qt event loop
        app.exec()


if __name__ == '__main__':
    main(sys.argv)
