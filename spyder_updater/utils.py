# Copyright © Spyder Updater Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Main script to display the updater UI and call its OS specific scripts."""

# Standard library imports
import json
from pathlib import Path

# Third-party imports
import qdarkstyle
from qtpy.QtWidgets import QApplication
import jsonschema


def validate_schema(update_info):
    """Validate if the update info corresponds to update schema."""

    # Validate that info conforms to our schema (throws an error if it fails)
    schema_file = Path(__file__).parent / "assets" / "info-schema.json"
    schema = json.loads(schema_file.read_text())

    try:
        jsonschema.validate(update_info, schema)
        return True
    except jsonschema.ValidationError:
        print(
            "Update info doesn't contain the required fields to perform the "
            "update. Aborting!"
        )
        return False


class UpdaterApplication(QApplication):
    """QApplication for the updater UI."""

    def __init__(self, *args, update_info=None):
        QApplication.__init__(self, *args)

        # Set font
        font = self.font()
        font.setFamily(update_info["font_family"])
        font.setPointSize(update_info["font_size"])
        self.setFont(font)

        # Set style
        palette = (
            qdarkstyle.DarkPalette
            if update_info["interface_theme"] == "dark"
            else qdarkstyle.LightPalette
        )
        self.setStyleSheet(qdarkstyle.load_stylesheet(palette=palette))
