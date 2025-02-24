# Copyright © Spyder Updater Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Graphical interface that performs the update process."""

# Standard library imports
from pathlib import Path

# Third-party imports
import qstylizer.style
import qtawesome as qta
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QImage, QPainter, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import QDialog, QLabel, QSpacerItem, QVBoxLayout


def svg_to_scaled_pixmap(scale_factor, theme, rescale=None):
    """
    Transform svg to a QPixmap that is scaled according to a scale factor.

    Parameters
    ----------
    scale_factor: float
        Scale factor at which Spyder is displayed.
    rescale: float, optional
        Rescale pixmap according to a factor between 0 and 1.
    """
    fname = "spyder.svg" if theme == "dark" else "spyder-light.svg"
    image_path = str(Path(__file__).parent / "assets" / fname)

    # Get width and height
    pm = QPixmap(image_path)
    width = pm.width()
    height = pm.height()

    # Rescale but preserving aspect ratio
    if rescale is not None:
        aspect_ratio = width / height
        width = int(width * rescale)
        height = int(width / aspect_ratio)

    # Paint image using svg renderer
    image = QImage(
        int(width * scale_factor), int(height * scale_factor),
        QImage.Format_ARGB32_Premultiplied
    )
    image.fill(0)
    painter = QPainter(image)
    renderer = QSvgRenderer(image_path)
    renderer.render(painter)
    painter.end()

    # This is also necessary to make the image look good for different
    # scale factors
    if scale_factor > 1.0:
        image.setDevicePixelRatio(scale_factor)

    # Create pixmap out of image
    final_pm = QPixmap.fromImage(image)
    final_pm = final_pm.copy(
        0, 0, int(width * scale_factor), int(height * scale_factor)
    )

    return final_pm


class Updater(QDialog):

    def __init__(self, update_info: dict):
        super().__init__(None)
        self._update_info = update_info

        # Attributes from update_info
        self.install_file = self._update_info["install_file"]
        self.conda_exec = self._update_info["conda_exec"]
        self.env_path = self._update_info["env_path"]
        self.update_type = self._update_info["update_type"]

        # Window adjustments
        self.setWindowTitle(self._update_info["window_title"])
        self.setMinimumWidth(650)
        self.setMinimumHeight(350)

        # Hide window close button so it can't be closed while performing the
        # update.
        # TODO: Change this to True when the UI is ready!
        self._hide_close_button(False)

        # Image (icon)
        image_label = QLabel(self)
        image_label.setPixmap(
            svg_to_scaled_pixmap(
                self._update_info["scale_factor"],
                self._update_info["interface_theme"],
                rescale=0.7
            )
        )
        image_label.setAlignment(Qt.AlignCenter)
        image_label_qss = qstylizer.style.StyleSheet()
        image_label_qss.QLabel.setValues(border="0px")
        image_label.setStyleSheet(image_label_qss.toString())

        # Main text
        font_size = self._update_info["font_size"]
        text_label = QLabel(self._update_info["initial_message"], parent=self)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label_qss = qstylizer.style.StyleSheet()
        text_label_qss.QLabel.setValues(
            fontSize=f"{font_size + 5}pt", border="0px"
        )
        text_label.setStyleSheet(text_label_qss.toString())

        # Spinner
        spin_widget = qta.IconWidget()
        self._spin = qta.Spin(spin_widget, interval=3)
        spin_icon = qta.icon(
            "mdi.loading",
            color=self._update_info["icon_color"],
            animation=self._spin
        )

        spin_widget.setIconSize(QSize(36, 36))
        spin_widget.setIcon(spin_icon)
        spin_widget.setStyleSheet(image_label_qss.toString())
        spin_widget.setAlignment(Qt.AlignCenter)

        # Setup layout
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(image_label)
        layout.addWidget(text_label)
        layout.addItem(QSpacerItem(20, 20))
        layout.addWidget(spin_widget)
        layout.addStretch(1)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

    def _hide_close_button(self, hide):
        if hide:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinimizeButtonHint
                | Qt.WindowMaximizeButtonHint
            )
        else:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinimizeButtonHint
                | Qt.WindowMaximizeButtonHint
                | Qt.WindowCloseButtonHint
            )
