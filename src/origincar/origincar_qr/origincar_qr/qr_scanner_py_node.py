"""
qr_scanner_py_node.py — QR code scanner for OriginCar (Python version).

Primary decoder: pyzbar (zbar wrapper) — best range.
Fallback: cv2.QRCodeDetector — best extreme angles.
Auto-detects max camera resolution (set frame_width=0 / frame_height=0).
Preview shows CLAHE-enhanced image with minimal latency.
"""

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from pyzbar.pyzbar import decode as pyzbar_decode
from pyzbar.pyzbar import ZBarSymbol


class QRScannerNode(Node):
    """ROS 2 node — multi-pass QR decoding with auto-resolution & low-latency preview."""

    def __init__(self):
        super().__init__('qr_scanner_node')

        # ── Declare parameters ──
        self.declare_parameter('camera_id', 0)
        self.declare_parameter('frame_width', 0)   # 0 = auto
        self.declare_parameter('frame_height', 0)  # 0 = auto
        self.declare_parameter('scan_rate_hz', 10.0)
        self.declare_parameter('show_preview', False)
        self.declare_parameter('enable_multiscale', True)
        self.declare_parameter('clahe_clip_limit', 2.0)
        self.declare_parameter('clahe_tile_size', 8)

        camera_id = self.get_parameter('camera_id').value
        req_w = self.get_parameter('frame_width').value
        req_h = self.get_parameter('frame_height').value
        rate = self.get_parameter('scan_rate_hz').value
        self.show_preview = self.get_parameter('show_preview').value
        self.enable_multiscale = self.get_parameter('enable_multiscale').value
        clahe_clip = self.get_parameter('clahe_clip_limit').value
        clahe_tile = self.get_parameter('clahe_tile_size').value

        # ── Open camera ──
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            self.get_logger().error(
                f'Cannot open camera /dev/video{camera_id}')
            raise RuntimeError(f'Camera /dev/video{camera_id} not available')

        # MJPG for higher resolution support
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))

        # Single-frame buffer: eliminates preview latency
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # ── Resolution: auto-detect or explicit ──
        if req_w > 0 and req_h > 0:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, req_w)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, req_h)
            self.actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.get_logger().info(
                f'Using requested resolution: {req_w}x{req_h} '
                f'(actual: {self.actual_w}x{self.actual_h})')
        else:
            # Auto-detect: set impossibly high → V4L2 clamps to max supported
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 10000)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 10000)
            self.actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if (self.actual_w > 3840 or self.actual_h > 2160 or
                    self.actual_w <= 0 or self.actual_h <= 0):
                self.get_logger().warn(
                    f'Auto-detect returned suspicious '
                    f'{self.actual_w}x{self.actual_h}, '
                    f'falling back to 1920x1080')
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                self.actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            else:
                self.get_logger().info(
                    f'Auto-detected max resolution: '
                    f'{self.actual_w}x{self.actual_h}')

        self.get_logger().info(
            f'Camera ready: /dev/video{camera_id} '
            f'@ {self.actual_w}x{self.actual_h}')

        # ── CLAHE ──
        self.clahe = cv2.createCLAHE(
            clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))

        # ── CV2 QR detector (fallback for extreme angles) ──
        self.cv2_detector = cv2.QRCodeDetector()

        # ── Preview window ──
        if self.show_preview:
            try:
                cv2.namedWindow('QR Scanner (CLAHE view)', cv2.WINDOW_NORMAL)
                pw = min(self.actual_w, 960)
                ph = min(self.actual_h, 540)
                cv2.resizeWindow('QR Scanner (CLAHE view)', pw, ph)
            except cv2.error:
                self.get_logger().warn(
                    'OpenCV GUI not available (missing GTK/QT). '
                    'Install opencv-python: pip install opencv-python')
                self.show_preview = False

        # ── Scan timer ──
        self.scan_timer = self.create_timer(1.0 / rate, self.scan_once)
        self.get_logger().info(
            f'QR scanner started | rate={rate} Hz | '
            f'{self.actual_w}x{self.actual_h} | '
            f'multiscale={self.enable_multiscale} | '
            f'CLAHE={clahe_clip}/{clahe_tile} | '
            f'preview={self.show_preview}')

    # ──────────────────────────────────────────────
    #  Preprocessing
    # ──────────────────────────────────────────────

    def preprocess_clahe(self, gray: np.ndarray) -> np.ndarray:
        return self.clahe.apply(gray)

    def preprocess_sharpen(self, gray: np.ndarray) -> np.ndarray:
        blurred = cv2.GaussianBlur(gray, (0, 0), 3.0)
        return cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)

    def preprocess_binary(self, gray: np.ndarray) -> np.ndarray:
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 15, 3)

    # ──────────────────────────────────────────────
    #  Decoding helpers
    # ──────────────────────────────────────────────

    def try_pyzbar(self, image: np.ndarray, pass_name: str) -> bool:
        codes = pyzbar_decode(image, symbols=[ZBarSymbol.QRCODE])
        found = False
        for code in codes:
            data = code.data.decode('utf-8', errors='replace')
            self.get_logger().info(f'✓ QR [{pass_name}]: {data}')
            print(data, flush=True)
            found = True
        return found

    def try_cv2_qr(self, color_img: np.ndarray) -> bool:
        data, pts, _ = self.cv2_detector.detectAndDecode(color_img)
        if data:
            self.get_logger().info(f'✓ QR [cv2.QRCodeDetector]: {data}')
            print(data, flush=True)
            return True
        return False

    # ──────────────────────────────────────────────
    #  Frame grabber with buffer flush (low latency)
    # ──────────────────────────────────────────────

    def grab_latest(self) -> np.ndarray | None:
        """Flush stale frames from the camera buffer, return the freshest one."""
        flushed = 0
        while self.cap.grab():
            flushed += 1
        if flushed == 0:
            return None
        ret, frame = self.cap.retrieve()
        if not ret or frame is None:
            return None
        return frame

    # ──────────────────────────────────────────────
    #  Main scan loop
    # ──────────────────────────────────────────────

    def scan_once(self):
        frame = self.grab_latest()
        if frame is None:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found = False

        # ── Pass 1: CLAHE → pyzbar ──
        enhanced = self.preprocess_clahe(gray)
        found = self.try_pyzbar(enhanced, 'CLAHE')

        # ── Pass 2: CLAHE + sharpen → pyzbar ──
        if not found and self.enable_multiscale:
            sharp = self.preprocess_sharpen(enhanced)
            found = self.try_pyzbar(sharp, 'CLAHE+Sharp')

        # ── Pass 3: Adaptive binary → pyzbar ──
        if not found and self.enable_multiscale:
            binary = self.preprocess_binary(gray)
            found = self.try_pyzbar(binary, 'Binary')

        # ── Pass 4: CLAHE + binary → pyzbar ──
        if not found and self.enable_multiscale:
            bin_clahe = self.preprocess_binary(enhanced)
            found = self.try_pyzbar(bin_clahe, 'CLAHE+Binary')

        # ── Pass 5: cv2.QRCodeDetector (extreme angles) ──
        if not found and self.enable_multiscale:
            found = self.try_cv2_qr(frame)

        # ── Pass 6–7: Downscale pyramid ──
        if not found and self.enable_multiscale:
            for scale in (0.75, 0.5):
                h, w = enhanced.shape[:2]
                down = cv2.resize(enhanced,
                                  (int(w * scale), int(h * scale)),
                                  interpolation=cv2.INTER_AREA)
                found = self.try_pyzbar(down, f'CLAHE@{int(scale*100)}%')
                if found:
                    break

        # ── Preview: CLAHE image (what the decoder sees) ──
        if self.show_preview:
            preview = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

            color = (0, 255, 0) if found else (0, 0, 255)
            radius = 16 if found else 8
            cv2.circle(preview, (24, 24), radius, color, -1)

            status = 'FOUND' if found else 'scanning...'
            cv2.putText(preview, f'{self.actual_w}x{self.actual_h}  CLAHE  {status}',
                        (48, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (255, 255, 255), 2)

            cv2.imshow('QR Scanner (CLAHE view)', preview)
            cv2.waitKey(1)

    def destroy_node(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = QRScannerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        print(f'[ERROR] {e}', flush=True)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
