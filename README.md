# IMX500 Remote Camera UI

Prototype for controlling a Raspberry Pi AI Camera from a laptop over a local network.
The browser UI is in [v3.html](v3.html); the Raspberry Pi HTTP service is in [raspberry_pi](raspberry_pi).

## Verified hardware and software path

- Camera: Raspberry Pi AI Camera, Sony IMX500, 12.3 MP still sensor resolution 4056 x 3040.
- Raspberry Pi: any current Pi with a compatible CSI camera connector; Pi 4 or Pi 5 is recommended for capture throughput.
- Camera stack: libcamera through Picamera2. The IMX500 AI/inference features are optional for this capture-only prototype.
- Raspberry Pi OS: current 64-bit Raspberry Pi OS is recommended. Picamera2 supports Bullseye and newer; on Bookworm/Trixie install Python packages in a virtual environment or through APT.
- Transfer: HTTP REST with binary `image/jpeg` response. Base64 and WebSocket are unnecessary for single still captures.

The exact camera mode is detected by Picamera2 at startup. The requested still configuration is 4056 x 3040; the actual status response is the source of truth.

## Project layout

```text
.
├── v1.html
├── v2.html
├── v3.html                 # connected browser UI
├── laptop
│   ├── api_client.py       # requests client
│   ├── main.py             # PySide6 desktop client
│   └── requirements.txt
└── raspberry_pi
	├── camera.py           # Picamera2 controller and capture lock
	├── config.py
	├── main.py             # Flask API
	├── requirements.txt
	└── imx500-camera.service
```

## Raspberry Pi installation

Use Raspberry Pi OS Bullseye or newer and update the matching camera stack:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3-picamera2 python3-venv
rpicam-hello --timeout 5000
```

Copy this repository to the Pi, then create the service environment. Picamera2 is intentionally installed from APT because Raspberry Pi recommends keeping it aligned with the system libcamera packages:

```bash
cd raspberry_pi
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

The server listens on `0.0.0.0:8000`. Keep it on the LAN; do not expose this unauthenticated prototype to the public internet.

### Optional systemd service

Adjust the `User`, `WorkingDirectory`, and `ExecStart` paths in `imx500-camera.service`, then:

```bash
sudo cp imx500-camera.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now imx500-camera
sudo systemctl status imx500-camera
```

## Laptop / browser setup

1. Put the Pi and laptop on the same Wi-Fi or Ethernet network.
2. Find the Pi address with `hostname -I`.
3. Open [v3.html](v3.html) in a modern browser.
4. Enter `http://<PI_IP>:8000` in **Remote camera** and press **Connect**.
5. Press **Capture from Camera**. The JPEG is transferred as binary, previewed without changing the original, and can be saved with **Save**.

If the browser blocks requests from a local file, serve the workspace from the laptop instead:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080/v3.html`.

### Optional PySide6 desktop client

On Windows:

```powershell
cd laptop
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

The desktop client keeps HTTP requests off the GUI thread with `QThread`, displays the full-resolution JPEG as a fitted preview, and writes the original response bytes when saving.

## API

`GET /api/status` returns camera readiness, model, resolution, and an error if initialization failed.

`POST /api/capture` accepts an optional JSON body:

```json
{"filename": "sample_001.jpg"}
```

It returns the JPEG bytes directly and includes `X-Capture-Width`, `X-Capture-Height`, `X-Capture-Sha256`, and `Content-Length` headers. Filenames are restricted to safe `.jpg` names, so path traversal is rejected.

## Test checklist

- `rpicam-hello` detects the camera.
- `GET /api/status` reports `ready: true`.
- UI Connect reports `Connected - Ready`.
- Capture returns a JPEG and the preview keeps its aspect ratio.
- Save writes the original JPEG, not the preview size.
- Empty or duplicate-friendly filenames work; unsafe names are rejected.
- Disconnecting Wi-Fi changes the UI to `Connection lost`.
- Restarting the service allows reconnecting without restarting the UI.
- Check logs with `journalctl -u imx500-camera -f`.

## Known boundary

This workspace contains a browser control surface, a PySide6 desktop client, and the Raspberry Pi capture service. AI inference, authentication, and live video streaming are intentionally outside the first capture workflow. They can be added without changing the capture API.

## Official references

- [Raspberry Pi AI Camera documentation](https://www.raspberrypi.com/documentation/accessories/ai-camera.html)
- [Raspberry Pi camera hardware specifications](https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification)
- [Picamera2 installation and manual](https://github.com/raspberrypi/picamera2)
"# UX/UI of Micro Plastic Analysis" 
