import io
import logging
import threading
from dataclasses import dataclass

from picamera2 import Picamera2

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CameraStatus:
    connected: bool
    ready: bool
    model: str
    width: int | None
    height: int | None
    error: str | None = None


class CameraController:
    def __init__(self, model: str) -> None:
        self._model = model
        self._camera: Picamera2 | None = None
        self._configuration = None
        self._lock = threading.Lock()
        self._error: str | None = None

    def initialize(self) -> None:
        try:
            self._camera = Picamera2()
            self._configuration = self._camera.create_still_configuration(
                main={"size": (4056, 3040), "format": "RGB888"}
            )
            self._camera.configure(self._configuration)
            self._camera.start()
            LOGGER.info("Camera initialized: %s", self._model)
        except Exception as exc:
            self._error = str(exc)
            LOGGER.exception("Camera initialization failed")

    def status(self) -> CameraStatus:
        if self._camera is None or self._configuration is None:
            return CameraStatus(False, False, self._model, None, None, self._error)
        size = self._configuration["main"]["size"]
        return CameraStatus(True, True, self._model, size[0], size[1])

    def capture_jpeg(self) -> tuple[bytes, int, int]:
        if self._camera is None or self._configuration is None:
            raise RuntimeError(self._error or "Camera not detected")
        with self._lock:
            output = io.BytesIO()
            self._camera.capture_file(output, format="jpeg")
            payload = output.getvalue()
            size = self._configuration["main"]["size"]
            LOGGER.info("Image captured: %sx%s, %s bytes", size[0], size[1], len(payload))
            return payload, size[0], size[1]

    def close(self) -> None:
        if self._camera is not None:
            self._camera.stop()
            self._camera.close()
            self._camera = None
