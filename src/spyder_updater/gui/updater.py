# Copyright © Spyder Updater Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Graphical interface that performs the update process."""

# Standard library imports
import os
from pathlib import Path
import shutil
import sys

# Third-party imports
import qdarkstyle
import qstylizer.style
import qtawesome as qta
from qtpy.QtCore import QByteArray, QProcess, QSize, Qt, QTimer
from qtpy.QtGui import QImage, QPainter, QPixmap, QTextCursor
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

        # Process to run the installation scripts
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._update_details)
        self._process.readyReadStandardError.connect(
            lambda: self._update_details(error=True)
        )
        self._process.finished.connect(self._handle_process_finished)
        self._process.errorOccurred.connect(self._handle_error)

        # Window adjustments
        self.setWindowTitle(self._update_info["window_title"])
        self.setWindowFlags(
            Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
        )

        # Timer to close the window automatically after the update finishes
        self._close_timer = QTimer(self)
        self._close_timer.setInterval(8000)
        self._close_timer.timeout.connect(self.close)

        # To check if the update is done
        self._update_done = False

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
        self._text_label = QLabel(
            self._update_info["initial_message"], parent=self
        )
        self._text_label.setAlignment(Qt.AlignCenter)
        self._text_label.setWordWrap(True)
        text_label_qss = qstylizer.style.StyleSheet()
        text_label_qss.QLabel.setValues(
            fontSize=f"{self._update_info['font_size'] + 5}pt",
            border="0px"
        )
        self._text_label.setStyleSheet(text_label_qss.toString())

        # Spinner
        self._spin_widget = qta.IconWidget()
        self._spin = qta.Spin(self._spin_widget, interval=3)
        spin_icon = qta.icon(
            "mdi.loading",
            color=self._update_info["icon_color"],
            animation=self._spin
        )

        self._spin_widget.setIconSize(QSize(36, 36))
        self._spin_widget.setIcon(spin_icon)
        self._spin_widget.setStyleSheet(image_label_qss.toString())
        self._spin_widget.setAlignment(Qt.AlignCenter)

        # Area to show stdout/stderr streams of the process that performs the
        # update
        self._streams_area = QPlainTextEdit(self)
        self._streams_area.setMinimumHeight(300)
        self._streams_area.setReadOnly(True)
        streams_areda_css = qstylizer.style.StyleSheet()
        streams_areda_css.QPlainTextEdit.setValues(
            fontFamily=f"{self._update_info['monospace_font_family']}",
            fontSize=f"{self._update_info['monospace_font_size']}pt",
            border="0px",
        )
        self._streams_area.setStyleSheet(streams_areda_css.toString())

        # Details
        details = CollapsibleWidget(self, update_info)
        details.addWidget(self._streams_area)

        # Timer to expand the details area
        self._expand_details_timer = QTimer(self)
        self._expand_details_timer.setInterval(300)
        self._expand_details_timer.setSingleShot(True)
        self._expand_details_timer.timeout.connect(
            lambda: details.expand(animate=False)
        )

        # Setup layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addStretch(1)
        layout.addWidget(image_label)
        layout.addWidget(self._text_label)
        layout.addItem(QSpacerItem(12, 12))
        layout.addWidget(self._spin_widget)
        layout.addItem(QSpacerItem(8, 8))
        layout.addWidget(details)
        layout.setContentsMargins(24, 24, 24, 24)
        self.setLayout(layout)
        self.layout().setSizeConstraint(QLayout.SetFixedSize)

    # ---- Qt methods
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        # Prevent window to be closed while performing the update
        if not self._update_done:
            event.ignore()
        else:
            event.accept()

    # ---- Private API
    # -------------------------------------------------------------------------
    def _add_text_to_streams_area(self, text):
        self._streams_area.moveCursor(QTextCursor.End)
        self._streams_area.appendHtml(text)
        self._streams_area.moveCursor(QTextCursor.End)

    def _when_update_is_done(self):
        self._update_done = True
        self._spin.stop()
        self._spin_widget.hide()

    def _expand_details(self):
        # We need to use a timer so that Qt centers the dialog first
        self._expand_details_timer.start()

    def _update_details(self, error=False):
        if error:
            self._process.setReadChannel(QProcess.StandardError)
        else:
            self._process.setReadChannel(QProcess.StandardOutput)

        qba = QByteArray()
        while self._process.bytesAvailable():
            if error:
                qba += self._process.readAllStandardError()
            else:
                qba += self._process.readAllStandardOutput()

        text = str(qba.data(), "utf-8")
        self._add_text_to_streams_area(text)

    def _handle_process_finished(self, exit_code, exit_status):
        self._when_update_is_done()

        if exit_code == 0 and exit_status == QProcess.NormalExit:
            self._text_label.setText(self._update_info["success_message"])
            self._close_timer.start()
        else:
            self._text_label.setText(self._update_info["failure_message"])
            self._expand_details()

    def _handle_error(self, error):
        self._when_update_is_done()
        self._text_label.setText(self._update_info["error_message"])

        if error == QProcess.FailedToStart:
            text = "The process failed to start"
        elif error == QProcess.Crashed:
            text = "The process crashed"
        else:
            text = "Unknown error. Please retry the update again"

        self._add_text_to_streams_area(text)
        self._expand_details()

    # ---- Public API
    # -------------------------------------------------------------------------
    def start_install(self, start_spyder: bool):
        # Install script
        script_name = 'install.' + ('bat' if os.name == 'nt' else 'sh')
        script_path = str(
            Path(__file__).parent.parent / 'scripts' / script_name
        )

        # Sub command
        if self._update_info.get("installation_script") is None:
            # Running the installation scripts
            sub_cmd = [
                script_path,
                '-i', self.install_file,
                '-c', self.conda_exec,
                '-p', self.env_path
            ]

            if self.update_type == 'minor':
                # Rebuild runtime environment
                sub_cmd.append('-r')

            if start_spyder:
                sub_cmd.append("-s")
        else:
            # For testing
            script = self._update_info["installation_script"]
            if not Path(script).is_file():
                script = str(Path(__file__).parents[2] / "tests" / script)
            sub_cmd = [script]

        # Final command assembly
        if os.name == 'nt':
            cmd = ['cmd', '/c'] + sub_cmd
        elif sys.platform == "darwin":
            cmd = [shutil.which("zsh")] + sub_cmd
        else:
            cmd = [shutil.which("bash")] + sub_cmd

        # For testing
        if self._update_info.get("installation_script") == "error.sh":
            cmd = ["foo"] + sub_cmd

        print(f"""Update command: "{' '.join(cmd)}" """)
        self._process.start(cmd[0], cmd[1:])
