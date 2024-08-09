import sys
import cv2

from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QFileDialog, QLabel, QVBoxLayout, QHBoxLayout,
                             QWidget, QSlider, QStyle, QSizePolicy, QGroupBox, QComboBox, QLineEdit, QToolBar,
                             QAction, QSpinBox, QDialog, QListWidget, QProgressBar, QMessageBox, QProgressDialog)
from PyQt5.QtGui import QImage, QPixmap, QPalette, QColor, QIcon
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize, QPoint


class FrameGrabber(QThread):
    frame_grabbed = pyqtSignal(object, int)

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.running = True
        self.current_frame = 0

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_grabbed.emit(frame, self.current_frame)
                self.current_frame += 1
            else:
                self.running = False

    def seek(self, frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.current_frame = frame_number

    def stop(self):
        self.running = False
        self.wait()


class VideoFrameExtractor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.video_path = None
        self.current_frame = None
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.frame_grabber = None
        self.bookmarks = []

    def initUI(self):
        self.setWindowTitle('Video Frame Extractor')
        self.setGeometry(100, 100, 1200, 800)

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self.load_action = QAction(QIcon.fromTheme("document-open"), 'Load Video', self)
        self.load_action.triggered.connect(self.load_video)
        self.toolbar.addAction(self.load_action)

        self.save_action = QAction(QIcon.fromTheme("document-save"), 'Save Frame', self)
        self.save_action.triggered.connect(self.save_frame)
        self.toolbar.addAction(self.save_action)

        self.bookmark_action = QAction(QIcon.fromTheme("bookmark-new"), 'Add Bookmark', self)
        self.bookmark_action.triggered.connect(self.add_bookmark)
        self.toolbar.addAction(self.bookmark_action)

        self.show_bookmarks_action = QAction(QIcon.fromTheme("bookmarks"), 'Show Bookmarks', self)
        self.show_bookmarks_action.triggered.connect(self.show_bookmarks)
        self.toolbar.addAction(self.show_bookmarks_action)

        self.export_bookmarks_action = QAction(QIcon.fromTheme("document-save-as"), 'Export Bookmark Frames', self)
        self.export_bookmarks_action.triggered.connect(self.export_bookmarks)
        self.toolbar.addAction(self.export_bookmarks_action)

        self.extract_frames_action = QAction(QIcon.fromTheme("document-export"), 'Extract Frames', self)
        self.extract_frames_action.triggered.connect(self.extract_frames)
        self.toolbar.addAction(self.extract_frames_action)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark'])
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        self.toolbar.addWidget(self.theme_combo)

        # Main layout
        main_layout = QVBoxLayout()

        # Time navigation
        time_layout = QHBoxLayout()
        self.time_label = QLabel('Time: 00:00:00.000')
        time_layout.addWidget(self.time_label)

        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        time_layout.addWidget(self.hour_spin)

        self.minute_spin = QSpinBox()
        self.minute_spin.setRange(0, 59)
        time_layout.addWidget(self.minute_spin)

        self.second_spin = QSpinBox()
        self.second_spin.setRange(0, 59)
        time_layout.addWidget(self.second_spin)

        self.millisecond_spin = QSpinBox()
        self.millisecond_spin.setRange(0, 999)
        time_layout.addWidget(self.millisecond_spin)

        self.go_button = QPushButton('Go')
        self.go_button.clicked.connect(self.go_to_time)
        time_layout.addWidget(self.go_button)

        main_layout.addLayout(time_layout)

        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.sliderMoved.connect(self.slider_moved)
        main_layout.addWidget(self.slider)

        # Preview label
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(320, 180)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.hide()

        # Main display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.image_label)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def load_video(self):
        self.video_path, _ = QFileDialog.getOpenFileName(self, "Select Video", "",
                                                         "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv)")
        if self.video_path:
            if self.frame_grabber:
                self.frame_grabber.stop()

            self.cap = cv2.VideoCapture(self.video_path)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.slider.setRange(0, self.total_frames - 1)

            self.frame_grabber = FrameGrabber(self.video_path)
            self.frame_grabber.frame_grabbed.connect(self.update_frame)
            self.frame_grabber.start()

            self.show_frame(0)

    def slider_pressed(self):
        self.preview_label.show()

    def slider_released(self):
        self.preview_label.hide()
        frame_number = self.slider.value()
        if self.frame_grabber:
            self.frame_grabber.seek(frame_number)
        self.show_frame(frame_number)

    def slider_moved(self, position):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame, self.preview_label)
                self.update_time_label(position)
                # Update preview label position
                slider_width = self.slider.width()
                slider_pos = self.slider.mapToGlobal(self.slider.pos())
                relative_pos = position / self.total_frames
                preview_x = slider_pos.x() + int(slider_width * relative_pos) - self.preview_label.width() // 2
                preview_y = slider_pos.y() - self.preview_label.height() - 10
                self.preview_label.move(self.mapFromGlobal(QPoint(preview_x, preview_y)))

    def show_frame(self, frame_number):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self.display_frame(frame, self.image_label)
                self.update_time_label(frame_number)

    def update_frame(self, frame, frame_number):
        self.current_frame = frame
        self.display_frame(frame, self.image_label)
        self.slider.setValue(frame_number)
        self.update_time_label(frame_number)

    def display_frame(self, frame, label):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))



    def save_frame(self):
        if self.current_frame is not None:
            save_path, _ = QFileDialog.getSaveFileName(self, "Save Frame", "", "TIFF (*.tiff)")
            if save_path:
                height, width = self.current_frame.shape[:2]
                print_size_inches = 10
                scale_factor = max(1, (300 * print_size_inches) / max(width, height))
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                resized_frame = cv2.resize(self.current_frame, (new_width, new_height),
                                           interpolation=cv2.INTER_LANCZOS4)
                cv2.imwrite(save_path, resized_frame, [
                    cv2.IMWRITE_TIFF_COMPRESSION, 1,
                    cv2.IMWRITE_TIFF_RESUNIT, 2,
                    cv2.IMWRITE_TIFF_XDPI, 300,
                    cv2.IMWRITE_TIFF_YDPI, 300
                ])
                print(f"Frame saved in {save_path} with resolution {new_width}x{new_height}")

    def change_theme(self, index):
        app = QApplication.instance()
        if index == 0:  # Light theme
            app.setStyle("Fusion")
            palette = QPalette()
            app.setPalette(palette)
        else:  # Dark theme
            app.setStyle("Fusion")
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(palette)

    def update_time_label(self, frame_number):
        if self.fps > 0:
            time_in_seconds = frame_number / self.fps
            hours = int(time_in_seconds // 3600)
            minutes = int((time_in_seconds % 3600) // 60)
            seconds = int(time_in_seconds % 60)
            milliseconds = int((time_in_seconds % 1) * 1000)
            self.time_label.setText(f'Time: {hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}')
            self.hour_spin.setValue(hours)
            self.minute_spin.setValue(minutes)
            self.second_spin.setValue(seconds)
            self.millisecond_spin.setValue(milliseconds)
        else:
            self.time_label.setText('Time: 00:00:00.000')

    def go_to_time(self):
        if self.fps > 0:
            hours = self.hour_spin.value()
            minutes = self.minute_spin.value()
            seconds = self.second_spin.value()
            milliseconds = self.millisecond_spin.value()
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            frame_number = int(total_seconds * self.fps)
            self.slider.setValue(frame_number)
            self.show_frame(frame_number)

    def add_bookmark(self):
        if self.cap:
            current_frame = self.slider.value()
            if current_frame not in self.bookmarks:
                self.bookmarks.append(current_frame)
                self.bookmarks.sort()
                print(f"Bookmark added at frame {current_frame}")
            else:
                print(f"Bookmark already exists at frame {current_frame}")

    def show_bookmarks(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Bookmarks")
        layout = QVBoxLayout()
        list_widget = QListWidget()
        for bookmark in sorted(self.bookmarks):
            time = self.frame_to_time(bookmark)
            list_widget.addItem(f"Frame {bookmark} - {time}")
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.exec_()

    def frame_to_time(self, frame_number):
        if self.fps > 0:
            time_in_seconds = frame_number / self.fps
            hours = int(time_in_seconds // 3600)
            minutes = int((time_in_seconds % 3600) // 60)
            seconds = int(time_in_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "00:00:00"

    def extract_frames(self):
        try:
            if not self.cap:
                print("No video loaded")
                return



            dialog = QDialog(self)
            dialog.setWindowTitle("Extract Frames")
            layout = QVBoxLayout()

            start_frame_spin = QSpinBox()
            start_frame_spin.setRange(0, self.total_frames - 1)
            layout.addWidget(QLabel("Start Frame:"))
            layout.addWidget(start_frame_spin)

            end_frame_spin = QSpinBox()
            end_frame_spin.setRange(0, self.total_frames - 1)
            end_frame_spin.setValue(self.total_frames - 1)
            layout.addWidget(QLabel("End Frame:"))
            layout.addWidget(end_frame_spin)

            interval_spin = QSpinBox()
            interval_spin.setRange(1, 1000)
            interval_spin.setValue(1)
            layout.addWidget(QLabel("Interval:"))
            layout.addWidget(interval_spin)

            extract_button = QPushButton("Extract")
            layout.addWidget(extract_button)

            progress_bar = QProgressBar()
            layout.addWidget(progress_bar)

            dialog.setLayout(layout)

            def do_extract():
                start_frame = start_frame_spin.value()
                end_frame = end_frame_spin.value()
                interval = interval_spin.value()

                save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Frames")
                if not save_dir:
                    return

                total_frames = (end_frame - start_frame) // interval + 1
                progress_bar.setRange(0, total_frames)
                progress_bar.setValue(0)

                self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                for i in range(total_frames):
                    ret, frame = self.cap.read()
                    if ret:
                        frame_number = start_frame + i * interval
                        filename = f"frame_{frame_number:06d}.tiff"
                        filepath = f"{save_dir}/{filename}"
                        cv2.imwrite(filepath, frame, [
                            cv2.IMWRITE_TIFF_COMPRESSION, 1,
                            cv2.IMWRITE_TIFF_RESUNIT, 2,
                            cv2.IMWRITE_TIFF_XDPI, 300,
                            cv2.IMWRITE_TIFF_YDPI, 300
                        ])
                        progress_bar.setValue(i + 1)
                        QApplication.processEvents()  # Keep UI responsive

                    # Skip frames according to interval
                    for _ in range(interval - 1):
                        self.cap.read()


                dialog.accept()

            extract_button.clicked.connect(do_extract)
            dialog.exec_()
        except Exception as e:
            print(f"Error in extract_frames: {e}")

    def export_bookmarks(self):
        if not self.bookmarks or not self.cap:
            QMessageBox.information(self, "Export Bookmarks", "No bookmarks to export or no video loaded.")
            return

        save_dir = QFileDialog.getExistingDirectory(self, "Select Directory to Save Bookmark Frames")
        if not save_dir:
            return

        progress_dialog = QProgressDialog("Exporting bookmark frames...", "Cancel", 0, len(self.bookmarks), self)
        progress_dialog.setWindowModality(Qt.WindowModal)

        for i, bookmark in enumerate(self.bookmarks):
            if progress_dialog.wasCanceled():
                break

            self.cap.set(cv2.CAP_PROP_POS_FRAMES, bookmark)
            ret, frame = self.cap.read()
            if ret:
                time = self.frame_to_time(bookmark)
                filename = f"bookmark_frame_{bookmark:06d}_{time.replace(':', '-')}.tiff"
                filepath = f"{save_dir}/{filename}"

                # Resize for 300 DPI
                height, width = frame.shape[:2]
                print_size_inches = 10
                scale_factor = max(1, (300 * print_size_inches) / max(width, height))
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)

                cv2.imwrite(filepath, resized_frame, [
                    cv2.IMWRITE_TIFF_COMPRESSION, 1,
                    cv2.IMWRITE_TIFF_RESUNIT, 2,
                    cv2.IMWRITE_TIFF_XDPI, 300,
                    cv2.IMWRITE_TIFF_YDPI, 300
                ])

            progress_dialog.setValue(i + 1)

        progress_dialog.close()
        QMessageBox.information(self, "Export Bookmarks", f"Bookmark frames exported successfully to {save_dir}")

    def closeEvent(self, event):
        if self.frame_grabber:
            self.frame_grabber.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VideoFrameExtractor()
    ex.show()
    sys.exit(app.exec_())