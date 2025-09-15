import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QFileDialog, QMessageBox
from PyQt5.uic import loadUi
import requests
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.patches as mpatches
import folium
import os
import webbrowser
import math
import shutil

# --- Reusable Button Animation Logic ---
button_animation_data = {}

def _scale_button(button, scale_factor):
    """Helper function to scale a given button from center."""
    # Get animation data for the specific button
    if button not in button_animation_data:
        return

    original_size = button_animation_data[button]['original_size']
    scale_animation = button_animation_data[button]['scale']

    current_geo = button.geometry()
    center = current_geo.center()

    new_width = int(original_size.width() * scale_factor)
    new_height = int(original_size.height() * scale_factor)

    new_geo = QtCore.QRect(
        center.x() - new_width // 2,
        center.y() - new_height // 2,
        new_width,
        new_height
    )

    # Start the scale animation
    scale_animation.setStartValue(current_geo)
    scale_animation.setEndValue(new_geo)
    scale_animation.start()

def _button_hover_enter(button, event):
    """Animation when mouse enters button."""
    if button not in button_animation_data:
        return

    shadow = button_animation_data[button]['shadow']

    # Increase shadow on hover
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 4)
    shadow.setColor(QtGui.QColor(230, 0, 0, 120))

    # Scale up by 5%
    _scale_button(button, 1.05)

def _button_hover_leave(button, event):
    """Animation when mouse leaves button."""
    if button not in button_animation_data:
        return

    shadow = button_animation_data[button]['shadow']

    # Reset shadow
    shadow.setBlurRadius(15)
    shadow.setOffset(0, 3)
    shadow.setColor(QtGui.QColor(230, 0, 0, 100))

    # Scale back to original size
    _scale_button(button, 1.0)

def _button_press(button, event):
    """Animation when button is pressed."""
    if button not in button_animation_data:
        return

    shadow = button_animation_data[button]['shadow']

    # Decrease shadow on press
    shadow.setBlurRadius(10)
    shadow.setOffset(0, 2)
    shadow.setColor(QtGui.QColor(230, 0, 0, 80))

    # Scale down by 2%
    _scale_button(button, 0.98)

    QtWidgets.QApplication.processEvents()

def _button_release(button, event):
    """Animation when button is released."""
    if button not in button_animation_data:
        return

    shadow = button_animation_data[button]['shadow']

    # Reset shadow
    shadow.setBlurRadius(15)
    shadow.setOffset(0, 3)
    shadow.setColor(QtGui.QColor(230, 0, 0, 100))

    # Scale back to hover size
    _scale_button(button, 1.05)

    # Manually emit clicked signal as we overrode mouseReleaseEvent
    button.clicked.emit()

    QtWidgets.QApplication.processEvents()

def setup_animated_buttons(button_list, parent_widget):
    """Sets up animations and effects for a list of buttons."""
    for button in button_list:
        if not isinstance(button, QtWidgets.QPushButton):
            print(f"Warning: {button} is not a QPushButton. Skipping animation setup.")
            continue

        # Store original size for reference
        button_animation_data[button] = {
            'original_size': button.size(),
            'scale': QtCore.QPropertyAnimation(button, b"geometry", parent_widget), # Pass parent_widget
            'shadow': QtWidgets.QGraphicsDropShadowEffect(parent_widget), # Pass parent_widget
        }

        # Set up shadow effect
        button_animation_data[button]['shadow'].setBlurRadius(15)
        button_animation_data[button]['shadow'].setColor(QtGui.QColor(230, 0, 0, 100))
        button_animation_data[button]['shadow'].setOffset(0, 3)
        button.setGraphicsEffect(button_animation_data[button]['shadow'])

        # Set up animations
        button_animation_data[button]['scale'].setDuration(100)
        button_animation_data[button]['scale'].setEasingCurve(QtCore.QEasingCurve.OutQuad)

        # Connect events
        button.enterEvent = lambda e, btn=button: _button_hover_enter(btn, e)
        button.leaveEvent = lambda e, btn=button: _button_hover_leave(btn, e)
        # Use a wrapper function for mouse press/release to handle non-left clicks
        button.mousePressEvent = lambda e, btn=button: _button_press(btn, e) if e.button() == QtCore.Qt.LeftButton else QtWidgets.QPushButton.mousePressEvent(btn, e)
        button.mouseReleaseEvent = lambda e, btn=button: _button_release(btn, e) if e.button() == QtCore.Qt.LeftButton else QtWidgets.QPushButton.mouseReleaseEvent(btn, e)
# --- End Reusable Button Animation Logic ---


