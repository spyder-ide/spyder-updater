# Copyright © Spyder Updater Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Graphical interface that performs the update process."""

# Standard library imports
from pathlib import Path

# Third-party imports
import qdarkstyle
import qstylizer.style
import qtawesome as qta
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QImage, QPainter, QPixmap
from qtpy.QtSvg import QSvgRenderer
from qtpy.QtWidgets import (
    QDialog,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QPushButton,
    QSpacerItem,
    QVBoxLayout
)
from superqt import QCollapsible


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


class CollapsibleWidget(QCollapsible):
    """Collapsible widget to hide and show child widgets."""

    def __init__(self, parent, update_info):
        super().__init__(title=update_info["details_title"], parent=parent)
        self._update_info = update_info

        if self._update_info["interface_theme"] == "dark":
            self._palette = qdarkstyle.DarkPalette
        else:
            self._palette = qdarkstyle.LightPalette

        # Remove spacing between toggle button and contents area
        self.layout().setSpacing(0)

        # Set icons
        self.setCollapsedIcon(
            qta.icon(
                "mdi.chevron-right",
                color=self._update_info["icon_color"],
            )
        )
        self.setExpandedIcon(
            qta.icon(
                "mdi.chevron-down",
                color=self._update_info["icon_color"],
            )
        )

        # To change the style only of these widgets
        self._toggle_btn.setObjectName("collapsible-toggle")
        self.content().setObjectName("collapsible-content")

        # Add padding to the inside content
        self.content().layout().setContentsMargins(*((12,) * 4))

        # Set stylesheet
        self._css = self._generate_stylesheet()
        self.setStyleSheet(self._css.toString())

        # Signals
        self.toggled.connect(self._on_toggled)

        # Set our properties for the toggle button
        self._set_toggle_btn_properties()

    def set_content_bottom_margin(self, bottom_margin):
        """Set bottom margin of the content area to `bottom_margin`."""
        margins = self.content().layout().contentsMargins()
        margins.setBottom(bottom_margin)
        self.content().layout().setContentsMargins(margins)

    def set_content_right_margin(self, right_margin):
        """Set right margin of the content area to `right_margin`."""
        margins = self.content().layout().contentsMargins()
        margins.setRight(right_margin)
        self.content().layout().setContentsMargins(margins)

    def sizeHint(self):
        return QSize(600, 10)

    def _generate_stylesheet(self):
        """Generate base stylesheet for this widget."""
        css = qstylizer.style.StyleSheet()

        # --- Style for the header button
        css["QPushButton#collapsible-toggle"].setValues(
            # Increase padding (the default one is too small).
            padding="9px 9px 9px 6px",
            # Make it a bit different from a default QPushButton to not drag
            # the same amount of attention to it.
            backgroundColor=self._palette.COLOR_BACKGROUND_3
        )

        # Make hover color match the change of background color above
        css["QPushButton#collapsible-toggle:hover"].setValues(
            backgroundColor=self._palette.COLOR_BACKGROUND_4,
        )

        # --- Style for the contents area
        css["QWidget#collapsible-content"].setValues(
            # Remove top border to make it appear attached to the header button
            borderTop="0px",
            # Add border to the other edges
            border=f'1px solid {self._palette.COLOR_BACKGROUND_4}',
            # Add border radius to the bottom to make it match the style of our
            # other widgets.
            borderBottomLeftRadius=f'{self._palette.SIZE_BORDER_RADIUS}',
            borderBottomRightRadius=f'{self._palette.SIZE_BORDER_RADIUS}',
        )

        return css

    def _on_toggled(self, state):
        """Adjustments when the button is toggled."""
        if state:
            # Remove bottom rounded borders from the header when the widget is
            # expanded.
            self._css["QPushButton#collapsible-toggle"].setValues(
                borderBottomLeftRadius='0px',
                borderBottomRightRadius='0px',
            )
        else:
            # Restore bottom rounded borders to the header when the widget is
            # collapsed.
            self._css["QPushButton#collapsible-toggle"].setValues(
                borderBottomLeftRadius=f'{self._palette.SIZE_BORDER_RADIUS}',
                borderBottomRightRadius=f'{self._palette.SIZE_BORDER_RADIUS}',
            )

        self.setStyleSheet(self._css.toString())

    def _set_toggle_btn_properties(self):
        """Set properties for the toogle button."""

        def enter_event(event):
            self.setCursor(Qt.PointingHandCursor)
            super(QPushButton, self._toggle_btn).enterEvent(event)

        def leave_event(event):
            self.setCursor(Qt.ArrowCursor)
            super(QPushButton, self._toggle_btn).leaveEvent(event)

        self.toggleButton().enterEvent = enter_event
        self.toggleButton().leaveEvent = leave_event


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

        # Area to show stdout/stderr streams of the process that performs the
        # update
        self._streams_area = QPlainTextEdit(self)
        self._streams_area.setMinimumHeight(300)
        self._streams_area.setReadOnly(True)
        streams_areda_css = qstylizer.style.StyleSheet()
        streams_areda_css.QPlainTextEdit.setValues(
            border="0px",
        )
        self._streams_area.setStyleSheet(streams_areda_css.toString())

        # Details
        details = CollapsibleWidget(self, update_info)
        details.addWidget(self._streams_area)

        # Setup layout
        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(image_label)
        layout.addWidget(text_label)
        layout.addItem(QSpacerItem(10, 10))
        layout.addWidget(spin_widget)
        layout.addItem(QSpacerItem(12, 12))
        layout.addWidget(details)
        layout.addStretch(1)
        layout.setContentsMargins(30, 30, 30, 30)
        self.setLayout(layout)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    def _hide_close_button(self, hide):
        if hide:
            self.setWindowFlags(
                Qt.Window | Qt.WindowMinimizeButtonHint
            )
        else:
            self.setWindowFlags(
                Qt.Window
                | Qt.WindowMinimizeButtonHint
                | Qt.WindowCloseButtonHint
            )
