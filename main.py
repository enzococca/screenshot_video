import sys
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QLabel, QVBoxLayout, QHBoxLayout, \
    QWidget, QSlider, QStyle, QSizePolicy, QGroupBox, QComboBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QTranslator, QLocale


class FrameGrabber(QThread):
    frame_grabbed = pyqtSignal(object)

    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.running = True

    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_grabbed.emit(frame)
            else:
                self.running = False

    def seek(self, frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

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
        self.fps = 0  # Inizializzato a 0
        self.frame_grabber = None
        self.translator = QTranslator()

    def initUI(self):
        self.setWindowTitle(self.tr('Video Frame Extractor'))
        self.setGeometry(100, 100, 1200, 800)

        main_layout = QVBoxLayout()

        # Toolbar group
        toolbar_group = QGroupBox(self.tr("Controls"))
        toolbar_layout = QHBoxLayout()

        self.load_button = QPushButton(self.tr('Load Video'))
        self.load_button.clicked.connect(self.load_video)
        self.load_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.load_button.setFixedSize(120, 40)
        toolbar_layout.addWidget(self.load_button)

        self.save_button = QPushButton(self.tr('Save Frame'))
        self.save_button.clicked.connect(self.save_frame)
        self.save_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.save_button.setFixedSize(120, 40)
        toolbar_layout.addWidget(self.save_button)

        self.time_label = QLabel(self.tr('Time: 00:00:00'))
        toolbar_layout.addWidget(self.time_label)

        self.language_combo = QComboBox()
        self.language_combo.addItems(['English', 'Italiano', 'Bahasa Indonesia'])
        self.language_combo.currentIndexChanged.connect(self.change_language)
        toolbar_layout.addWidget(self.language_combo)

        toolbar_group.setLayout(toolbar_layout)
        main_layout.addWidget(toolbar_group)

        # Slider group
        slider_group = QGroupBox(self.tr("Video Navigation"))
        slider_layout = QHBoxLayout()

        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.slider_moved)
        self.slider.sliderReleased.connect(self.slider_released)
        slider_layout.addWidget(self.slider)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(160, 90)
        self.preview_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        slider_layout.addWidget(self.preview_label)

        slider_group.setLayout(slider_layout)
        main_layout.addWidget(slider_group)

        # Main display group
        display_group = QGroupBox(self.tr("Frame Display"))
        display_layout = QVBoxLayout()

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        display_layout.addWidget(self.image_label)

        display_group.setLayout(display_layout)
        main_layout.addWidget(display_group)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_preview)
        self.timer.start(100)  # Update every 100ms

    def load_video(self):
        self.video_path, _ = QFileDialog.getOpenFileName(self, self.tr("Select Video"), "",
                                                         self.tr("Video Files (*.mp4 *.avi *.mkv *.mov *.wmv)"))
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

    def slider_moved(self):
        frame_number = self.slider.value()
        self.update_time_label(frame_number)

    def slider_released(self):
        frame_number = self.slider.value()
        if self.frame_grabber:
            self.frame_grabber.seek(frame_number)
        self.show_frame(frame_number)

    def show_frame(self, frame_number):
        if self.cap:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self.display_frame(frame, self.image_label)
                self.update_time_label(frame_number)

    def update_frame(self, frame):
        self.current_frame = frame
        self.display_frame(frame, self.image_label)

    def display_frame(self, frame, label):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


    def update_preview(self):
        if self.cap and self.slider.isSliderDown():
            preview_frame = self.slider.value()
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, preview_frame)
            ret, frame = self.cap.read()
            if ret:
                self.display_frame(frame, self.preview_label)

    def save_frame(self):
        if self.current_frame is not None:
            save_path, _ = QFileDialog.getSaveFileName(self, self.tr("Save Frame"), "", self.tr("TIFF (*.tiff)"))
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
                print(self.tr("Frame saved in {} with resolution {}x{}").format(save_path, new_width, new_height))

    def change_language(self, index):
        languages = ['en', 'it', 'id']
        QApplication.removeTranslator(self.translator)
        self.translator = QTranslator()
        success = self.translator.load(f"i18n_{languages[index]}")
        print(f"Loading translation file: i18n_{languages[index]}.qm - Success: {success}")
        QApplication.installTranslator(self.translator)
        self.retranslateUi()

    def retranslateUi(self):
        self.setWindowTitle(self.tr('Video Frame Extractor'))
        self.load_button.setText(self.tr('Load Video'))
        self.save_button.setText(self.tr('Save Frame'))
        self.update_time_label(self.slider.value())

    def update_time_label(self, frame_number):
        if self.fps > 0:
            time_in_seconds = frame_number / self.fps
            hours = int(time_in_seconds // 3600)
            minutes = int((time_in_seconds % 3600) // 60)
            seconds = int(time_in_seconds % 60)
            self.time_label.setText(self.tr('Time: {:02d}:{:02d}:{:02d}').format(hours, minutes, seconds))
        else:
            self.time_label.setText(self.tr('Time: 00:00:00'))

    def closeEvent(self, event):
        if self.frame_grabber:
            self.frame_grabber.stop()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set default language to English
    translator = QTranslator()
    translator.load("i18n_en")
    app.installTranslator(translator)

    ex = VideoFrameExtractor()
    ex.show()
    sys.exit(app.exec_())