def load_saved_thresholds():
    try:
        with open('thresholds.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def apply_table_styling(table):
    """Apply consistent, modern styling to QTableWidget objects"""
    # Set alternating row colors for better readability
    table.setAlternatingRowColors(True)
    
    # Set selection behavior to select entire rows
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    
    # Make the header more prominent
    header = table.horizontalHeader()
    header.setHighlightSections(False)
    header.setStretchLastSection(True)
    header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
    header.setDefaultAlignment(QtCore.Qt.AlignCenter)
    
    # Hide vertical header (row numbers)
    table.verticalHeader().setVisible(False)
    
    # Set minimal row height
    table.verticalHeader().setDefaultSectionSize(40)
    
    # Set item alignment to center
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                item.setTextAlignment(QtCore.Qt.AlignCenter)

selected_train_file = None
selected_analysis_type = None
thresholds_data = {}
file_uploaded = False


class MainWindow(QMainWindow):
    def __init__(self, widget):
        super(MainWindow, self).__init__()
        loadUi("mainwindow.ui", self)
        self.widget = widget
        self.insights_page = None  # Store once to reuse
        self.setWindowTitle("DriveTest Analyzer")

        # Make window resizable
        self.setWindowFlags(QtCore.Qt.Window)
        self.setMinimumSize(1000, 700)  # Set minimum size but allow resizing

        # Setup UI improvements
        self._setup_tooltips()
        self._enhance_buttons()
        self._setup_ui_enhancements() # Add UI enhancements

        # Connect button signals
        self.download_button.clicked.connect(self.Download_Function)
        self.browse1_button.clicked.connect(self.Browse1_Function)
        self.browse2_button.clicked.connect(self.Browse2_Function)
        self.set_thresholds_button.clicked.connect(self.got_to_set_thresholds)
        self.classification_button.clicked.connect(self.got_to_classification)
        self.insights_button.clicked.connect(self.got_to_insights)
        self.actions_button.clicked.connect(self.got_to_actions)
        self.predefined_button.clicked.connect(self.got_to_predefined)
        self.Run_button.clicked.connect(self.Run_Analysis)
        self.browse3_button.clicked.connect(self.Browse3_Function) # Connect Browse3 button

        # Initially disable insights button
        self.insights_button.setEnabled(False)

        # Connect exports button to the download function
        # Note: Download_Function is now used for downloading the sample file
        if hasattr(self, 'exports_button'):
            self.exports_button.clicked.connect(self.Download_Function) # Connect exports button
        else:
            print("Warning: exports_button not found in mainwindow.ui")

        # Connect Run_button_2 to terminate the application
        if hasattr(self, 'Run_button_2'):
            self.Run_button_2.clicked.connect(self.close_application) # Connect Run_button_2
        else:
            print("Warning: Run_button_2 not found in mainwindow.ui")

        # Setup temporary feedback labels
        self.drivetest_feedback_label = QtWidgets.QLabel(self.centralwidget)
        self.drivetest_feedback_label.setGeometry(QtCore.QRect(self.upload_drivetest_line.x(), self.upload_drivetest_line.y() + self.upload_drivetest_line.height() + 5, 400, 20)) # Position below line edit, increased width
        self.drivetest_feedback_label.setAlignment(QtCore.Qt.AlignLeft)
        self.drivetest_feedback_label.setStyleSheet("font-size: 10pt;")
        self.drivetest_feedback_label.setHidden(True)

        self.cellfile_feedback_label = QtWidgets.QLabel(self.centralwidget)
        self.cellfile_feedback_label.setGeometry(QtCore.QRect(self.upload_cellfile_line.x(), self.upload_cellfile_line.y() + self.upload_cellfile_line.height() + 5, 400, 20)) # Position below line edit, increased width
        self.cellfile_feedback_label.setAlignment(QtCore.Qt.AlignLeft)
        self.cellfile_feedback_label.setStyleSheet("font-size: 10pt;")
        self.cellfile_feedback_label.setHidden(True)

        # Feedback label for RB Utilization file
        self.rbsfile_feedback_label = QtWidgets.QLabel(self.centralwidget)
        self.rbsfile_feedback_label.setGeometry(QtCore.QRect(self.upload_RBs_line.x(), self.upload_RBs_line.y() + self.upload_RBs_line.height() + 5, 400, 20))
        self.rbsfile_feedback_label.setAlignment(QtCore.Qt.AlignLeft)
        self.rbsfile_feedback_label.setStyleSheet("font-size: 10pt;")
        self.rbsfile_feedback_label.setHidden(True)

        # Timer for hiding feedback labels
        self.feedback_timer = QtCore.QTimer(self)
        self.feedback_timer.setSingleShot(True)
        self.feedback_timer.timeout.connect(self._hide_feedback_labels)

        # Ensure specific labels have a white background
        try:
            for label_name in ['label_3', 'label_4', 'label_5', 'label_6', 'label_7', 'label_8']:
                label = getattr(self, label_name, None)
                if label and isinstance(label, QtWidgets.QLabel):
                    label.setStyleSheet("background-color: white; font: 75 16pt \"Century Gothic\";")
        except Exception as e:
            print(f"Error applying white background to labels: {e}")

    def _setup_tooltips(self):
        """Add helpful tooltips to UI elements"""
        self.download_button.setToolTip("Download a sample drive test file")
        self.browse1_button.setToolTip("Select your drive test data file")
        self.browse2_button.setToolTip("Select your cell configuration file")
        self.set_thresholds_button.setToolTip("Set custom KPI thresholds for analysis")
        self.predefined_button.setToolTip("Use a predefined model for analysis")
        self.Run_button.setToolTip("Run the analysis with current settings")
        self.classification_button.setToolTip("View problem classification results")
        self.insights_button.setToolTip("View detailed KPI statistics and charts")
        self.actions_button.setToolTip("View recommended actions")

    def _enhance_buttons(self):
        """Improve button appearance and effects"""
        # Add visual cue on hover
        for button in [self.download_button, self.browse1_button, self.browse2_button, 
                      self.browse3_button, # Add browse3 button
                      self.set_thresholds_button, self.predefined_button, self.Run_button,
                      self.classification_button, self.insights_button, self.actions_button]:
            button.setCursor(QtCore.Qt.PointingHandCursor)
            # Set minimum size for better clickability
            button.setMinimumHeight(32)

    def _setup_ui_enhancements(self):
        """Apply modern UI enhancements"""
        # Add 3D effect to the content frame with a subtle shadow
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)  # Match SetKpis contentFrame blur
        shadow.setColor(QtGui.QColor(180, 0, 0, 120)) # Match SetKpis contentFrame color (darker red with transparency)
        shadow.setOffset(0, 5)   # Match SetKpis contentFrame vertical offset
        # Apply shadow to the content frame (assuming it's named 'contentFrame' in the .ui file)
        if hasattr(self, 'contentFrame'):
            self.contentFrame.lower() # Send the content frame to the back
            # Ensure content frame expands and allows space for status bar
            size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            size_policy.setHorizontalStretch(0)
            size_policy.setVerticalStretch(0)
            size_policy.setHeightForWidth(self.contentFrame.sizePolicy().hasHeightForWidth())
            self.contentFrame.setSizePolicy(size_policy)
            self.contentFrame.setGraphicsEffect(shadow)
        else:
            print("Warning: 'contentFrame' not found in mainwindow.ui. Shadow not applied.")

        # Add button animations for navigation buttons
        self._setup_button_animations()

    def _setup_button_animations(self):
        """Add hover and click animations to the main navigation buttons"""
        self.button_animations = {}
        buttons_to_animate = [
            self.set_thresholds_button, self.predefined_button, self.Run_button,
            self.classification_button, self.insights_button, self.actions_button,
            self.download_button, self.browse1_button, self.browse2_button, # Add download and browse buttons
            self.exports_button, self.Run_button_2 # Add exports and Run_button_2
        ]
        
        for button in buttons_to_animate:
            # Store original size for reference
            self.button_animations[button] = {
                'original_size': button.size(),
                'scale': QtCore.QPropertyAnimation(button, b"geometry"),
                'shadow': QtWidgets.QGraphicsDropShadowEffect(self),
            }
            
            # Set up shadow effect
            self.button_animations[button]['shadow'].setBlurRadius(15)
            self.button_animations[button]['shadow'].setColor(QtGui.QColor(230, 0, 0, 100))
            self.button_animations[button]['shadow'].setOffset(0, 3)
            button.setGraphicsEffect(self.button_animations[button]['shadow'])
            
            # Set up animations
            self.button_animations[button]['scale'].setDuration(100)
            self.button_animations[button]['scale'].setEasingCurve(QtCore.QEasingCurve.OutQuad)
            
            # Connect events
            button.enterEvent = lambda e, btn=button: self._button_hover_enter(btn, e)
            button.leaveEvent = lambda e, btn=button: self._button_hover_leave(btn, e)
            button.mousePressEvent = lambda e, btn=button: self._button_press(btn, e) if e.button() == QtCore.Qt.LeftButton else btn.mousePressEvent(e)
            button.mouseReleaseEvent = lambda e, btn=button: self._button_release(btn, e) if e.button() == QtCore.Qt.LeftButton else btn.mouseReleaseEvent(e)

    def _scale_button(self, button, scale_factor):
        """Helper function to scale a given button from center"""
        # Get animation data for the specific button
        if button not in self.button_animations:
            return

        original_size = self.button_animations[button]['original_size']
        scale_animation = self.button_animations[button]['scale']

        current_geo = button.geometry()
        center = current_geo.center()
        
        new_width = int(original_size.width() * scale_factor)
        new_height = int(original_size.height() * scale_factor)
        
        new_geo = QtCore.QRect(
            center.x() - new_width // 2,
            center.y() - new_height // 2,
            new_width,
            new_height
        )
        
        # Start the scale animation
        scale_animation.setStartValue(current_geo)
        scale_animation.setEndValue(new_geo)
        scale_animation.start()

    def _button_hover_enter(self, button, event):
        """Animation when mouse enters button"""
        if button not in self.button_animations:
            return

        shadow = self.button_animations[button]['shadow']

        # Increase shadow on hover
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QtGui.QColor(230, 0, 0, 120))
        
        # Scale up by 5%
        self._scale_button(button, 1.05)
        

    def _button_hover_leave(self, button, event):
        """Animation when mouse leaves button"""
        if button not in self.button_animations:
            return

        shadow = self.button_animations[button]['shadow']

        # Reset shadow
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QtGui.QColor(230, 0, 0, 100))

        # Scale back to original size
        self._scale_button(button, 1.0)

    def _button_press(self, button, event):
        """Animation when button is pressed"""
        if button not in self.button_animations:
            return

        shadow = self.button_animations[button]['shadow']

        # Decrease shadow on press
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QtGui.QColor(230, 0, 0, 80))

        # Scale down by 2%
        self._scale_button(button, 0.98)

        QtWidgets.QApplication.processEvents()

    def _button_release(self, button, event):
        """Animation when button is released"""
        if button not in self.button_animations:
            return

        shadow = self.button_animations[button]['shadow']

        # Reset shadow
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QtGui.QColor(230, 0, 0, 100))
        

        # Scale back to hover size
        self._scale_button(button, 1.05)
        
        # Manually emit clicked signal as we overrode mouseReleaseEvent
        button.clicked.emit()
        
        QtWidgets.QApplication.processEvents()

    def Download_Function(self):
        # Create and show loading overlay
        self.loading_overlay = QtWidgets.QWidget(self) # Create overlay on main window
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);") # Semi-transparent black

        self.loading_label = QtWidgets.QLabel(self.loading_overlay)
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
        self.loading_label.setText("Preparing sample file for download...")
        self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;") # White, large, bold text

        self.loading_overlay.show()
        QtWidgets.QApplication.processEvents() # Ensure overlay is displayed immediately

        try:
                print("Download sample clicked.")
                # Define the path to the sample file
                sample_file_name = "DT_Data_Sample.csv"
                current_dir = os.path.dirname(os.path.abspath(__file__))
                sample_file_path = os.path.join(current_dir, sample_file_name)

                if not os.path.exists(sample_file_path):
                    # Display error on overlay if file not found
                    self.loading_label.setText(f"Error: Sample file not found.\n{sample_file_path}")
                    self.loading_label.setStyleSheet("color: red; font-size: 24pt; font-weight: bold;")
                    return # Exit function after displaying error

                # Hide overlay temporarily to show the save dialog
                self.loading_overlay.hide()

                # Open a save file dialog
                save_file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Sample Drive Test File", sample_file_name, "CSV Files (*.csv);;All Files (*)"
                )

                # Show overlay again before processing the save result
                self.loading_overlay.show()
                QtWidgets.QApplication.processEvents()

                if save_file_path:
                    try:
                        # Copy the sample file to the chosen save location
                        import shutil
                        shutil.copyfile(sample_file_path, save_file_path)
                        # Display success message on the overlay
                        self.loading_label.setText("Download Complete!")
                        self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;") # Keep the standard font size
                    except Exception as e:
                        # Display error message on the overlay
                        self.loading_label.setText(f"Failed to save sample file:\n{e}")
                        self.loading_label.setStyleSheet("color: red; font-size: 24pt; font-weight: bold;")
                else:
                    # Handle case where user cancels save dialog
                    self.loading_label.setText("Download cancelled.")
                    self.loading_label.setStyleSheet("color: orange; font-size: 24pt; font-weight: bold;")

        except Exception as e:
            # Display general exception error on the overlay
            self.loading_label.setText(f"An error occurred during download:\n{e}")
            self.loading_label.setStyleSheet("color: red; font-size: 24pt; font-weight: bold;")
        finally:
            # Hide and delete loading overlay after a delay (3 seconds)
            QtCore.QTimer.singleShot(3000, self.hide_loading_overlay)

    def Browse1_Function(self):

        global file_uploaded
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Drive Test File", "", "Excel Files (*.csv *.xlsx);;All Files (*)")
        if file_path:
            self.upload_drivetest_line.setText(file_path)
            
            # Create and show loading overlay
            self.loading_overlay = QtWidgets.QWidget(self) # Create overlay on main window
            self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
            self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);") # Semi-transparent black

            self.loading_label = QtWidgets.QLabel(self.loading_overlay)
            self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
            self.loading_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
            self.loading_label.setText("Uploading and processing file...")
            self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;") # White, large, bold text

            self.loading_overlay.show()
            QtWidgets.QApplication.processEvents() # Ensure overlay is displayed immediately

            try:
                # Read the file content to send it directly
                with open(file_path, 'rb') as f:
                    upload = requests.post("http://127.0.0.1:3000/upload-test", files={'file': f})

                if upload.status_code == 200:
                    # The backend is expected to save the file and run the initial filtering
                    self._show_feedback('drivetest', "Drive test file uploaded and processed successfully.", "green")
                    self.upload_drivetest_line.setStyleSheet("border: 2px solid green;")
                    file_uploaded = True # Keep this flag if it's used elsewhere, though its meaning changes slightly
                    self.insights_button.setEnabled(True) # Enable insights button on success
                else:
                    # Handle potential errors from the backend upload endpoint
                    error_message = upload.json().get('error', 'Unknown upload error')
                    self._show_feedback('drivetest', f"Drive test file upload failed: {error_message}", "red")
                    self.upload_drivetest_line.setStyleSheet("border: 2px solid red;")
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Failed to read or upload file:\n{e}") # Updated message
                # Indicate error with red border
                self.upload_drivetest_line.setStyleSheet("border: 2px solid red;")
            finally:
                # Hide and delete loading overlay
                if hasattr(self, 'loading_overlay') and self.loading_overlay is not None:
                    self.loading_overlay.hide()
                    self.loading_overlay.deleteLater() # Schedule for deletion
                    self.loading_overlay = None # Remove reference

    def Browse2_Function(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Cell File", "", "Excel Files (*.xlsx *.xls);;All Files (*)")
        if file_path:
            self.upload_cellfile_line.setText(file_path)
            try:
                with open(file_path, 'rb') as f:
                    upload = requests.post("http://127.0.0.1:3000/upload-cell", files={'file': f})
                if upload.status_code == 200:
                    self._show_feedback('cellfile', "Cell file uploaded successfully.", "green")
                    # Indicate success with green border
                    self.upload_cellfile_line.setStyleSheet("border: 2px solid green;")
                else:
                    self._show_feedback('cellfile', f"Cell file upload failed: {upload.json().get('error')}", "red")
                    # Indicate failure with red border
                    self.upload_cellfile_line.setStyleSheet("border: 2px solid red;")
            except Exception as e:
                QMessageBox.critical(self, "Upload Error", str(e)) # Keep critical error as popup
                # Indicate error with red border
                self.upload_cellfile_line.setStyleSheet("border: 2px solid red;")

    # New function to browse and upload RB Utilization file
    def Browse3_Function(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select RB Utilization File", "", "Excel Files (*.xlsx *.xls);;All Files (*)")
        if file_path:
            self.upload_RBs_line.setText(file_path)
            try:
                with open(file_path, 'rb') as f:
                    upload = requests.post("http://127.0.0.1:3000/upload-rb", files={'file': f})
                if upload.status_code == 200:
                    self._show_feedback('rbsfile', "RB Utilization file uploaded successfully.", "green")
                    self.upload_RBs_line.setStyleSheet("border: 2px solid green;")
                else:
                    self._show_feedback('rbsfile', f"RB Utilization file upload failed: {upload.json().get('error')}", "red")
                    self.upload_RBs_line.setStyleSheet("border: 2px solid red;")
            except Exception as e:
                QMessageBox.critical(self, "Upload Error", str(e))
                self.upload_RBs_line.setStyleSheet("border: 2px solid red;")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def got_to_set_thresholds(self):
        self.switch_to(SetKpis)

    def got_to_predefined(self):
        self.switch_to(Predefined)

    def got_to_classification(self):
        self.switch_to(Classification)

    def got_to_insights(self):
        global file_uploaded

        if not self.insights_page:
            self.insights_page = Insights(self.widget)
            self.widget.addWidget(self.insights_page)
            self.insights_page.refresh_insights_charts()  # Always refresh charts when first created
        
        elif self.widget.indexOf(self.insights_page) == -1:
            self.widget.addWidget(self.insights_page)
            self.insights_page.refresh_insights_charts()  # Always refresh charts when re-adding to widget

        # Always refresh charts when file has been uploaded
        if file_uploaded:
            self.insights_page.refresh_insights_charts()
            file_uploaded = False

        # Always ensure it's part of the stack before showing
        self.widget.setCurrentWidget(self.insights_page)





    def got_to_actions(self):
        self.switch_to(Actions)

    def Run_Analysis(self):
        global selected_analysis_type, selected_train_file, thresholds_data
        file_path = self.upload_drivetest_line.text()
        if not file_path:
            QMessageBox.critical(self, "Error", "Drive Test file is missing.")
            return

        # Create and show loading overlay
        self.loading_overlay = QtWidgets.QWidget(self) # Create overlay on main window
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);") # Semi-transparent black

        self.loading_label = QtWidgets.QLabel(self.loading_overlay)
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
        self.loading_label.setText("Running analysis...")
        self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;") # White, large, bold text

        self.loading_overlay.show()
        QtWidgets.QApplication.processEvents() # Ensure overlay is displayed immediately

        try:
            if selected_analysis_type == 'thresholds':
                thresholds_data['type'] = 'thresholds'
                response = requests.post("http://127.0.0.1:3000/run-analysis", data=thresholds_data)
            elif selected_analysis_type == 'predefined':
                if selected_train_file:
                    with open(selected_train_file, 'rb') as train:
                        response = requests.post("http://127.0.0.1:3000/run-analysis", data={'type': 'predefined'}, files={'file': train})
                else:
                    response = requests.post("http://127.0.0.1:3000/run-analysis", data={'type': 'predefined'})
            else:
                raise Exception("No analysis type selected.")

            result = response.json()

            # Check if default training file was used for predefined analysis
            used_default_train = (selected_analysis_type == 'predefined' and result.get('used_default_train_file', False))

            if used_default_train:
                # Display message about using default file
                self.loading_label.setText("Using default training file...")
                self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;")
                QtWidgets.QApplication.processEvents() # Update GUI immediately

                # Use a timer to show the final success message after a short delay (e.g., 2 seconds)
                QtCore.QTimer.singleShot(2000, lambda: self.show_final_analysis_message(result))
            else:
                # Directly show the final success message if default wasn't used
                self.show_final_analysis_message(result)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        finally:
            # Hide and delete loading overlay
            # The timer will handle hiding the overlay in success/handled error cases.
            # The finally block ensures cleanup even for unhandled exceptions, though the timer might not be started.
            # Keeping this simplified finally block for safety, although the timer is the primary hiding mechanism now.
            if hasattr(self, 'loading_overlay') and self.loading_overlay is not None and not self.loading_overlay.isHidden():
                # If for some reason the timer didn't hide it (e.g., unhandled exception), hide and delete.
                self.hide_loading_overlay()

    def show_final_analysis_message(self, result):
        """Updates loading label with final analysis message and hides overlay."""
        success_message = result.get("message", "Analysis complete.")
        self.loading_label.setText(success_message)
        # Keep the color white for success message as requested previously
        self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;")
        QtWidgets.QApplication.processEvents() # Update GUI immediately

        # Use a timer to hide the overlay after a delay (3 seconds)
        QtCore.QTimer.singleShot(3000, self.hide_loading_overlay)

        # Switch to classification tab and show chart
        self.classification_window = Classification(self.widget)
        self.widget.addWidget(self.classification_window)
        self.widget.setCurrentWidget(self.classification_window)
        self.classification_window.show_prediction_bar_chart()

    def _show_feedback(self, file_type, message, color):
        """Shows feedback message in the appropriate label"""
        label = None
        if file_type == 'drivetest':
            label = self.drivetest_feedback_label
        elif file_type == 'cellfile':
            label = self.cellfile_feedback_label

        if label:
            label.setStyleSheet(f"background-color: white; color: {color}; font-size: 10pt;") # Added white background
            label.setText(message)
            label.setHidden(False)
            self.feedback_timer.start(5000) # Show message for 5 seconds

    def _hide_feedback_labels(self):
        """Hides all temporary feedback labels"""
        self.drivetest_feedback_label.setHidden(True)
        self.cellfile_feedback_label.setHidden(True)
        self.rbsfile_feedback_label.setHidden(True) # Hide RB Utilization feedback label

    def hide_loading_overlay(self):
        if hasattr(self, 'loading_overlay') and self.loading_overlay is not None:
            self.loading_overlay.hide()
            self.loading_overlay.deleteLater() # Schedule for deletion
            self.loading_overlay = None # Remove reference

    def close_application(self):
        """Terminates the application."""
        print("Closing application...")
        QtWidgets.QApplication.quit() # Use QApplication.quit() for a clean exit


class SetKpis(QMainWindow):
    def __init__(self, widget):
        super(SetKpis, self).__init__()
        loadUi("setthreshold.ui", self)
        self.widget = widget
        
        # Apply modern styling and animations
        self._setup_ui_enhancements()
        
        # Connect signals
        self.submit_button.clicked.connect(self.Submit_Function)
        self.Back_button.clicked.connect(self.return_to_main)
        
        # Load saved thresholds
        saved = load_saved_thresholds()
        self.min_line.setText(str(saved.get('min', '7')))
        self.max_line.setText(str(saved.get('max', '15')))
        self.throughput_line.setText(str(saved.get('throughput', '10000')))
        self.RSRP_line.setText(str(saved.get('rsrp', '-110')))
        self.RSRQ_line.setText(str(saved.get('rsrq', '-15')))
        self.SINR_line.setText(str(saved.get('sinr', '5')))
        self.UE_line.setText(str(saved.get('ue', '23')))
        self.Handover_line.setText(str(saved.get('handover', '5')))
        self.distance_line.setText(str(saved.get('distance', '500')))
        self.overlap_line.setText(str(saved.get('overlap', '3')))
        self.PRB_line.setText(str(saved.get('prb', '70')))
        self.Handover_line_2.setText(str(saved.get('rsrp_neighbor_difference', '6')))
        
        # Set initial focus
        self.throughput_line.setFocus()

    def _setup_ui_enhancements(self):
        """Apply modern UI enhancements and animations"""
        # Ensure the content frame is at the back
        self.contentFrame.lower()
        
        # Add 3D effect to content frame with darker red shadow
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)  # Increased blur for a softer shadow
        shadow.setColor(QtGui.QColor(180, 0, 0, 120)) # Darker red color with increased transparency
        shadow.setOffset(0, 5)   # Increased vertical offset for more depth
        self.contentFrame.setGraphicsEffect(shadow)
        
        # Add 3D effect to title label with darker red shadow
        title_shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        title_shadow.setBlurRadius(12)  # Slightly increased blur
        title_shadow.setColor(QtGui.QColor(180, 0, 0, 180)) # Darker red, slightly more opaque for text shadow
        title_shadow.setOffset(0, 2)   # Kept offset
        self.titleLabel.setGraphicsEffect(title_shadow)
        
        # Add tooltips to all input fields with improved descriptions
        self.throughput_line.setToolTip("Target throughput in kbps (e.g., 10000 for 10 Mbps)\\nRecommended range: 5000-15000 kbps")
        self.min_line.setToolTip("Minimum number of samples required to identify a problem area\\nRecommended value: 7")
        self.max_line.setToolTip("Maximum number of samples to consider for a single problem area\\nRecommended value: 15")
        self.RSRP_line.setToolTip("Reference Signal Received Power threshold in dBm\\nRecommended range: -110 to -90 dBm")
        self.RSRQ_line.setToolTip("Reference Signal Received Quality threshold in dB\\nRecommended range: -15 to -10 dB")
        self.SINR_line.setToolTip("Signal-to-Interference-plus-Noise Ratio threshold in dB\\nRecommended range: 5 to 20 dB")
        self.UE_line.setToolTip("User Equipment transmit power threshold in dBm\\nRecommended value: 23 dBm")
        self.Handover_line.setToolTip("Handover threshold in dB for inter-frequency handovers\\nRecommended value: 5 dB")
        self.distance_line.setToolTip("Distance threshold in meters for detecting overshooting cells\\nRecommended value: 500 m")
        self.overlap_line.setToolTip("Threshold for detecting overlapping cells\\nRecommended value: 3")
        self.PRB_line.setToolTip("Physical Resource Block utilization threshold in percentage\\nRecommended range: 70-90%")
        
        # Add input validation
        self._setup_validators()
        
        # Add button hover effect for submit button
        # Removed _setup_submit_button_animation()
        
        # Add button hover effect for back button
        # Removed _setup_back_button_animation()
        
        # Add focus animations for input fields
        self._setup_focus_animations()
    
    # Removed _setup_submit_button_animation method
    # Removed _setup_back_button_animation method
    # Removed _scale_button method
    # Removed _button_hover_enter method
    # Removed _button_hover_leave method
    # Removed _button_press method
    # Removed _button_release method

    def _setup_focus_animations(self):
        """Add animations when input fields gain focus"""
        input_fields = [
            self.throughput_line, self.min_line, self.max_line, 
            self.RSRP_line, self.RSRQ_line, self.SINR_line,
            self.UE_line, self.Handover_line, self.distance_line,
            self.overlap_line, self.PRB_line
        ]
        
        for field in input_fields:
            # Connect focus events using installEventFilter instead of overriding focusInEvent
            field.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle events for all widgets with installed event filters"""
        if event.type() == QtCore.QEvent.FocusIn:
            # Handle focus in for input fields
            if isinstance(obj, QtWidgets.QLineEdit):
                obj.setStyleSheet("""
                    border: 2px solid #e60000;
                    border-radius: 6px;
                    padding: 8px;
                    background-color: rgba(255, 250, 250, 0.5);
                """)
                return False  # Let the event continue
                
        elif event.type() == QtCore.QEvent.FocusOut:
            # Handle focus out for input fields
            if isinstance(obj, QtWidgets.QLineEdit):
                obj.setStyleSheet("""
                    border: 1px solid #cccccc;
                    border-radius: 6px;
                    padding: 8px;
                    background-color: transparent;
                """)
                return False  # Let the event continue
                
        # Standard event processing
        return super().eventFilter(obj, event)
    
    def _add_shadow_effect(self, widget, blur_radius=10, color=QtCore.Qt.black, x_offset=0, y_offset=2):
        """Add shadow effect to a widget"""
        # This method is no longer used
        pass
    
    def _animate_form_entry(self):
        """Create staggered animations for form elements appearing"""
        # This method is no longer used
        pass
    
    def _setup_validators(self):
        """Add input validators to ensure correct data entry"""
        # Integer validators
        int_validator = QtGui.QIntValidator()
        self.min_line.setValidator(int_validator)
        self.max_line.setValidator(int_validator)
        self.PRB_line.setValidator(QtGui.QIntValidator(0, 100))  # 0-100%
        
        # Double validators with range
        double_validator = QtGui.QDoubleValidator()
        self.throughput_line.setValidator(double_validator)
        self.RSRP_line.setValidator(QtGui.QDoubleValidator(-150, 0, 2))  # RSRP range
        self.RSRQ_line.setValidator(QtGui.QDoubleValidator(-30, 0, 2))   # RSRQ range
        self.SINR_line.setValidator(QtGui.QDoubleValidator(-10, 30, 2))  # SINR range
        self.UE_line.setValidator(double_validator)
        self.Handover_line.setValidator(double_validator)
        self.distance_line.setValidator(double_validator)
        self.overlap_line.setValidator(double_validator)
    
    def _add_vodafone_branding(self):
        """Add Vodafone logo to the UI"""
        try:
            # Create a label for the Vodafone logo
            logo_label = QtWidgets.QLabel(self.centralwidget)
            logo_label.setGeometry(QtCore.QRect(700, 20, 60, 60))
            
            # Try to load the Vodafone logo if it exists
            if os.path.exists("vodafone_logo.png"):
                pixmap = QtGui.QPixmap("vodafone_logo.png")
                logo_label.setPixmap(pixmap.scaled(60, 60, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
                logo_label.setToolTip("Vodafone DriveTest Analyzer")
            else:
                # Create a text-based logo if image doesn't exist
                logo_label.setText("V")
                logo_label.setAlignment(QtCore.Qt.AlignCenter)
                logo_label.setStyleSheet("""
                    background-color: #e60000; 
                    color: white; 
                    font-size: 24pt; 
                    font-weight: bold;
                    border-radius: 30px;
                """)
                logo_label.setToolTip("Vodafone DriveTest Analyzer")
        except Exception as e:
            print(f"Could not add Vodafone branding: {e}")

    def Submit_Function(self):
        global selected_analysis_type, thresholds_data
        
        selected_analysis_type = 'thresholds'
        self.widget.selected_analysis_type = 'thresholds'
        
        # Create a simple message overlay without graphics effects
        self.message_overlay = QtWidgets.QWidget(self)
        self.message_overlay.setGeometry(0, 0, self.width(), self.height())
        self.message_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);")
        
        # Create message label
        self.message_label = QtWidgets.QLabel(self.message_overlay)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
        self.message_label.setText("Saving thresholds...")
        self.message_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;")
        
        self.message_overlay.show()
        QtWidgets.QApplication.processEvents()
        
        # Save the thresholds
        thresholds_data = {
            'min': self.min_line.text(),
            'max': self.max_line.text(),
            'throughput': self.throughput_line.text(),
            'rsrp': self.RSRP_line.text(),
            'rsrq': self.RSRQ_line.text(),
            'sinr': self.SINR_line.text(),
            'ue': self.UE_line.text(),
            'handover': self.Handover_line.text(),
            'distance': self.distance_line.text(),
            'overlap': self.overlap_line.text(),
            'prb': self.PRB_line.text(),
            'rsrp_neighbor_difference': self.Handover_line_2.text() # Get value from Handover_line_2
        }

        # Save thresholds to JSON file
        with open('thresholds.json', 'w') as f:
            json.dump(thresholds_data, f)
        
        # Simulate processing time for visual feedback
        QtCore.QTimer.singleShot(1000, lambda: self.return_to_main())

    def return_to_main(self):
        """Return to the main window without animations"""
        # Simply remove all extra widgets and return to main
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)


class Predefined(QMainWindow):
    def __init__(self, widget):
        super(Predefined, self).__init__()
        loadUi("predefined.ui", self)
        self.widget = widget
        # Apply UI enhancements
        self._setup_ui_enhancements()

        # Connect buttons
        self.Done_button.clicked.connect(self.Submit_Function)
        # Assuming browse3_button is for selecting the training file
        if hasattr(self, 'browse3_button'):
            self.browse3_button.clicked.connect(self.Browse3_Function)
        else:
            print("Warning: browse3_button not found in predefined.ui")

        # Connect Back button to return to main window
        if hasattr(self, 'Back_button'):
            self.Back_button.clicked.connect(self.return_to_main)
        else:
            print("Warning: Back_button not found in predefined.ui")

        # Loading overlay attributes
        self.loading_overlay = None
        self.loading_label = None

    def Submit_Function(self):
        global selected_train_file, selected_analysis_type
        selected_analysis_type = 'predefined'
        self.widget.selected_analysis_type = 'predefined'

        file_path = self.training_line.text()
        if not file_path:
            # If no file is uploaded, use the default and show message
            selected_train_file = ""

            # Create and show a temporary message overlay
            self.message_overlay = QtWidgets.QWidget(self) # Create overlay on predefined window
            self.message_overlay.setGeometry(0, 0, self.width(), self.height())
            self.message_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);") # Semi-transparent black

            self.message_label = QtWidgets.QLabel(self.message_overlay)
            self.message_label.setAlignment(QtCore.Qt.AlignCenter)
            self.message_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
            self.message_label.setText("Using default training file...")
            self.message_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;")

            self.message_overlay.show()
            QtWidgets.QApplication.processEvents() # Ensure overlay is displayed immediately

            # Use a timer to hide the message and return to main after a delay
            QtCore.QTimer.singleShot(2000, self.hide_message_overlay_and_return_to_main) # Show message for 2 seconds
        else:
            # If a file path is present, set it and return immediately
            selected_train_file = file_path
            self.return_to_main() # Correctly indented return to main

    def Browse3_Function(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Training File", "", "CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return # User cancelled the dialog

        self.training_line.setText(file_path)

        # Create and show loading overlay
        self.loading_overlay = QtWidgets.QWidget(self) # Create overlay on predefined window
        self.loading_overlay.setGeometry(0, 0, self.width(), self.height())
        self.loading_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 120);") # Semi-transparent black

        self.loading_label = QtWidgets.QLabel(self.loading_overlay)
        self.loading_label.setAlignment(QtCore.Qt.AlignCenter)
        self.loading_label.setGeometry(QtCore.QRect(0, 0, self.width(), self.height()))
        self.loading_label.setText("Uploading training file...")
        self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;") # White, large, bold text

        self.loading_overlay.show()
        QtWidgets.QApplication.processEvents() # Ensure overlay is displayed immediately

        try:
            # Read the file content to send it directly
            with open(file_path, 'rb') as f:
                # Use the new /upload-train endpoint
                upload = requests.post("http://127.0.0.1:3000/upload-train", files={'file': f})

            if upload.status_code == 200:
                # Display success message on the overlay
                success_message = upload.json().get('message', 'Training file uploaded successfully.')
                self.loading_label.setText(success_message)
                self.loading_label.setStyleSheet("color: white; font-size: 24pt; font-weight: bold;")
                self.training_line.setStyleSheet("border: 2px solid green;")
            else:
                # Display error message on the overlay
                error_message = upload.json().get('error', 'Unknown upload error')
                self.loading_label.setText(f"Upload failed: {error_message}")
                self.loading_label.setStyleSheet("color: red; font-size: 24pt; font-weight: bold;")
                self.training_line.setStyleSheet("border: 2px solid red;")
        except Exception as e:
            # Display general exception error on the overlay
            self.loading_label.setText(f"An error occurred during upload: {e}")
            self.loading_label.setStyleSheet("color: red; font-size: 24pt; font-weight: bold;")
            self.training_line.setStyleSheet("border: 2px solid red;")
        finally:
            # Hide and delete loading overlay after a delay (3 seconds)
            QtCore.QTimer.singleShot(3000, self.hide_loading_overlay)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def hide_loading_overlay(self):
        """Hides and deletes the loading overlay."""
        if hasattr(self, 'loading_overlay') and self.loading_overlay is not None:
            self.loading_overlay.hide()
            self.loading_overlay.deleteLater() # Schedule for deletion
            self.loading_overlay = None # Remove reference

    def _setup_ui_enhancements(self):
        """Apply modern UI enhancements to the Predefined page."""
        # Add 3D effect to the content frame with a subtle shadow (matching MainWindow)
        try:
            if hasattr(self, 'contentFrame'):
                shadow = QtWidgets.QGraphicsDropShadowEffect(self)
                shadow.setBlurRadius(25)  # Match MainWindow contentFrame blur
                shadow.setColor(QtGui.QColor(180, 0, 0, 120)) # Match MainWindow contentFrame color
                shadow.setOffset(0, 5)   # Match MainWindow contentFrame vertical offset
                self.contentFrame.setGraphicsEffect(shadow)
            else:
                 print("Warning: 'contentFrame' not found in predefined.ui. Shadow not applied.")
        except Exception as e:
            print(f"Error applying shadow to contentFrame in Predefined page: {e}")

    def hide_message_overlay_and_return_to_main(self):
        """Hides the temporary message overlay and returns to the main window."""
        if hasattr(self, 'message_overlay') and self.message_overlay is not None:
            self.message_overlay.hide()
            self.message_overlay.deleteLater() # Schedule for deletion
            self.message_overlay = None # Remove reference
        self.return_to_main()


class Classification(QMainWindow):
    def __init__(self, widget):
        super(Classification, self).__init__()
        loadUi("problemclassification.ui", self)
        self.widget = widget

        # Button connections
        self.exports_button.clicked.connect(self.return_to_main)
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(self.open_bad_coverage_page)
        self.Handover_Button.clicked.connect(self.open_handover_page)
        self.Overlapping_button.clicked.connect(self.open_overlapping_page)
        self.Highload_button.clicked.connect(self.open_highload_page)
        self.OvershootingButton.clicked.connect(self.open_overshooting_page)



        self.show_prediction_bar_chart()

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

        # 🔥 If returning to Classification, refresh the bar chart
        if isinstance(window, Classification):
            window.refresh_chart()

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def refresh_chart(self):
        """Regenerate the bar chart every time you come back to this page."""
        self.show_prediction_bar_chart()

    def show_prediction_bar_chart(self):
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import os
            global selected_analysis_type

            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Chart Error", "Unknown analysis type.")
                return

            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Chart Error", f"CSV file not found at: {csv_path}")
                return

            df = pd.read_csv(csv_path)

            # Fill down missing values in the 'Dominant Problem' column
            df["Dominant Problem"] = df["Dominant Problem"].ffill()
            # Group by unique Spot Area
            unique_spots = df.drop_duplicates(subset="Spot_Area_Num", keep='first')
            counts = unique_spots["Dominant Problem"].value_counts()

            fig, ax = plt.subplots(figsize=(10, 6))
            fig.subplots_adjust(bottom=0.35)  # Increase bottom margin for rotated x-axis labels

            ax.bar(counts.index, counts.values, color='tomato')
            ax.set_title("Predicted Dominant Problems per Area", fontsize=13)
            ax.set_ylabel("Number of Areas", fontsize=11)
            ax.set_xlabel("Dominant Problem", fontsize=11)
            ax.tick_params(axis='x', labelrotation=45)

            canvas = FigureCanvas(fig)

            # Clear old chart if exists
            if self.chartArea.layout() is None:
                layout = QtWidgets.QVBoxLayout(self.chartArea)
                self.chartArea.setLayout(layout)
            else:
                while self.chartArea.layout().count():
                    item = self.chartArea.layout().takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)

            # Add new chart
            self.chartArea.layout().addWidget(canvas)

        except Exception as e:
            QMessageBox.warning(self, "Chart Error", f"Could not generate chart: {e}")


    

    def open_bad_coverage_page(self):
        from pyqt import BadCoveragePage  # adjust if necessary
        self.bad_coverage_page = BadCoveragePage(self.widget)
        self.widget.addWidget(self.bad_coverage_page)
        self.widget.setCurrentWidget(self.bad_coverage_page)

    def open_handover_page(self):
        from pyqt import HandoverPage  # adjust if necessary
        self.handover_page = HandoverPage(self.widget)
        self.widget.addWidget(self.handover_page)
        self.widget.setCurrentWidget(self.handover_page)

    def open_overlapping_page(self):
        from pyqt import OverlappingPage  # or wherever it is
        self.overlapping_page = OverlappingPage(self.widget)
        self.widget.addWidget(self.overlapping_page)
        self.widget.setCurrentWidget(self.overlapping_page)

    def open_highload_page(self):
        from pyqt import HighLoadPage
        self.highload_page = HighLoadPage(self.widget)
        self.widget.addWidget(self.highload_page)
        self.widget.setCurrentWidget(self.highload_page)

    def open_overshooting_page(self):
        from pyqt import OvershootingPage
        self.overshooting_page = OvershootingPage(self.widget)
        self.widget.addWidget(self.overshooting_page)
        self.widget.setCurrentWidget(self.overshooting_page)


class BadCoveragePage(QMainWindow):
    def __init__(self, widget):
        super(BadCoveragePage, self).__init__()
        loadUi("badCoverage.ui", self)
        self.widget = widget

        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(lambda: self.switch_to(BadCoveragePage))
        self.Handover_Button.clicked.connect(lambda: self.switch_to(HandoverPage))
        self.Overlapping_button.clicked.connect(lambda: self.switch_to(OverlappingPage))
        self.Highload_button.clicked.connect(lambda: self.switch_to(HighLoadPage))
        self.exports_button.clicked.connect(self.return_to_main)
        self.OvershootingButton.clicked.connect(lambda: self.switch_to(OvershootingPage))

        # Initialize the table
        self.badCoverageTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)  # Make table read-only
        
        # Define stylish button stylesheet
        self.stylish_button_style = """
            QPushButton {
                background-color: #FFCCCC; /* Light red background */
                color: #B30000; /* Deep red text */
                font-size: 10pt; /* Slightly larger font */
                font-weight: bold;
                border: 2px solid #E60000; /* Vodafone red border */
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFE5E5; /* Lighter red on hover */
                border-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #FF9999;
                border-color: #990000;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """
        
        self.populate_bad_coverage_table()

        # Ensure label_7 has a white background
        try:
            label7 = getattr(self, 'label_7', None)
            if label7 and isinstance(label7, QtWidgets.QLabel):
                label7.setStyleSheet("background-color: white; font: 75 16pt \"Century Gothic\";")
        except Exception as e:
            print(f"Error applying white background to label_7: {e}")

        # Setup insights overlay
        self.insights_overlay = QtWidgets.QWidget(self) # Create overlay on BadCoveragePage
        self.insights_overlay.setGeometry(0, 0, self.width(), self.height()) # Cover the whole page
        self.insights_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);") # Semi-transparent dark background
        self.insights_overlay.setHidden(True)

        self.insights_label = QtWidgets.QLabel(self.insights_overlay)
        self.insights_label.setAlignment(QtCore.Qt.AlignCenter)
        self.insights_label.setGeometry(QtCore.QRect(0, 0, self.insights_overlay.width(), self.insights_overlay.height()))
        self.insights_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;") # White, bold text
        self.insights_label.setWordWrap(True) # Enable word wrapping

        # Install event filter to hide overlay on click
        self.insights_overlay.installEventFilter(self)

    def populate_bad_coverage_table(self):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print("DEBUG: selected_analysis_type =", analysis_type)
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            df["Dominant Problem"] = df["Dominant Problem"].ffill()

            # Load recommendations
            if analysis_type == "predefined":
                suggestion_path = os.path.join(base_dir, "For_ML_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            elif analysis_type == "thresholds":
                suggestion_path = os.path.join(base_dir, "For_Code_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            else:
                QMessageBox.warning(self, "Error", "Unknown analysis type.")
                return
            if not os.path.exists(suggestion_path):
                QMessageBox.warning(self, "Error", f"CSV file not found at: {suggestion_path}")
                return
            

            # suggestion_path = os.path.join(base_dir, "For_ML_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            if not os.path.exists(suggestion_path):
                raise FileNotFoundError(f"Suggestion file not found at: {suggestion_path}")
            suggestion_df = pd.read_csv(suggestion_path)
            suggestion_df = suggestion_df.drop_duplicates(subset="Spot_Area_Num", keep='first')
            suggestion_map = dict(zip(suggestion_df["Spot_Area_Num"], suggestion_df.iloc[:, 14]))
            
            # Also create a map for RSRP Range increase per Area
            rsrp_range_map = {}
            if "RSRP Range increase per Area" in suggestion_df.columns:
                rsrp_range_map = dict(zip(suggestion_df["Spot_Area_Num"], suggestion_df["RSRP Range increase per Area"]))
            
            # Check if Insights column exists before trying to access it
            if "Insights" in suggestion_df.columns:
                insights_map = dict(zip(suggestion_df["Spot_Area_Num"], suggestion_df["Insights"]))
            else:
                insights_map = {}  # Empty dict if no Insights column

            # Filter for Bad Coverage
            bad_df = df[df["Dominant Problem"] == "Bad Coverage"]
            unique_spots = bad_df.drop_duplicates(subset="Spot_Area_Num")

            self.badCoverageTable.setRowCount(len(unique_spots))
            self.badCoverageTable.setColumnCount(3)
            self.badCoverageTable.setHorizontalHeaderLabels(["Spot Area", "RSRP Range Increase", "See on Map"])

            for i, spot in enumerate(unique_spots["Spot_Area_Num"]):
                # Spot number (center-aligned)
                spot_item = QtWidgets.QTableWidgetItem(str(spot))
                spot_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.badCoverageTable.setItem(i, 0, spot_item)

                # Recommendation text box (center the text inside QTextEdit)
                recommendation = rsrp_range_map.get(spot, "No recommendation")
                rec_box = QtWidgets.QTextEdit()
                rec_box.setText(str(recommendation))
                rec_box.setReadOnly(True)
                rec_box.setAlignment(QtCore.Qt.AlignCenter)
                rec_box.setStyleSheet("background-color: rgba(255, 255, 255, 0.7);")

                # See Insights button
                btn_insights = QtWidgets.QPushButton("See Insights")
                # Apply the defined stylish button stylesheet
                btn_insights.setStyleSheet(self.stylish_button_style)
                btn_insights.clicked.connect(lambda _, s=spot: self.show_insights_message(s, insights_map))

                # Layout for recommendation + button
                rec_widget = QtWidgets.QWidget()
                rec_layout = QtWidgets.QHBoxLayout(rec_widget)
                rec_layout.addWidget(rec_box)
                rec_layout.addWidget(btn_insights)
                rec_layout.setContentsMargins(0, 0, 0, 0)
                self.badCoverageTable.setCellWidget(i, 1, rec_widget)

                # See on Map button (full cell width)
                btn_map = QtWidgets.QPushButton("See on Map")
                btn_map.setIcon(QtGui.QIcon("map_icon.png"))  # Add a map icon
                # Apply the defined stylish button stylesheet
                btn_map.setStyleSheet(self.stylish_button_style)
                btn_map.clicked.connect(lambda _, s=spot: self.show_on_map(s))
                btn_map.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.badCoverageTable.setCellWidget(i, 2, btn_map)

            # Apply consistent styling (This might conflict with custom styles, remove or adjust as needed)
            # apply_table_styling(self.badCoverageTable) # Removed or commented out to avoid conflicts

            # Enhance table header appearance by setting font directly
            header = self.badCoverageTable.horizontalHeader()
            font = QtGui.QFont()
            font.setPointSize(12)
            font.setBold(True)
            header.setFont(font)
            header.setStyleSheet("QHeaderView::section { background-color: #ecf0f1; border: 1px solid #d0d0d0; padding: 4px; }") # Keep other header styles if needed

            # Set column stretching behavior
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

            # Remove table borders and ensure gridline color is kept
            self.badCoverageTable.setStyleSheet("QTableWidget { border: none; gridline-color: #d0d0d0; }")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not populate table:\n{e}")

    def show_insights_message(self, spot, insights_map):
        if not hasattr(self, 'insights_overlay') or self.insights_overlay is None:
             print("Insights overlay not initialized.")
             return

        if not insights_map:
            msg = "Insights are not available in this analysis mode."
        else:
            msg = insights_map.get(spot, "No insights available for this area.")

        # Update label text and show overlay
        self.insights_label.setText(str(msg))
        # Ensure overlay covers the current size of the page
        self.insights_overlay.setGeometry(0, 0, self.width(), self.height())
        self.insights_label.setGeometry(QtCore.QRect(0, 0, self.insights_overlay.width(), self.insights_overlay.height()))
        self.insights_overlay.raise_() # Bring to front
        self.insights_overlay.show()

    def eventFilter(self, obj, event):
        # Filter clicks on the insights overlay to hide it
        if obj is self.insights_overlay and event.type() == QtCore.QEvent.MouseButtonPress:
            self.insights_overlay.hide()
            return True # Event handled
        return super().eventFilter(obj, event)

    def show_recommendations(self, spot):
        QMessageBox.information(self, "Recommendations", f"Showing recommendations for Spot Area: {spot}")

    def show_on_map(self, spot):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Map Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            filtered_df = df[df["Spot_Area_Num"] == spot]
            if filtered_df.empty:
                QMessageBox.information(self, "No Data", "No data found for this spot.")
                return
            cell_df = pd.read_excel("Uploaded_Cell.xlsx")
            cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
            cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"}.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.3, color='blue'):
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            latitudes = filtered_df["Latitude"].values
            longitudes = filtered_df["Longitude"].values
            m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=14)

            for lat, lon in zip(latitudes, longitudes):
                folium.Marker(location=[lat, lon], popup=f"Spot: {spot}").add_to(m)

            for _, row in cell_df.iterrows():
                lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                name = row["CellNAME"]
                band = row.get("Freq Band", "Unknown")
                color = get_band_color(band)
                popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                draw_sector(m, lat, lon, azimuth, popup_html, color=color)
                folium.CircleMarker(location=[lat, lon], radius=3, color=color, fill=True,
                                    fill_opacity=1, popup=f"{name} (site center)").add_to(m)

            # Create Maps directory if it doesn't exist
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)
            
            # Save map in Maps directory
            map_path = os.path.join(maps_dir, f"map_spot_{spot}.html")
            m.save(map_path)
            webbrowser.open(map_path)

        except Exception as e:
            QMessageBox.warning(self, "Map Error", f"Error generating map:\n{e}")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)


