import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from api_client import CameraApiClient


class Worker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, action, *args):
        super().__init__()
        self.action = action
        self.args = args

    @Slot()
    def run(self):
        try:
            self.finished.emit(self.action(*self.args))
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("IMX500 Remote Camera")
        self.resize(760, 620)
        self.client: CameraApiClient | None = None
        self.last_image: bytes | None = None
        self.last_filename = ""
        self.active_thread: QThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        form = QFormLayout()
        self.endpoint = QLineEdit("http://192.168.1.100:8000")
        self.filename = QLineEdit()
        self.filename.setPlaceholderText("image_001.jpg")
        form.addRow("Camera API", self.endpoint)
        form.addRow("Filename", self.filename)
        layout.addLayout(form)

        actions = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_camera)
        self.capture_button = QPushButton("Capture")
        self.capture_button.setEnabled(False)
        self.capture_button.clicked.connect(self.capture_image)
        self.save_button = QPushButton("Save as...")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_image)
        actions.addWidget(self.connect_button)
        actions.addWidget(self.capture_button)
        actions.addWidget(self.save_button)
        layout.addLayout(actions)

        self.status = QLabel("Disconnected")
        self.camera_info = QLabel("Camera: - | Resolution: -")
        self.preview = QLabel("No image captured")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(380)
        self.preview.setStyleSheet("border: 1px solid #cfc8b2; background: #fbf9f3;")
        self.log = QLabel("Ready")
        self.log.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(self.camera_info)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.log)
        self.setCentralWidget(root)

    def run_async(self, action, *args) -> None:
        if self.active_thread is not None:
            return
        self.active_thread = QThread(self)
        worker = Worker(action, *args)
        worker.moveToThread(self.active_thread)
        self.active_thread.started.connect(worker.run)
        worker.finished.connect(self.on_worker_finished)
        worker.failed.connect(self.on_worker_failed)
        worker.finished.connect(self.stop_worker)
        worker.failed.connect(self.stop_worker)
        self.active_thread.finished.connect(worker.deleteLater)
        self.active_thread.finished.connect(self.active_thread.deleteLater)
        self.active_thread.start()

    def stop_worker(self) -> None:
        if self.active_thread is not None:
            thread = self.active_thread
            self.active_thread = None
            thread.quit()

    def connect_camera(self) -> None:
        self.client = CameraApiClient(self.endpoint.text().strip())
        self.status.setText("Connecting...")
        self.run_async(self.client.status)

    def capture_image(self) -> None:
        if self.client is None:
            return
        self.capture_button.setEnabled(False)
        self.status.setText("Capturing...")
        self.run_async(self.client.capture, self.filename.text().strip())

    def save_image(self) -> None:
        if not self.last_image:
            return
        suggested = self.last_filename or f"IMG_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        path, _ = QFileDialog.getSaveFileName(self, "Save original JPEG", suggested, "JPEG image (*.jpg)")
        if path:
            try:
                Path(path).write_bytes(self.last_image)
                self.log.setText(f"Saved {Path(path).name}")
            except OSError as exc:
                QMessageBox.critical(self, "Unable to save image", str(exc))

    @Slot(object)
    def on_worker_finished(self, result) -> None:
        if isinstance(result, tuple):
            self.last_image, headers = result
            self.last_filename = headers.get("Content-Disposition", "").split('filename="')[-1].rstrip('"')
            image = QImage.fromData(self.last_image)
            self.preview.setPixmap(QPixmap.fromImage(image).scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.save_button.setEnabled(True)
            self.status.setText("Captured")
            self.log.setText(f"Received {len(self.last_image) // 1024} KB JPEG")
            self.capture_button.setEnabled(True)
        else:
            self.capture_button.setEnabled(bool(result.ready))
            self.status.setText("Connected - Ready" if result.ready else "Camera unavailable")
            self.camera_info.setText(f"Camera: {result.camera_model} | Resolution: {result.width} x {result.height}")
            self.log.setText("Status checked")

    @Slot(str)
    def on_worker_failed(self, message: str) -> None:
        self.status.setText("Connection lost")
        self.log.setText(message)
        self.capture_button.setEnabled(False)
        QMessageBox.warning(self, "Camera request failed", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
