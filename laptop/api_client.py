from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class CameraStatus:
    camera_connected: bool
    camera_model: str
    width: int | None
    height: int | None
    ready: bool
    error: str | None = None


class CameraApiClient:
    def __init__(self, base_url: str, timeout: float = 35) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def status(self) -> CameraStatus:
        response = requests.get(f"{self.base_url}/api/status", timeout=5)
        response.raise_for_status()
        data = response.json()
        resolution = data.get("resolution") or {}
        return CameraStatus(
            bool(data.get("camera_connected")),
            data.get("camera_model", "Unknown camera"),
            resolution.get("width"),
            resolution.get("height"),
            bool(data.get("ready")),
            data.get("error"),
        )

    def capture(self, filename: str) -> tuple[bytes, dict[str, str]]:
        response = requests.post(
            f"{self.base_url}/api/capture",
            json={"filename": filename} if filename else {},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.content, dict(response.headers)