class OverlappingPage(QMainWindow):
    def __init__(self, widget):
        super(OverlappingPage, self).__init__()
        loadUi("Overlapping.ui", self)
        self.widget = widget

        # Initialize the table with improved properties
        self.OverlappingTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # Define stylish button stylesheet
        self.stylish_button_style = """
            QPushButton {
                background-color: #FFCCCC; /* Light red background */
                color: #B30000; /* Deep red text */
                font-size: 10pt; /* Slightly larger font */
                font-weight: bold;
                border: 2px solid #E60000; /* Vodafone red border */
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFE5E5; /* Lighter red on hover */
                border-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #FF9999;
                border-color: #990000;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """

        # Setup recommendations overlay (renamed for consistency)
        self.message_overlay = QtWidgets.QWidget(self) # Create overlay on OverlappingPage
        self.message_overlay.setGeometry(0, 0, self.width(), self.height()) # Cover the whole page
        self.message_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);") # Semi-transparent dark background
        self.message_overlay.setHidden(True)

        self.message_label = QtWidgets.QLabel(self.message_overlay)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
        self.message_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;") # White, bold text
        self.message_label.setWordWrap(True) # Enable word wrapping

        # Install event filter to hide overlay on click
        self.message_overlay.installEventFilter(self)
        
        # Populate table content
        self.populate_overlapping_table()
       
        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(lambda: self.switch_to(BadCoveragePage))
        self.Handover_Button.clicked.connect(lambda: self.switch_to(HandoverPage))
        self.Overlapping_button.clicked.connect(lambda: self.switch_to(OverlappingPage))
        self.Highload_button.clicked.connect(lambda: self.switch_to(HighLoadPage))
        self.exports_button.clicked.connect(self.return_to_main)
        self.OvershootingButton.clicked.connect(lambda: self.switch_to(OvershootingPage))

    def populate_overlapping_table(self):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            df["Dominant Problem"] = df["Dominant Problem"].ffill()

            overlap_df = df[df["Dominant Problem"].str.strip().str.lower() == "overlapping"]
            unique_spots = overlap_df.drop_duplicates(subset="Spot_Area_Num")

            self.OverlappingTable.setRowCount(len(unique_spots))
            self.OverlappingTable.setColumnCount(3)
            self.OverlappingTable.setHorizontalHeaderLabels(["Spot Area", "Recommendations", "View on Map"])

            for i, spot in enumerate(unique_spots["Spot_Area_Num"]):
                # Center aligned spot number
                spot_item = QtWidgets.QTableWidgetItem(str(spot))
                spot_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.OverlappingTable.setItem(i, 0, spot_item)

                # Recommendation button with icon
                btn_rec = QtWidgets.QPushButton("See Recommendations")
                btn_rec.setIcon(QtGui.QIcon("recommendation_icon.png")) # Add an icon if available
                btn_rec.setStyleSheet(self.stylish_button_style) # Apply the defined stylesheet
                btn_rec.setCursor(QtCore.Qt.PointingHandCursor)
                btn_rec.clicked.connect(lambda _, s=spot: self.show_recommendations(s))
                self.OverlappingTable.setCellWidget(i, 1, btn_rec)

                # Map button with icon
                btn_map = QtWidgets.QPushButton("View on Map")
                btn_map.setIcon(QtGui.QIcon("map_icon.png")) # Add a map icon if available
                btn_map.setStyleSheet(self.stylish_button_style) # Apply the defined stylesheet
                btn_map.clicked.connect(lambda _, s=spot: self.show_on_map(s))
                btn_map.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.OverlappingTable.setCellWidget(i, 2, btn_map)

            # Enhance table header appearance
            header = self.OverlappingTable.horizontalHeader()
            font = QtGui.QFont()
            font.setPointSize(12) # Increased font size
            font.setBold(True)
            header.setFont(font)
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # Stretch columns
            header.setStyleSheet("QHeaderView::section { background-color: #ecf0f1; border: 1px solid #d0d0d0; padding: 4px; }") # Keep other header styles if needed

            # Remove table borders and ensure gridline color is kept
            self.OverlappingTable.setStyleSheet("QTableWidget { border: none; gridline-color: #d0d0d0; }")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not populate Overlapping table:\n{e}")

    def show_recommendations(self, spot):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Determine the correct path based on analysis type
            if analysis_type == "thresholds":
                suggestion_path = os.path.join(base_dir, "For_Code_Results", "Overlapping_Solution", "Suggestion_Overlapping_onlybad.csv")
            elif analysis_type == "predefined":
                suggestion_path = os.path.join(base_dir, "For_ML_Results", "Overlapping_Solution", "Suggestion_Overlapping_onlybad.csv")
            else:
                # Use the custom overlay for this message too
                self.message_label.setText("Unknown analysis type.")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                return
                
            if not os.path.exists(suggestion_path):
                # Use the custom overlay for this message too
                self.message_label.setText(f"Error: CSV file not found at: {suggestion_path}")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                return
                
            # Read the CSV file
            suggestion_df = pd.read_csv(suggestion_path)
            
            # Filter for the specific spot area
            spot_data = suggestion_df[suggestion_df["Spot_Area_Num"] == spot]
            
            if spot_data.empty:
                message = f"No SINR range increase recommendation found for Spot Area: {spot}"
            else:
            # Get the SINR Range increase per Area value
                sinr_range = spot_data["SINR Range increase per Area"].values[0]
            
            # Display the recommendation using the overlay
            self.message_label.setText(f"Recommended SINR Range increase for Spot Area {spot}: {sinr_range}")
            self.message_overlay.setGeometry(0, 0, self.width(), self.height())
            self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
            self.message_overlay.raise_()
            self.message_overlay.show()
        
        except Exception as e:
            # Use the custom overlay for error messages too
            self.message_label.setText(f"Could not load recommendations:\\n{e}")
            self.message_overlay.setGeometry(0, 0, self.width(), self.height())
            self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
            self.message_overlay.raise_()
            self.message_overlay.show()

    def show_on_map(self, spot_area_num):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Map Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            filtered_df = df[df["Spot_Area_Num"] == spot_area_num]
            if filtered_df.empty:
                QMessageBox.information(self, "No Data", "No data found for this spot.")
                return
            cell_df = pd.read_excel("Uploaded_Cell.xlsx")
            cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
            cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"}.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.3, color='blue'):
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            latitudes = filtered_df["Latitude"].values
            longitudes = filtered_df["Longitude"].values
            m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=14)

            for lat, lon in zip(latitudes, longitudes):
                folium.Marker(location=[lat, lon], popup=f"Spot: {spot_area_num}").add_to(m)

            for _, row in cell_df.iterrows():
                lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                name = row["CellNAME"]
                band = row.get("Freq Band", "Unknown")
                color = get_band_color(band)
                popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                draw_sector(m, lat, lon, azimuth, popup_html, color=color)
                folium.CircleMarker(location=[lat, lon], radius=3, color=color, fill=True,
                                    fill_opacity=1, popup=f"{name} (site center)").add_to(m)

            # Create Maps directory if it doesn't exist
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)
            
            # Save map in Maps directory
            map_path = os.path.join(maps_dir, f"map_spot_{spot_area_num}.html")
            m.save(map_path)
            webbrowser.open(map_path)

        except Exception as e:
            QMessageBox.warning(self, "Map Error", f"Error generating map:\n{e}")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        # Filter clicks on the message overlay to hide it
        if obj is self.message_overlay and event.type() == QtCore.QEvent.MouseButtonPress:
            self.message_overlay.hide()
            return True # Event handled
        # If the event is not for the message overlay, pass it to the base class eventFilter
        return super().eventFilter(obj, event)


class HighLoadPage(QMainWindow):
    def __init__(self, widget):
        super(HighLoadPage, self).__init__()
        loadUi("HighLoad.ui", self)  # your UI file for HighLoad
        self.widget = widget

        # Setup recommendations overlay
        self.message_overlay = QtWidgets.QWidget(self) # Create overlay on HighLoadPage
        self.message_overlay.setGeometry(0, 0, self.width(), self.height()) # Cover the whole page
        self.message_overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);") # Semi-transparent dark background
        self.message_overlay.setHidden(True)

        self.message_label = QtWidgets.QLabel(self.message_overlay)
        self.message_label.setAlignment(QtCore.Qt.AlignCenter)
        self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
        self.message_label.setStyleSheet("color: white; font-size: 14pt; font-weight: bold;") # White, bold text
        self.message_label.setWordWrap(True) # Enable word wrapping

        # Install event filter to hide overlay on click
        self.message_overlay.installEventFilter(self)

        # Define stylish button stylesheet (matching BadCoveragePage)
        self.stylish_button_style = """
            QPushButton {
                background-color: #FFCCCC; /* Light red background */
                color: #B30000; /* Deep red text */
                font-size: 10pt; /* Slightly larger font */
                font-weight: bold;
                border: 2px solid #E60000; /* Vodafone red border */
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFE5E5; /* Lighter red on hover */
                border-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #FF9999;
                border-color: #990000;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """

        self.populate_highload_table()

    

        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(lambda: self.switch_to(BadCoveragePage))
        self.Handover_Button.clicked.connect(lambda: self.switch_to(HandoverPage))
        self.Overlapping_button.clicked.connect(lambda: self.switch_to(OverlappingPage))
        self.Highload_button.clicked.connect(lambda: self.switch_to(HighLoadPage))
        self.exports_button.clicked.connect(self.return_to_main)
        self.OvershootingButton.clicked.connect(lambda: self.switch_to(OvershootingPage))

    def populate_highload_table(self):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                # Use the custom overlay for this message too
                self.message_label.setText("Unknown analysis type.")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                return
            if not os.path.exists(csv_path):
                # Use the custom overlay for this message too
                self.message_label.setText(f"Error: CSV file not found at: {csv_path}")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                return
            df = pd.read_csv(csv_path)
            df["Dominant Problem"] = df["Dominant Problem"].ffill()

            highload_df = df[df["Dominant Problem"].str.strip().str.lower() == "high load"]
            unique_spots = highload_df.drop_duplicates(subset="Spot_Area_Num")

            # Load recommendations from Highload_Problem_SectorBands_Detailed_3.csv
            if analysis_type == "thresholds":
                highload_recommendation_path = os.path.join(base_dir, "For_Code_Results", "Highload_Solution", "Highload_Problem_SectorBands_Detailed_3.csv")
            elif analysis_type == "predefined":
                highload_recommendation_path = os.path.join(base_dir, "For_ML_Results", "Highload_Solution", "Highload_Problem_SectorBands_Detailed_3.csv")
            else:
                # Use the custom overlay for this message too
                self.message_label.setText("Unknown analysis type for recommendations.")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                return
                
            if os.path.exists(highload_recommendation_path):
                rec_df = pd.read_csv(highload_recommendation_path)
                rec_df = rec_df.drop_duplicates(subset="Spot_Area_Num", keep='first')
                rec_map = dict(zip(rec_df["Spot_Area_Num"], rec_df["Recommendation"]))
            else:
                # Use the custom overlay for this message too
                self.message_label.setText(f"Error: Recommendation file not found at: {highload_recommendation_path}")
                self.message_overlay.setGeometry(0, 0, self.width(), self.height())
                self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
                self.message_overlay.raise_()
                self.message_overlay.show()
                rec_map = {}

            self.HighLoadTable.setRowCount(len(unique_spots))
            self.HighLoadTable.setColumnCount(3)
            self.HighLoadTable.setHorizontalHeaderLabels(["Spot_Area_Num", "See Recommendations", "See on Map"])

            for i, spot in enumerate(unique_spots["Spot_Area_Num"]):
                spot_item = QtWidgets.QTableWidgetItem(str(spot))
                spot_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.HighLoadTable.setItem(i, 0, spot_item)

                # See Recommendations button
                btn_rec = QtWidgets.QPushButton("See Recommendations")
                btn_rec.setStyleSheet(self.stylish_button_style) # Apply stylish button style
                btn_rec.clicked.connect(lambda _, s=spot: self.show_highload_recommendation(s, rec_map))
                self.HighLoadTable.setCellWidget(i, 1, btn_rec)

                btn_map = QtWidgets.QPushButton("See on Map")
                btn_map.setStyleSheet(self.stylish_button_style) # Apply stylish button style
                btn_map.clicked.connect(lambda _, s=spot: self.show_on_map(s))
                btn_map.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.HighLoadTable.setCellWidget(i, 2, btn_map)

                # Enhance table header appearance by setting font directly (matching BadCoveragePage)
                header = self.HighLoadTable.horizontalHeader()
                font = QtGui.QFont()
                font.setPointSize(12) # Increased font size
                font.setBold(True)
                header.setFont(font)
                header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # Stretch columns
                header.setStyleSheet("QHeaderView::section { background-color: #ecf0f1; border: 1px solid #d0d0d0; padding: 4px; }") # Keep other header styles if needed

                # Remove table borders and ensure gridline color is kept (matching BadCoveragePage)
                # Note: Text alignment can be set per item or with a delegate if needed globally without conflicting
                self.HighLoadTable.setStyleSheet("QTableWidget { border: none; gridline-color: #d0d0d0; }")

                # Hide vertical header (row numbers) - This was already here, just keeping it.
            self.HighLoadTable.verticalHeader().setVisible(False)

        except Exception as e:
            # Use the custom overlay for error messages too
            self.message_label.setText(f"Could not populate High Load table:\\n{e}")
            self.message_overlay.setGeometry(0, 0, self.width(), self.height())
            self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
            self.message_overlay.raise_()
            self.message_overlay.show()

    def show_highload_recommendation(self, spot, rec_map):
        msg = rec_map.get(spot, "No recommendation available for this area.")
        # Use the custom overlay to display the message
        self.message_label.setText(str(msg))
        self.message_overlay.setGeometry(0, 0, self.width(), self.height())
        self.message_label.setGeometry(QtCore.QRect(0, 0, self.message_overlay.width(), self.message_overlay.height()))
        self.message_overlay.raise_()
        self.message_overlay.show()

    def show_on_map(self, spot_area_num):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Map Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            filtered_df = df[df["Spot_Area_Num"] == spot_area_num]
            if filtered_df.empty:
                QMessageBox.information(self, "No Data", "No data found for this spot.")
                return
            cell_df = pd.read_excel("Uploaded_Cell.xlsx")
            cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
            cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"}.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.3, color='blue'):
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            latitudes = filtered_df["Latitude"].values
            longitudes = filtered_df["Longitude"].values
            m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=14)

            for lat, lon in zip(latitudes, longitudes):
                folium.Marker(location=[lat, lon], popup=f"Spot: {spot_area_num}").add_to(m)

            for _, row in cell_df.iterrows():
                lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                name = row["CellNAME"]
                band = row.get("Freq Band", "Unknown")
                color = get_band_color(band)
                popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                draw_sector(m, lat, lon, azimuth, popup_html, color=color)
                folium.CircleMarker(location=[lat, lon], radius=3, color=color, fill=True,
                                    fill_opacity=1, popup=f"{name} (site center)").add_to(m)

            # Create Maps directory if it doesn't exist
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)
            
            # Save map in Maps directory
            map_path = os.path.join(maps_dir, f"map_spot_{spot_area_num}.html")
            m.save(map_path)
            webbrowser.open(map_path)

        except Exception as e:
            QMessageBox.warning(self, "Map Error", f"Error generating map:\n{e}")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        # Filter clicks on the message overlay to hide it
        if obj is self.message_overlay and event.type() == QtCore.QEvent.MouseButtonPress:
            self.message_overlay.hide()
            return True # Event handled
        # If the event is not for the message overlay, pass it to the base class eventFilter
        return super().eventFilter(obj, event)


class Insights(QMainWindow):
    def __init__(self, widget):
        super(Insights, self).__init__()
        print("DEBUG: Initializing Insights page")
        loadUi("KPIinsights.ui", self)
        self.widget = widget
        
        # Set page title
        self.setWindowTitle("KPI Insights")
        
        # Configure the modern chart style
        self._setup_chart_style()
        
        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.exports_button.clicked.connect(self.return_to_main)

        # Connect Histogram button signal
        if hasattr(self, 'Histogram_button'):
            print("DEBUG: Histogram_button found, connecting signal")
            self.Histogram_button.clicked.connect(self.goto_histogram_page)
        else:
            print("DEBUG: Warning: Histogram_button not found in KPIinsights.ui")

    def _setup_chart_style(self):
        """Configure a modern, visually appealing style for charts"""
        # Use a modern style for all plots
        plt.style.use('seaborn-v0_8-whitegrid')
        
        # Set custom colors for the application's charts
        self.color_palette = {
            "throughput": "#3498db",  # Blue
            "rsrp": "#2ecc71",        # Green
            "rsrq": "#9b59b6",        # Purple
            "sinr": "#e74c3c"         # Red
        }
        
        # Set fonts
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Verdana']
        
        # Customize other style elements
        plt.rcParams['axes.labelsize'] = 11
        plt.rcParams['axes.titlesize'] = 13
        plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams['axes.spines.top'] = False
        plt.rcParams['axes.spines.right'] = False

    def _setup_button_animations(self):
        """Add hover and click animations to the navigation buttons"""
        buttons_to_animate = [
            self.classification_button,
            self.insights_button,
            self.actions_button,
            self.exports_button,
        ]
        setup_animated_buttons(buttons_to_animate, self) # Pass self as the parent widget

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def plot_cdf_in_frame(self, frame, column_name, title, color='teal'):
        try:
            file_path = "Graphs_Divided_input.csv"
            if not os.path.exists(file_path):
                self._display_message_in_frame(frame, "No data file found")
                return

            df = pd.read_csv(file_path)

            if column_name not in df.columns:
                self._display_message_in_frame(frame, f"Column not found:\n{column_name}")
                return

            values = df[column_name].dropna().sort_values()

            if values.empty:
                self._display_message_in_frame(frame, "No valid data to plot")
                return

            # Get color from the palette
            if column_name == "PDSCH Phy Throughput (kbps)":
                plot_color = self.color_palette["throughput"]
                values = values / 1000
                xlabel = "Throughput (Mbps)"
            elif column_name == "Serving Cell RSRP (dBm)":
                plot_color = self.color_palette["rsrp"]
                xlabel = "RSRP (dBm)"
            elif column_name == "Serving Cell RSRQ (dB)":
                plot_color = self.color_palette["rsrq"]
                xlabel = "RSRQ (dB)"
            elif column_name == "Serving Cell RS SINR (dB)":
                plot_color = self.color_palette["sinr"]
                xlabel = "SINR (dB)"
            else:
                plot_color = color
                xlabel = column_name

            n = len(values)
            cdf = [(i + 1) / n for i in range(n)]

            # Create a container widget to hold both the instruction label and chart
            container = QtWidgets.QWidget()
            container_layout = QtWidgets.QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            
            # Add instructional label
            instruction_label = QtWidgets.QLabel("Click on the chart to expand")
            instruction_label.setAlignment(QtCore.Qt.AlignCenter)
            instruction_label.setStyleSheet("color: #ff0000; font-size: 9pt; font-style: italic; font-weight: bold;") # Changed color to red
            container_layout.addWidget(instruction_label)
            
            # Increase figure size to accommodate x-axis labels better
            fig, ax = plt.subplots(figsize=(6.0, 5.2), facecolor='#f8f9fa') # Further increased width and height
            
            # Plot with improved styling
            ax.plot(values, cdf, color=plot_color, linewidth=2.5, alpha=0.9)
            
            # Add fill below the line for visual emphasis
            ax.fill_between(values, 0, cdf, color=plot_color, alpha=0.2)
            
            # Add grid but make it subtle
            ax.grid(True, linestyle='--', alpha=0.7, color='#cccccc')
            
            # Improve title and labels
            ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
            ax.set_xlabel(xlabel, fontsize=10, fontweight='bold', labelpad=12) # Increased labelpad for better visibility
            ax.set_ylabel("CDF", fontsize=10, fontweight='bold', labelpad=12) # Increased labelpad for better visibility
            
            # Set more ticks for finer x-axis steps but limit number to prevent overcrowding
            if column_name == "PDSCH Phy Throughput (kbps)":
                # Use fewer ticks for better visibility
                min_val, max_val = values.min(), values.max()
                # Calculate a reasonable number of steps for the data range
                step = (max_val - min_val) / 5  # Reduced number of steps for clearer labels
                ax.set_xticks(np.linspace(min_val, max_val, 6))  # Use 6 evenly spaced ticks
                # Format throughput values with fewer decimal places
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.1f'))
            elif column_name == "Serving Cell RSRP (dBm)":
                # For RSRP, use more reasonable steps in small chart
                min_val, max_val = values.min(), values.max()
                # Round to nearest 5 for cleaner ticks
                min_val_rounded = np.floor(min_val / 5) * 5
                max_val_rounded = np.ceil(max_val / 5) * 5
                # Use 6-8 ticks for better readability
                ax.set_xticks(np.linspace(min_val_rounded, max_val_rounded, 7))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            elif column_name == "Serving Cell RSRQ (dB)":
                # For RSRQ, use more reasonable steps
                min_val, max_val = values.min(), values.max()
                # Round to nearest 2 for cleaner ticks
                min_val_rounded = np.floor(min_val / 2) * 2
                max_val_rounded = np.ceil(max_val / 2) * 2
                # Use 6-7 ticks for better readability
                ax.set_xticks(np.linspace(min_val_rounded, max_val_rounded, 6))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            elif column_name == "Serving Cell RS SINR (dB)":
                # For SINR, use more reasonable steps
                min_val, max_val = values.min(), values.max()
                # Round to nearest 3 for cleaner ticks
                min_val_rounded = np.floor(min_val / 3) * 3
                max_val_rounded = np.ceil(max_val / 3) * 3
                # Use 6-7 ticks for better readability
                ax.set_xticks(np.linspace(min_val_rounded, max_val_rounded, 7))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            elif column_name == "UE TX Power - PUSCH (dBm) Carrier 1":
                # For UE Power, use more reasonable steps in small chart (similar to RSRP)
                min_val, max_val = values.min(), values.max()
                # Round to nearest 5 for cleaner ticks
                min_val_rounded = np.floor(min_val / 5) * 5
                max_val_rounded = np.ceil(max_val / 5) * 5
                # Use 6-8 ticks for better readability
                ax.set_xticks(np.linspace(min_val_rounded, max_val_rounded, 7))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            
            # Make x-axis labels visible and prevent overlap
            ax.tick_params(axis='x', rotation=45, labelsize=10, colors='#000000', pad=8)  # Increased font size and padding
            ax.tick_params(axis='y', labelsize=9, colors='#505050')
            
            # Adjust the subplot parameters to give more room to the x-axis labels
            fig.subplots_adjust(bottom=0.30, left=0.15, right=0.95, top=0.90)  # Increased bottom margin and added left/right margins
            
            # Add a light border around the plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#dddddd')
                spine.set_linewidth(1)

            canvas = FigureCanvas(fig)

            # Make the canvas clickable to open a bigger view
            canvas.mpl_connect('button_press_event', lambda event: self._show_expanded_chart(column_name, title, plot_color))

            # Add canvas to container
            container_layout.addWidget(canvas)

            # Clear the frame's layout
            if frame.layout() is None:
                layout = QtWidgets.QVBoxLayout(frame)
                frame.setLayout(layout)
            else:
                while frame.layout().count():
                    item = frame.layout().takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)

            # Add the container to the frame
            frame.layout().addWidget(container)

        except Exception as e:
            self._display_message_in_frame(frame, f"Error:\n{str(e)}")

    def _show_expanded_chart(self, column_name, title, color):
        try:
            file_path = "Graphs_Divided_input.csv"
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Error", "No data file found")
                return

            df = pd.read_csv(file_path)
            if column_name not in df.columns:
                QMessageBox.warning(self, "Error", "Column not found")
                return

            values = df[column_name].dropna().sort_values()
            if values.empty:
                QMessageBox.warning(self, "Error", "No valid data to plot")
                return

            # Prepare data for plotting
            if column_name == "PDSCH Phy Throughput (kbps)":
                values = values / 1000
                xlabel = "Throughput (Mbps)"
            elif column_name == "Serving Cell RSRP (dBm)":
                xlabel = "RSRP (dBm)"
            elif column_name == "Serving Cell RSRQ (dB)":
                xlabel = "RSRQ (dB)"
            elif column_name == "Serving Cell RS SINR (dB)":
                xlabel = "SINR (dB)"
            elif column_name == "UE TX Power - PUSCH (dBm) Carrier 1":
                xlabel = "UE TX Power (dBm)"
            else:
                xlabel = column_name

            n = len(values)
            cdf = [(i + 1) / n for i in range(n)]

            # Create expanded figure (larger size)
            expanded_fig = plt.figure(figsize=(12, 8), facecolor='#f8f9fa')
            ax = expanded_fig.add_subplot(111)
            
            # Plot the CDF with enhanced styling
            ax.plot(values, cdf, color=color, linewidth=3, alpha=0.9)
            # Add fill below the line for visual emphasis
            ax.fill_between(values, 0, cdf, color=color, alpha=0.2)
            
            # Set detailed title and labels with improved styling
            ax.set_title(f"{title} - Detailed View", fontsize=18, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel, fontsize=14, fontweight='bold', labelpad=10)
            ax.set_ylabel("CDF", fontsize=14, fontweight='bold', labelpad=10)
            
            # Add grid but make it subtle
            ax.grid(True, linestyle='--', alpha=0.6, color='#cccccc')
            
            # Set more detailed ticks with improved spacing
            if column_name == "PDSCH Phy Throughput (kbps)":
                min_val, max_val = values.min(), values.max()
                # Use more ticks for expanded view but ensure they're evenly spaced
                ax.set_xticks(np.linspace(min_val, max_val, 15))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.1f'))
            elif column_name == "Serving Cell RSRP (dBm)":
                min_val, max_val = values.min(), values.max()
                # Round to nearest 1 for expanded view
                min_val_rounded = np.floor(min_val)
                max_val_rounded = np.ceil(max_val)
                # Calculate appropriate step size for 15-20 ticks
                range_size = max_val_rounded - min_val_rounded
                step = max(1, int(range_size / 15))  # At least 1dB steps, but more if range is large
                ax.set_xticks(np.arange(min_val_rounded, max_val_rounded + step, step))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            elif column_name == "Serving Cell RSRQ (dB)":
                min_val, max_val = values.min(), values.max()
                # For RSRQ, use 0.5dB steps in expanded view
                min_val_rounded = np.floor(min_val * 2) / 2  # Round to nearest 0.5
                max_val_rounded = np.ceil(max_val * 2) / 2
                range_size = max_val_rounded - min_val_rounded
                step = max(0.5, range_size / 15)  # Use at least 0.5dB steps
                ax.set_xticks(np.arange(min_val_rounded, max_val_rounded + step/2, step))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.1f'))
            elif column_name == "Serving Cell RS SINR (dB)":
                min_val, max_val = values.min(), values.max()
                # For SINR, use 1dB steps in expanded view
                min_val_rounded = np.floor(min_val)
                max_val_rounded = np.ceil(max_val)
                range_size = max_val_rounded - min_val_rounded
                step = max(1, int(range_size / 15))  # At least 1dB steps
                ax.set_xticks(np.arange(min_val_rounded, max_val_rounded + step, step))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            elif column_name == "UE TX Power - PUSCH (dBm) Carrier 1":
                # For UE Power, use more reasonable steps in small chart (similar to RSRP)
                min_val, max_val = values.min(), values.max()
                # Round to nearest 5 for cleaner ticks
                min_val_rounded = np.floor(min_val / 5) * 5
                max_val_rounded = np.ceil(max_val / 5) * 5
                # Calculate appropriate step size for 15-20 ticks (similar to RSRP expanded view)
                range_size = max_val_rounded - min_val_rounded
                step = max(1, int(range_size / 15))  # At least 1dB steps
                # Use 6-8 ticks for better readability
                ax.set_xticks(np.arange(min_val_rounded, max_val_rounded + step/2, step))
                ax.xaxis.set_major_formatter(plt.FormatStrFormatter('%.0f'))
            
            # Enhance tick appearance
            ax.tick_params(axis='x', rotation=45, labelsize=11, colors='#505050', pad=8)
            ax.tick_params(axis='y', labelsize=11, colors='#505050', pad=8)
            
            # Add vertical lines for key percentiles
            percentiles = [0.1, 0.5, 0.9]  # 10th, 50th (median), 90th percentiles
            percentile_values = [float(np.percentile(values, p*100)) for p in percentiles]
            percentile_labels = ["10th", "50th\n(Median)", "90th"]
            percentile_colors = ["#ff9800", "#e91e63", "#9c27b0"]  # Orange, Pink, Purple
            
            for i, (p, val, label) in enumerate(zip(percentiles, percentile_values, percentile_labels)):
                ax.axvline(x=val, color=percentile_colors[i], linestyle='--', linewidth=1.5, alpha=0.7)
                ax.text(val, 0.02, f"{label}\n{val:.2f}", 
                        ha='center', va='bottom', fontsize=10, color=percentile_colors[i],
                        bbox=dict(boxstyle="round,pad=0.3", fc='white', ec=percentile_colors[i], alpha=0.8))
            
            # Add statistical information with better formatting
            stats_text = (f"Statistics:\n"
                         f"Min: {values.min():.2f}\n"
                         f"Max: {values.max():.2f}\n"
                         f"Mean: {values.mean():.2f}\n"
                         f"Median: {values.median():.2f}\n"
                         f"Std Dev: {values.std():.2f}\n"
                         f"Total Samples: {len(values)}")
            
            ax.text(0.01, 0.97, stats_text, transform=ax.transAxes, 
                   bbox=dict(boxstyle="round,pad=0.5", facecolor='white', alpha=0.8, edgecolor='#cccccc'),
                   fontsize=11, verticalalignment='top')
            
            # Add a light border around the plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#dddddd')
                spine.set_linewidth(1)
            
            # Adjust layout to ensure all elements are visible
            expanded_fig.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.90)
            
            # Create a new dialog to display the expanded chart
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"{title} - Expanded View")
            dialog.setMinimumSize(900, 600)
            
            layout = QtWidgets.QVBoxLayout(dialog)
            expanded_canvas = FigureCanvas(expanded_fig)
            layout.addWidget(expanded_canvas)
            
            # Add a close button with better styling
            close_btn = QtWidgets.QPushButton("Close")
            close_btn.setStyleSheet("padding: 8px 16px; font-weight: bold; color: #ff0000; background-color: #e0e0e0;")
            close_btn.setMinimumWidth(120)
            close_btn.setMaximumWidth(120)
            close_btn.clicked.connect(dialog.close)
            
            # Add button container for centering
            button_container = QtWidgets.QWidget()
            button_layout = QtWidgets.QHBoxLayout(button_container)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            button_layout.addStretch()
            layout.addWidget(button_container)
            
            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to show expanded chart: {str(e)}")
       
    def _display_message_in_frame(self, frame, message):
        if frame.layout() is None:
            layout = QtWidgets.QVBoxLayout(frame)
            frame.setLayout(layout)
        else:
            while frame.layout().count():
                item = frame.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        label = QtWidgets.QLabel(message)
        label.setAlignment(QtCore.Qt.AlignCenter)
        frame.layout().addWidget(label)

    def refresh_insights_charts(self):
        # Check if the data file exists before plotting
        file_path = "Graphs_Divided_input.csv"
        if not os.path.exists(file_path):
            for frame in [self.throughput_frame, self.RSRP_frame, self.RSRQ_frame, self.SINR_frame]:
                self._display_message_in_frame(frame, "No data file found")
            return
            
        self.plot_cdf_in_frame(self.throughput_frame, "PDSCH Phy Throughput (kbps)", "Throughput CDF", color='orange')
        self.plot_cdf_in_frame(self.RSRP_frame, "Serving Cell RSRP (dBm)", "RSRP CDF", color='blue')
        self.plot_cdf_in_frame(self.RSRQ_frame, "Serving Cell RSRQ (dB)", "RSRQ CDF", color='green')
        self.plot_cdf_in_frame(self.SINR_frame, "Serving Cell RS SINR (dB)", "SINR CDF", color='purple')
        # Add CDF for UE TX Power
        try:
            self.plot_cdf_in_frame(self.UE_Power_frame, "UE TX Power - PUSCH (dBm) Carrier 1", "UE TX Power CDF", color='brown')
        except AttributeError:
            print("Warning: UE_Power_frame not found in KPIinsights.ui")

        # Ensure label_7 has a white background
        try:
            label7 = getattr(self, 'label_7', None)
            if label7 and isinstance(label7, QtWidgets.QLabel):
                label7.setStyleSheet("background-color: white; font: 75 16pt \"Century Gothic\";")
        except Exception as e:
            print(f"Error applying white background to label_7: {e}")

    def goto_histogram_page(self):
        """Navigate to the Histogram Page."""
        print("DEBUG: goto_histogram_page called")
        self.switch_to(HistogramPage)


class HandoverPage(QMainWindow):
    def __init__(self, widget):
        super(HandoverPage, self).__init__()
        loadUi("Handover.ui", self)
        self.widget = widget

        # Define stylish button stylesheet
        self.stylish_button_style = """
            QPushButton {
                background-color: #FFCCCC; /* Light red background */
                color: #B30000; /* Deep red text */
                font-size: 10pt; /* Slightly larger font */
                font-weight: bold;
                border: 2px solid #E60000; /* Vodafone red border */
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFE5E5; /* Lighter red on hover */
                border-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #FF9999;
                border-color: #990000;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """

        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(lambda: self.switch_to(BadCoveragePage))
        self.Handover_Button.clicked.connect(lambda: self.switch_to(HandoverPage))
        self.Overlapping_button.clicked.connect(lambda: self.switch_to(OverlappingPage))
        self.Highload_button.clicked.connect(lambda: self.switch_to(HighLoadPage))
        self.exports_button.clicked.connect(self.return_to_main)
        self.OvershootingButton.clicked.connect(lambda: self.switch_to(OvershootingPage))
        
        # Populate handover tables after defining stylish_button_style
        self.populate_handover_tables()

    def populate_handover_tables(self):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            df["Dominant Problem"] = df["Dominant Problem"].ffill()

            # Normalize the Predicted Dominant Problem column
            df["Dominant Problem"] = df["Dominant Problem"].astype(str).str.strip().str.lower()

            intra_df = df[df["Dominant Problem"] == "intra-frequency handover"].drop_duplicates(subset="Spot_Area_Num")
            inter_df = df[df["Dominant Problem"] == "inter-frequency handover"].drop_duplicates(subset="Spot_Area_Num")

            self._populate_table(self.IntraTable, intra_df)
            self._populate_table(self.InterTable, inter_df)

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not populate handover tables:\n{e}")


    def _populate_table(self, table, df):
        table.setRowCount(len(df))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Spot_Area_Num", "See on Map"])

        # Enhance table header appearance
        header = table.horizontalHeader()
        font = QtGui.QFont()
        font.setPointSize(12) # Increased font size
        font.setBold(True)
        header.setFont(font)
        header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # Stretch columns
        header.setStyleSheet("QHeaderView::section { background-color: #ecf0f1; border: 1px solid #d0d0d0; padding: 4px; }") # Keep other header styles if needed

        # Remove table borders and ensure gridline color is kept
        # Note: Text alignment can be set per item or with a delegate if needed globally without conflicting
        table.setStyleSheet("QTableWidget { border: none; gridline-color: #d0d0d0; }")

        for i, spot in enumerate(df["Spot_Area_Num"]):
            spot_item = QtWidgets.QTableWidgetItem(str(spot))
            spot_item.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(i, 0, spot_item)

            btn_map = QtWidgets.QPushButton("See on Map")
            btn_map.setStyleSheet(self.stylish_button_style) # Apply the defined stylesheet
            btn_map.setCursor(QtCore.Qt.PointingHandCursor) # Add pointing hand cursor
            btn_map.clicked.connect(lambda _, s=spot: self.show_on_map(s))
            table.setCellWidget(i, 1, btn_map)

    def show_recommendations(self, spot):
        QMessageBox.information(self, "Recommendations", f"Showing recommendations for Spot Area: {spot}")

    def show_on_map(self, spot_area_num):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Map Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            filtered_df = df[df["Spot_Area_Num"] == spot_area_num]
            if filtered_df.empty:
                QMessageBox.information(self, "No Data", "No data found for this spot.")
                return
            cell_df = pd.read_excel("Uploaded_Cell.xlsx")
            cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
            cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {
                    1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"
                }.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.3, color='blue'):
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            latitudes = filtered_df["Latitude"].values
            longitudes = filtered_df["Longitude"].values
            m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=14)

            for lat, lon in zip(latitudes, longitudes):
                folium.Marker(location=[lat, lon], popup=f"Spot: {spot_area_num}").add_to(m)

            for _, row in cell_df.iterrows():
                lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                name = row["CellNAME"]
                band = row.get("Freq Band", "Unknown")
                color = get_band_color(band)
                popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                draw_sector(m, lat, lon, azimuth, popup_html, color=color)
                folium.CircleMarker(location=[lat, lon], radius=3, color=color, fill=True,
                                    fill_opacity=1, popup=f"{name} (site center)").add_to(m)

            # Create Maps directory if it doesn't exist
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)
            
            # Save map in Maps directory
            map_path = os.path.join(maps_dir, f"map_spot_{spot_area_num}.html")
            m.save(map_path)
            webbrowser.open(map_path)

        except Exception as e:
            QMessageBox.warning(self, "Map Error", f"Error generating map:\n{e}")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)


class Actions(QMainWindow):
    def __init__(self, widget):
        super(Actions, self).__init__()
        loadUi("Recommendations.ui", self)
        self.widget = widget

        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(self.show_bad_coverage_recommendations_on_map)
        self.Overlapping_button_2.clicked.connect(self.show_overlapping_recommendations_on_map)
        self.HighLoad_button.clicked.connect(self.show_highload_recommendations_on_map)
        self.exports_button.clicked.connect(self.return_to_main)

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)

    def show_bad_coverage_recommendations_on_map(self):
       
        try:
            import os
            import pandas as pd
            import folium
            import webbrowser
            import math

            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))

            if analysis_type == "thresholds":
                problem_areas_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_Code_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            elif analysis_type == "predefined":
                problem_areas_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_ML_Results", "Bad_Coverage_Solution", "Suggestion_BadCoverage_onlybad.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return

            if not os.path.exists(problem_areas_path):
                QMessageBox.warning(self, "Map Error", f"Problem areas CSV not found at: {problem_areas_path}")
                return
            if not os.path.exists(suggestion_path):
                QMessageBox.warning(self, "Map Error", f"Suggestion CSV not found at: {suggestion_path}")
                return

            # Load dataframes
            df_problems = pd.read_csv(problem_areas_path)
            df_suggestions = pd.read_csv(suggestion_path)

            # Filter for Bad Coverage and get unique spots with Lat/Lon
            bad_coverage_spots = df_problems[
                df_problems["Dominant Problem"].astype(str).str.strip().str.lower() == "bad coverage"
            ].drop_duplicates(subset="Spot_Area_Num")

            if bad_coverage_spots.empty:
                QMessageBox.information(self, "Map Info", "No Bad Coverage areas found to display on map.")
                return

            # Create a map of spot areas to recommendations
            # Ensure only the first recommendation per spot area is considered
            df_suggestions_unique = df_suggestions.drop_duplicates(subset="Spot_Area_Num", keep='first')

            recommendation_map = {}
            if "RSRP Range increase per Area" in df_suggestions_unique.columns:
                recommendation_map = dict(zip(df_suggestions_unique["Spot_Area_Num"], df_suggestions_unique["RSRP Range increase per Area"].fillna("No specific recommendation")))
            else:
                QMessageBox.warning(self, "Map Warning", "'RSRP Range increase per Area' column not found in suggestion file.")
                # Provide a default empty map or handle as needed
                recommendation_map = {spot: "Recommendation not available" for spot in bad_coverage_spots["Spot_Area_Num"]}


            # Create Folium map centered on the first Bad Coverage spot
            initial_location = [bad_coverage_spots.iloc[0]["Latitude"], bad_coverage_spots.iloc[0]["Longitude"]]
            m = folium.Map(location=initial_location, zoom_start=14)

            # Add markers for each Bad Coverage spot with recommendation popup
            for index, row in bad_coverage_spots.iterrows():
                spot_num = row["Spot_Area_Num"]
                lat = row["Latitude"]
                lon = row["Longitude"]
                recommendation = recommendation_map.get(spot_num, "No recommendation available")

                # Ensure latitude and longitude are not NaN
                if pd.notna(lat) and pd.notna(lon):
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(f"<b>Spot Area:</b> {spot_num}<br><b>Recommendation:</b> {recommendation}", max_width=300),
                        icon=folium.Icon(color='red', icon='info-sign') # Use a distinct icon/color
                    ).add_to(m)
                else:
                    print(f"Warning: Skipping spot {spot_num} due to missing Lat/Lon.")

            # --- Start: Cell Drawing Logic ---
            cell_file_path = os.path.join(base_dir, "Uploaded_Cell.xlsx")
            if not os.path.exists(cell_file_path):
                QMessageBox.warning(self, "Map Warning", f"Cell file not found at: {cell_file_path}. Cannot draw sectors.")
                cell_df = pd.DataFrame() # Create empty DataFrame to avoid errors
            else:
                cell_df = pd.read_excel(cell_file_path)
                cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
                cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {
                    1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"
                }.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.1, color='blue'): # Set radius_km to 0.1 for small sectors
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            # Add sectors to the map from cell_df, only if cell_df is not empty
            if not cell_df.empty:
                for _, row in cell_df.iterrows():
                    lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                    name = row["CellNAME"]
                    band = row.get("Freq Band", "Unknown")
                    color = get_band_color(band)
                    popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                    # Draw the sector with a small radius
                    draw_sector(m, lat, lon, azimuth, popup_html, color=color, radius_km=0.1) # Ensure small radius here too
                    folium.CircleMarker(location=[lat, lon], radius=2, color=color, fill=True,
                                        fill_opacity=1, popup=f"{name} (site center)").add_to(m)
            # --- End: Cell Drawing Logic ---


            # Create Maps directory if it\'s not an error
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)

            # Save map
            map_path = os.path.join(maps_dir, "bad_coverage_recommendations_map.html")
            m.save(map_path)

            # Open map in browser
            webbrowser.open(map_path)

        except FileNotFoundError as e:
            QMessageBox.critical(self, "File Error", f"Required file not found:\\n{e}")
        except KeyError as e:
            QMessageBox.critical(self, "Data Error", f"Missing expected column in data:\\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Map Error", f"Error generating map:\\n{e}")

    def show_overlapping_recommendations_on_map(self):

        try:
            import os
            import pandas as pd
            import folium
            import webbrowser
            import math

            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))

            if analysis_type == "thresholds":
                problem_areas_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_Code_Results", "Overlapping_Solution", "Suggestion_Overlapping_onlybad.csv")
            elif analysis_type == "predefined":
                problem_areas_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_ML_Results", "Overlapping_Solution", "Suggestion_Overlapping_onlybad.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return

            if not os.path.exists(problem_areas_path):
                QMessageBox.warning(self, "Map Error", f"Problem areas CSV not found at: {problem_areas_path}")
                return
            if not os.path.exists(suggestion_path):
                QMessageBox.warning(self, "Map Error", f"Suggestion CSV not found at: {suggestion_path}")
                return

            # Load dataframes
            df_problems = pd.read_csv(problem_areas_path)
            df_suggestions = pd.read_csv(suggestion_path)

            # Filter for Overlapping and get unique spots with Lat/Lon
            overlapping_spots = df_problems[
                df_problems["Dominant Problem"].astype(str).str.strip().str.lower() == "overlapping"
            ].drop_duplicates(subset="Spot_Area_Num")

            if overlapping_spots.empty:
                QMessageBox.information(self, "Map Info", "No Overlapping areas found to display on map.")
                return

            # Create a map of spot areas to recommendations
            # Ensure only the first recommendation per spot area is considered
            df_suggestions_unique = df_suggestions.drop_duplicates(subset="Spot_Area_Num", keep='first')

            recommendation_map = {}
            if "SINR Range increase per Area" in df_suggestions_unique.columns:
                recommendation_map = dict(zip(df_suggestions_unique["Spot_Area_Num"], df_suggestions_unique["SINR Range increase per Area"].fillna("No specific recommendation")))
            else:
                QMessageBox.warning(self, "Map Warning", "'SINR Range increase per Area' column not found in suggestion file.")
                # Provide a default empty map or handle as needed
                recommendation_map = {spot: "Recommendation not available" for spot in overlapping_spots["Spot_Area_Num"]}


            # Create Folium map centered on the first Bad Coverage spot
            initial_location = [overlapping_spots.iloc[0]["Latitude"], overlapping_spots.iloc[0]["Longitude"]]
            m = folium.Map(location=initial_location, zoom_start=14)

            # Add markers for each Overlapping spot with recommendation popup
            for index, row in overlapping_spots.iterrows():
                spot_num = row["Spot_Area_Num"]
                lat = row["Latitude"]
                lon = row["Longitude"]
                recommendation = recommendation_map.get(spot_num, "No recommendation available")

                # Ensure latitude and longitude are not NaN
                if pd.notna(lat) and pd.notna(lon):
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(f"<b>Spot Area:</b> {spot_num}<br><b>Recommendation:</b> {recommendation}", max_width=300),
                        icon=folium.Icon(color='red', icon='info-sign') # Use a distinct icon/color
                    ).add_to(m)
                else:
                    print(f"Warning: Skipping spot {spot_num} due to missing Lat/Lon.")

            # --- Start: Cell Drawing Logic ---
            cell_file_path = os.path.join(base_dir, "Uploaded_Cell.xlsx")
            if not os.path.exists(cell_file_path):
                QMessageBox.warning(self, "Map Warning", f"Cell file not found at: {cell_file_path}. Cannot draw sectors.")
                cell_df = pd.DataFrame() # Create empty DataFrame to avoid errors
            else:
                cell_df = pd.read_excel(cell_file_path)
                cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
                cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {
                    1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"
                }.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.1, color='blue'): # Set radius_km to 0.1 for small sectors
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            # Add sectors to the map from cell_df, only if cell_df is not empty
            if not cell_df.empty:
                for _, row in cell_df.iterrows():
                    lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                    name = row["CellNAME"]
                    band = row.get("Freq Band", "Unknown")
                    color = get_band_color(band)
                    popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                    # Draw the sector with a small radius
                    draw_sector(m, lat, lon, azimuth, popup_html, color=color, radius_km=0.1) # Ensure small radius here too
                    folium.CircleMarker(location=[lat, lon], radius=2, color=color, fill=True,
                                        fill_opacity=1, popup=f"{name} (site center)").add_to(m)
            # --- End: Cell Drawing Logic ---


            # Create Maps directory if it\'s not an error
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)

            # Save map
            map_path = os.path.join(maps_dir, "overlapping_recommendations_map.html")
            m.save(map_path)

            # Open map in browser
            webbrowser.open(map_path)

        except FileNotFoundError as e:
            QMessageBox.critical(self, "File Error", f"Required file not found:\\n{e}")
        except KeyError as e:
            QMessageBox.critical(self, "Data Error", f"Missing expected column in data:\\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Map Error", f"Error generating map:\\n{e}")

    def show_highload_recommendations_on_map(self):

        try:
            import os
            import pandas as pd
            import folium
            import webbrowser
            import math

            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))

            if analysis_type == "thresholds":
                problem_areas_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_Code_Results", "Highload_Solution", "Highload_Problem_SectorBands_Detailed_3.csv")
            elif analysis_type == "predefined":
                problem_areas_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
                suggestion_path = os.path.join(base_dir, "For_ML_Results", "Highload_Solution", "Highload_Problem_SectorBands_Detailed_3.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return

            if not os.path.exists(problem_areas_path):
                QMessageBox.warning(self, "Map Error", f"Problem areas CSV not found at: {problem_areas_path}")
                return
            if not os.path.exists(suggestion_path):
                QMessageBox.warning(self, "Map Error", f"Suggestion CSV not found at: {suggestion_path}")
                return

            # Load dataframes
            df_problems = pd.read_csv(problem_areas_path)
            df_suggestions = pd.read_csv(suggestion_path)

            # Filter for High Load and get unique spots with Lat/Lon
            high_load_spots = df_problems[
                df_problems["Dominant Problem"].astype(str).str.strip().str.lower() == "high load"
            ].drop_duplicates(subset="Spot_Area_Num")

            if high_load_spots.empty:
                QMessageBox.information(self, "Map Info", "No High Load areas found to display on map.")
                return

            # Create a map of spot areas to recommendations
            # Ensure only the first recommendation per spot area is considered
            df_suggestions_unique = df_suggestions.drop_duplicates(subset="Spot_Area_Num", keep='first')

            recommendation_map = {}
            if "Recommendation" in df_suggestions_unique.columns:
                recommendation_map = dict(zip(df_suggestions_unique["Spot_Area_Num"], df_suggestions_unique["Recommendation"].fillna("No specific recommendation")))
            else:
                QMessageBox.warning(self, "Map Warning", "'Recommendation' column not found in suggestion file.")
                # Provide a default empty map or handle as needed
                recommendation_map = {spot: "Recommendation not available" for spot in high_load_spots["Spot_Area_Num"]}


            # Create Folium map centered on the first High Load spot
            initial_location = [high_load_spots.iloc[0]["Latitude"], high_load_spots.iloc[0]["Longitude"]]
            m = folium.Map(location=initial_location, zoom_start=14)

            # Add markers for each High Load spot with recommendation popup
            for index, row in high_load_spots.iterrows():
                spot_num = row["Spot_Area_Num"]
                lat = row["Latitude"]
                lon = row["Longitude"]
                recommendation = recommendation_map.get(spot_num, "No recommendation available")

                # Ensure latitude and longitude are not NaN
                if pd.notna(lat) and pd.notna(lon):
                    folium.Marker(
                        location=[lat, lon],
                        popup=folium.Popup(f"<b>Spot Area:</b> {spot_num}<br><b>Recommendation:</b> {recommendation}", max_width=300),
                        icon=folium.Icon(color='red', icon='info-sign') # Use a distinct icon/color
                    ).add_to(m)
                else:
                    print(f"Warning: Skipping spot {spot_num} due to missing Lat/Lon.")

            # --- Start: Cell Drawing Logic ---
            cell_file_path = os.path.join(base_dir, "Uploaded_Cell.xlsx")
            if not os.path.exists(cell_file_path):
                QMessageBox.warning(self, "Map Warning", f"Cell file not found at: {cell_file_path}. Cannot draw sectors.")
                cell_df = pd.DataFrame() # Create empty DataFrame to avoid errors
            else:
                cell_df = pd.read_excel(cell_file_path)
                cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
                cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {
                    1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"
                }.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.1, color='blue'): # Set radius_km to 0.1 for small sectors
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            # Add sectors to the map from cell_df, only if cell_df is not empty
            if not cell_df.empty:
                for _, row in cell_df.iterrows():
                    lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                    name = row["CellNAME"]
                    band = row.get("Freq Band", "Unknown")
                    color = get_band_color(band)
                    popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                    # Draw the sector with a small radius
                    draw_sector(m, lat, lon, azimuth, popup_html, color=color, radius_km=0.1) # Ensure small radius here too
                    folium.CircleMarker(location=[lat, lon], radius=2, color=color, fill=True,
                                        fill_opacity=1, popup=f"{name} (site center)").add_to(m)
            # --- End: Cell Drawing Logic ---


            # Create Maps directory if it\'s not an error
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)

            # Save map
            map_path = os.path.join(maps_dir, "highload_recommendations_map.html")
            m.save(map_path)

            # Open map in browser
            webbrowser.open(map_path)

        except FileNotFoundError as e:
            QMessageBox.critical(self, "File Error", f"Required file not found:\\n{e}")
        except KeyError as e:
            QMessageBox.critical(self, "Data Error", f"Missing expected column in data:\\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Map Error", f"Error generating map:\\n{e}")




class OvershootingPage(QMainWindow):
    def __init__(self, widget):
        super(OvershootingPage, self).__init__()
        loadUi("Overshooting.ui", self)  # UI file for Overshooting
        self.widget = widget
        
        # Initialize table
        self.OvershootingTable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # Define stylish button stylesheet
        self.stylish_button_style = """
            QPushButton {
                background-color: #FFCCCC; /* Light red background */
                color: #B30000; /* Deep red text */
                font-size: 10pt; /* Slightly larger font */
                font-weight: bold;
                border: 2px solid #E60000; /* Vodafone red border */
                border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #FFE5E5; /* Lighter red on hover */
                border-color: #CC0000;
            }
            QPushButton:pressed {
                background-color: #FF9999;
                border-color: #990000;
                padding-top: 7px;
                padding-bottom: 3px;
            }
        """
        
        self.populate_overshooting_table()

        # Button connections for full navigation
        self.classification_button.clicked.connect(lambda: self.switch_to(Classification))
        self.insights_button.clicked.connect(lambda: self.switch_to(Insights))
        self.actions_button.clicked.connect(lambda: self.switch_to(Actions))
        self.bad_coverage_button.clicked.connect(lambda: self.switch_to(BadCoveragePage))
        self.Handover_Button.clicked.connect(lambda: self.switch_to(HandoverPage))
        self.Overlapping_button.clicked.connect(lambda: self.switch_to(OverlappingPage))
        self.Highload_button.clicked.connect(lambda: self.switch_to(HighLoadPage))
        self.OvershootingButton.clicked.connect(lambda: self.switch_to(OvershootingPage))
        self.exports_button.clicked.connect(self.return_to_main)


    def populate_overshooting_table(self):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            df["Dominant Problem"] = df["Dominant Problem"].ffill()

            overshooting_df = df[df["Dominant Problem"].str.strip().str.lower() == "overshooting"]
            unique_spots = overshooting_df.drop_duplicates(subset="Spot_Area_Num")

            self.OvershootingTable.setRowCount(len(unique_spots))
            self.OvershootingTable.setColumnCount(3)
            self.OvershootingTable.setHorizontalHeaderLabels(["Spot Area", "Recommendations", "View on Map"])

            for i, spot in enumerate(unique_spots["Spot_Area_Num"]):
                # Spot number with center alignment
                spot_item = QtWidgets.QTableWidgetItem(str(spot))
                spot_item.setTextAlignment(QtCore.Qt.AlignCenter)
                self.OvershootingTable.setItem(i, 0, spot_item)

                # Recommendation button with icon
                btn_rec = QtWidgets.QPushButton("See Recommendations")
                btn_rec.setIcon(QtGui.QIcon("recommendation_icon.png"))  # Add icon if available
                btn_rec.setStyleSheet(self.stylish_button_style)
                btn_rec.setCursor(QtCore.Qt.PointingHandCursor)
                btn_rec.clicked.connect(lambda _, s=spot: self.show_recommendations(s))
                self.OvershootingTable.setCellWidget(i, 1, btn_rec)

                # Map button with icon
                btn_map = QtWidgets.QPushButton("View on Map")
                btn_map.setIcon(QtGui.QIcon("map_icon.png"))  # Add map icon if available
                btn_map.setStyleSheet(self.stylish_button_style)
                btn_map.clicked.connect(lambda _, s=spot: self.show_on_map(s))
                btn_map.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
                self.OvershootingTable.setCellWidget(i, 2, btn_map)

            # Enhance table header appearance by setting font directly
            header = self.OvershootingTable.horizontalHeader()
            font = QtGui.QFont()
            font.setPointSize(12) # Increased font size
            font.setBold(True)
            header.setFont(font)
            header.setSectionResizeMode(QtWidgets.QHeaderView.Stretch) # Stretch columns
            header.setStyleSheet("QHeaderView::section { background-color: #ecf0f1; border: 1px solid #d0d0d0; padding: 4px; }") # Keep other header styles if needed

            # Remove table borders and ensure gridline color is kept
            # Note: Text alignment can be set per item or with a delegate if needed globally without conflicting
            self.OvershootingTable.setStyleSheet("QTableWidget { border: none; gridline-color: #d0d0d0; }")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not populate Overshooting table:\n{e}")

    def show_recommendations(self, spot):
        QMessageBox.information(self, "Recommendations", f"Showing recommendations for Spot Area: {spot}")

    def show_on_map(self, spot_area_num):
        try:
            import os
            analysis_type = getattr(self.widget, 'selected_analysis_type', None)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            if analysis_type == "thresholds":
                csv_path = os.path.join(base_dir, "For_Code_Results", "Problem_Areas_Code_Output.csv")
            elif analysis_type == "predefined":
                csv_path = os.path.join(base_dir, "For_ML_Results", "Problem_Areas_ML_Output.csv")
            else:
                QMessageBox.warning(self, "Map Error", "Unknown analysis type.")
                return
            if not os.path.exists(csv_path):
                QMessageBox.warning(self, "Map Error", f"CSV file not found at: {csv_path}")
                return
            df = pd.read_csv(csv_path)
            filtered_df = df[df["Spot_Area_Num"] == spot_area_num]
            if filtered_df.empty:
                QMessageBox.information(self, "No Data", "No data found for this spot.")
                return
            cell_df = pd.read_excel("Uploaded_Cell.xlsx")
            cell_df["AZIMUTH"] = pd.to_numeric(cell_df["AZIMUTH"], errors="coerce")
            cell_df = cell_df.dropna(subset=["Latitude", "Longitude", "AZIMUTH"])

            def get_band_color(band):
                try:
                    band = int(band)
                except:
                    return "gray"
                return {1800: "red", 2100: "blue", 900: "green", 2600: "purple", 800: "orange"}.get(band, "gray")

            def draw_sector(map_obj, lat, lon, azimuth, popup_text, beamwidth=60, radius_km=0.3, color='blue'):
                import math
                points = []
                steps = 10
                start_angle = azimuth - beamwidth / 2
                end_angle = azimuth + beamwidth / 2
                for angle in range(int(start_angle), int(end_angle) + 1, int(beamwidth / steps)):
                    rad = math.radians(angle)
                    dlat = radius_km * math.cos(rad) / 111
                    dlon = radius_km * math.sin(rad) / (111 * math.cos(math.radians(lat)))
                    points.append([lat + dlat, lon + dlon])
                points.insert(0, [lat, lon])
                folium.Polygon(locations=points, color=color, fill=True, fill_opacity=0.3,
                               popup=folium.Popup(popup_text, max_width=300)).add_to(map_obj)

            latitudes = filtered_df["Latitude"].values
            longitudes = filtered_df["Longitude"].values
            m = folium.Map(location=[latitudes[0], longitudes[0]], zoom_start=14)

            for lat, lon in zip(latitudes, longitudes):
                folium.Marker(location=[lat, lon], popup=f"Spot: {spot_area_num}").add_to(m)

            for _, row in cell_df.iterrows():
                lat, lon, azimuth = row["Latitude"], row["Longitude"], row["AZIMUTH"]
                name = row["CellNAME"]
                band = row.get("Freq Band", "Unknown")
                color = get_band_color(band)
                popup_html = f"<b>Cell:</b> {name}<br><b>Band:</b> {band}<br><b>Azimuth:</b> {azimuth}°"
                draw_sector(m, lat, lon, azimuth, popup_html, color=color)
                folium.CircleMarker(location=[lat, lon], radius=3, color=color, fill=True,
                                    fill_opacity=1, popup=f"{name} (site center)").add_to(m)

            # Create Maps directory if it doesn't exist
            maps_dir = os.path.join(base_dir, "Maps")
            os.makedirs(maps_dir, exist_ok=True)
            
            # Save map in Maps directory
            map_path = os.path.join(maps_dir, f"map_spot_{spot_area_num}.html")
            m.save(map_path)
            webbrowser.open(map_path)

        except Exception as e:
            QMessageBox.warning(self, "Map Error", f"Error generating map:\n{e}")

    def switch_to(self, target):
        window = target(self.widget)
        self.widget.addWidget(window)
        self.widget.setCurrentWidget(window)

    def return_to_main(self):
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)


class HistogramPage(QMainWindow):
    def __init__(self, widget):
        super(HistogramPage, self).__init__()
        print("DEBUG: Initializing HistogramPage")
        loadUi("HistogramPage.ui", self)  # Load your new .ui file
        self.widget = widget

        # Ensure label_7 has a white background
        try:
            label7 = getattr(self, 'label_7', None)
            if label7 and isinstance(label7, QtWidgets.QLabel):
                label7.setStyleSheet("background-color: white; font: 75 16pt \"Century Gothic\";")
        except Exception as e:
            print(f"Error applying white background to label_7: {e}")

        # Connect navigation buttons
        # Assuming 'exports_button' exists and is for returning to main
        if hasattr(self, 'exports_button'):
            self.exports_button.clicked.connect(self.return_to_main)
        else:
            print("Warning: exports_button not found in HistogramPage.ui")

        # Add a back button or similar navigation if needed
        # For example, assuming you have a 'back_button' in HistogramPage.ui:
        # self.back_button.clicked.connect(self.return_to_insights)

        # Connect CDF_button signal to return to Insights page
        if hasattr(self, 'CDF_button'):
            print("DEBUG: CDF_button found, connecting signal")
            self.CDF_button.clicked.connect(self.return_to_insights)
        else:
            print("Warning: CDF_button not found in HistogramPage.ui")

        # Plot histograms for KPIs
        self.plot_histograms()

    def return_to_insights(self):
        """Return to the Insights page."""
        print("DEBUG: return_to_insights called from HistogramPage")
        # Find the Insights page in the stack or create a new one
        insights_window = None
        for i in range(self.widget.count()):
            if isinstance(self.widget.widget(i), Insights):
                insights_window = self.widget.widget(i)
                break
        
        if insights_window:
            self.widget.setCurrentWidget(insights_window)
        else:
            # If for some reason Insights page is not in stack, go back to main or recreate
            print("Insights page not found in stack, returning to main.")
            while self.widget.count() > 1:
                self.widget.removeWidget(self.widget.widget(1))
            self.widget.setCurrentIndex(0)

    def plot_histograms(self):
        """Plots the histograms for different KPIs in their respective frames."""
        # Use try-except to handle potential AttributeError if frames are not found
        try:
            self._plot_single_histogram(self.throughput_histogram_frame, "PDSCH Phy Throughput (kbps)", "Throughput Histogram", color='#3498db')
        except AttributeError:
            print("Warning: throughput_histogram_frame not found in HistogramPage.ui")

        try:
            self._plot_single_histogram(self.rsrp_histogram_frame, "Serving Cell RSRP (dBm)", "RSRP Histogram", color='#2ecc71')
        except AttributeError:
            print("Warning: rsrp_histogram_frame not found in HistogramPage.ui")

        try:
            self._plot_single_histogram(self.rsrq_histogram_frame, "Serving Cell RSRQ (dB)", "RSRQ Histogram", color='#9b59b6')
        except AttributeError:
            print("Warning: rsrq_histogram_frame not found in HistogramPage.ui")

        try:
            self._plot_single_histogram(self.sinr_histogram_frame, "Serving Cell RS SINR (dB)", "SINR Histogram", color='#e74c3c')
        except AttributeError:
            print("Warning: sinr_histogram_frame not found in HistogramPage.ui")

        # Add Histogram for UE TX Power
        try:
            self._plot_single_histogram(self.UE_Power_frame, "UE TX Power - PUSCH (dBm) Carrier 1", "UE TX Power Histogram", color='#8e44ad') # Using a different color, purple
        except AttributeError:
            print("Warning: UE_Power_frame not found in HistogramPage.ui")

    def _plot_single_histogram(self, frame, column_name, title, color='teal'):
        """Helper function to plot a single histogram in a given frame."""
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import os

            file_path = "Graphs_Divided_input.csv"
            if not os.path.exists(file_path):
                self._display_message_in_frame(frame, "No data file found")
                return

            df = pd.read_csv(file_path)

            if column_name not in df.columns:
                self._display_message_in_frame(frame, f"Column not found:\n{column_name}")
                return

            values = df[column_name].dropna().values

            if values.size == 0:
                self._display_message_in_frame(frame, "No valid data to plot")
                return

            # Use different x-axis label for throughput
            if column_name == "PDSCH Phy Throughput (kbps)":
                values = values / 1000 # Convert to Mbps
                xlabel = "Throughput (Mbps)"
            elif column_name == "Serving Cell RSRP (dBm)":
                xlabel = "RSRP (dBm)"
            elif column_name == "Serving Cell RSRQ (dB)":
                xlabel = "RSRQ (dB)"
            elif column_name == "Serving Cell RS SINR (dB)":
                xlabel = "SINR (dB)"
            else:
                 xlabel = column_name

            # Determine appropriate number of bins (e.g., using Freedman-Diaconis rule)
            # Or a fixed number, let's start with a reasonable default like 50
            bins = 50
            if values.size > 1:
                 iqr = np.percentile(values, 75) - np.percentile(values, 25)
                 bin_width = 2 * iqr / (values.size**(1/3)) # Freedman-Diaconis rule
                 if bin_width > 0:
                     bins = int(np.ceil((values.max() - values.min()) / bin_width))
                 bins = max(bins, 10) # Ensure a minimum number of bins
            else:
                bins = 1 # Handle single value case

            # Create a container widget to hold both the instruction label and chart
            container = QtWidgets.QWidget()
            container_layout = QtWidgets.QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)

            # Add instructional label
            instruction_label = QtWidgets.QLabel("Click on the chart to expand")
            instruction_label.setAlignment(QtCore.Qt.AlignCenter)
            instruction_label.setStyleSheet("color: #ff0000; font-size: 9pt; font-style: italic; font-weight: bold;")
            container_layout.addWidget(instruction_label)

            fig, ax = plt.subplots(figsize=(6.0, 5.2), facecolor='#f8f9fa')

            # Plot histogram
            counts, bin_edges, patches = ax.hist(values, bins=bins, color=color, edgecolor='#505050', alpha=0.9)

            # Add grid but make it subtle
            ax.grid(axis='y', linestyle='--', alpha=0.7, color='#cccccc')

            # Improve title and labels
            ax.set_title(title, fontsize=11, fontweight='bold', pad=10)
            ax.set_xlabel(xlabel, fontsize=10, fontweight='bold', labelpad=12)
            ax.set_ylabel("Frequency", fontsize=10, fontweight='bold', labelpad=12)

            # Make x-axis labels visible and prevent overlap
            ax.tick_params(axis='x', rotation=45, labelsize=10, colors='#000000', pad=8)
            ax.tick_params(axis='y', labelsize=9, colors='#505050')

            # Adjust layout
            fig.subplots_adjust(bottom=0.30, left=0.15, right=0.95, top=0.90)

            # Add a light border around the plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#dddddd')
                spine.set_linewidth(1)

            canvas = FigureCanvas(fig)

            # Make the canvas clickable to open a bigger view
            canvas.mpl_connect('button_press_event', lambda event: self._show_expanded_histogram(column_name, title, color, bins))

            # Add canvas to container
            container_layout.addWidget(canvas)

            # Clear the frame's layout
            if frame.layout() is None:
                layout = QtWidgets.QVBoxLayout(frame)
                frame.setLayout(layout)
            else:
                while frame.layout().count():
                    item = frame.layout().takeAt(0)
                    if item.widget():
                        item.widget().setParent(None)

            # Add the container to the frame
            frame.layout().addWidget(container)

        except Exception as e:
            self._display_message_in_frame(frame, f"Error:\n{str(e)}")

    def _show_expanded_histogram(self, column_name, title, color, bins):
        """Shows an expanded view of the histogram in a new dialog."""
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            import numpy as np
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            import os

            file_path = "Graphs_Divided_input.csv"
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Error", "No data file found")
                return

            df = pd.read_csv(file_path)
            if column_name not in df.columns:
                QMessageBox.warning(self, "Error", "Column not found")
                return

            values = df[column_name].dropna().values
            if values.size == 0:
                QMessageBox.warning(self, "Error", "No valid data to plot")
                return

            # Prepare data for plotting
            if column_name == "PDSCH Phy Throughput (kbps)":
                values = values / 1000 # Convert to Mbps
                xlabel = "Throughput (Mbps)"
            elif column_name == "Serving Cell RSRP (dBm)":
                xlabel = "RSRP (dBm)"
            elif column_name == "Serving Cell RSRQ (dB)":
                xlabel = "RSRQ (dB)"
            elif column_name == "Serving Cell RS SINR (dB)":
                xlabel = "SINR (dB)"
            else:
                xlabel = column_name

            # Use the same binning strategy as the small plot
            if values.size > 1:
                 iqr = np.percentile(values, 75) - np.percentile(values, 25)
                 bin_width = 2 * iqr / (values.size**(1/3)) # Freedman-Diaconis rule
                 if bin_width > 0:
                     bins = int(np.ceil((values.max() - values.min()) / bin_width))
                 bins = max(bins, 10) # Ensure a minimum number of bins
            else:
                bins = 1 # Handle single value case

            # Create expanded figure (larger size)
            expanded_fig = plt.figure(figsize=(12, 8), facecolor='#f8f9fa')
            ax = expanded_fig.add_subplot(111)

            # Plot histogram with enhanced styling
            ax.hist(values, bins=bins, color=color, edgecolor='#505050', alpha=0.9)

            # Add grid but make it subtle
            ax.grid(axis='y', linestyle='--', alpha=0.6, color='#cccccc')

            # Set detailed title and labels with improved styling
            ax.set_title(f"{title} - Detailed View", fontsize=18, fontweight='bold', pad=15)
            ax.set_xlabel(xlabel, fontsize=14, fontweight='bold', labelpad=10)
            ax.set_ylabel("Frequency", fontsize=14, fontweight='bold', labelpad=10)

            # Enhance tick appearance
            ax.tick_params(axis='x', rotation=45, labelsize=11, colors='#505050', pad=8)
            ax.tick_params(axis='y', labelsize=11, colors='#505050', pad=8)

            # Add a light border around the plot
            for spine in ax.spines.values():
                spine.set_edgecolor('#dddddd')
                spine.set_linewidth(1)

            # Adjust layout to ensure all elements are visible
            expanded_fig.subplots_adjust(bottom=0.15, left=0.1, right=0.95, top=0.90)

            # Create a new dialog to display the expanded chart
            dialog = QtWidgets.QDialog(self)
            dialog.setWindowTitle(f"{title} - Expanded View")
            dialog.setMinimumSize(900, 600)

            layout = QtWidgets.QVBoxLayout(dialog)
            expanded_canvas = FigureCanvas(expanded_fig)
            layout.addWidget(expanded_canvas)

            # Add a close button with better styling
            close_btn = QtWidgets.QPushButton("Close")
            close_btn.setStyleSheet("padding: 8px 16px; font-weight: bold; color: #ff0000; background-color: #e0e0e0;")
            close_btn.setMinimumWidth(120)
            close_btn.setMaximumWidth(120)
            close_btn.clicked.connect(dialog.close)

            # Add button container for centering
            button_container = QtWidgets.QWidget()
            button_layout = QtWidgets.QHBoxLayout(button_container)
            button_layout.addStretch()
            button_layout.addWidget(close_btn)
            button_layout.addStretch()
            layout.addWidget(button_container)

            dialog.exec_()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to show expanded histogram: {str(e)}")

    def _display_message_in_frame(self, frame, message):
        """Helper to display a message in a frame if data is missing or error occurs."""
        if frame.layout() is None:
            layout = QtWidgets.QVBoxLayout(frame)
            frame.setLayout(layout)
        else:
            while frame.layout().count():
                item = frame.layout().takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        label = QtWidgets.QLabel(message)
        label.setAlignment(QtCore.Qt.AlignCenter)
        frame.layout().addWidget(label)

    def return_to_main(self):
        """Return to the main window."""
        print("DEBUG: return_to_main called from HistogramPage")
        # Clear the stacked widget and return to the first page (main window)
        while self.widget.count() > 1:
            self.widget.removeWidget(self.widget.widget(1))
        self.widget.setCurrentIndex(0)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set application icon
    app_icon = QtGui.QIcon("icon.png")  # Make sure to have an icon.png file in your project directory
    app.setWindowIcon(app_icon)
    
    # Apply a modern style sheet
    app.setStyleSheet("""
        /* Global styles */
        QMainWindow, QDialog, QWidget {
            background-color: #f5f7fa;
            color: #2c3e50;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        
        /* Button styling */
        QPushButton {
            background-color: #e0e0e0;  /* Light grey background */
            color: #ff0000;  /* Red text */
            border-radius: 4px;
            padding: 6px 16px;
            font-weight: bold;
            border: none;
        }
        QPushButton:hover {
            /* background-color: #d0d0d0;  /* Slightly darker grey when hovering */ */
        }
        QPushButton:pressed {
            /* background-color: #c0c0c0;  /* Even darker grey when pressed */ */
            padding-top: 8px;
            padding-bottom: 4px;
        }
        
        /* Tab widget styling */
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
        QTabBar::tab {
            background: #e0e0e0;
            border: 1px solid #c4c4c4;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 6px 12px;
        }
        QTabBar::tab:selected {
            background: #3498db;
            color: white;
        }
        
        /* Line edit and text styling */
        QLineEdit, QTextEdit {
            border: 1px solid #bdc3c7;
            border-radius: 4px;
            padding: 4px;
            background-color: white;
        }
        
        /* Table styling */
        QTableWidget {
            gridline-color: #d0d0d0;
            background-color: white;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #3498db;
            color: white;
        }
        QHeaderView::section {
            background-color: #ecf0f1;
            border: 1px solid #d0d0d0;
            padding: 4px;
            font-weight: bold;
        }
        
        /* Scrollbar styling */
        QScrollBar:vertical {
            border: none;
            background: #f0f0f0;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #b8b8b8;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #a0a0a0;
        }
        
        /* Specific Label styling */
        #label_3,
        #label_4,
        #label_5,
        #label_6 {
            background-color: white; /* Set background to white for specific labels */
        }
        
        /* Tab widget styling */
        QTabWidget::pane {
            border: 1px solid #d0d0d0;
            border-radius: 4px;
        }
    """)
    
    widget = QStackedWidget()
    main = MainWindow(widget)
    widget.addWidget(main)
    widget.resize(1100, 750)
    widget.setWindowFlags(QtCore.Qt.Window)
    widget.setWindowTitle("DriveTest Analyzer Pro")
    widget.show()
    sys.exit(app.exec_())
