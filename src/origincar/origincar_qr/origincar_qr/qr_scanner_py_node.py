"""
qr_scanner_py_node.py — QR code scanner for OriginCar (Python version).

Opens a USB camera via OpenCV, continuously scans frames for QR codes,
and prints decoded data to stdout.
"""

import cv2
import rclpy
from rclpy.node import Node


class QRScannerNode(Node):
    """ROS 2 node that scans QR codes from a camera and prints results."""

    def __init__(self):
        super().__init__('qr_scanner_node')

        # Declare parameters
        self.declare_parameter('camera_id', 0)
        self.declare_parameter('frame_width', 640)
        self.declare_parameter('frame_height', 480)
        self.declare_parameter('scan_rate_hz', 10.0)
        self.declare_parameter('show_preview', False)

        camera_id = self.get_parameter('camera_id').value
        fw = self.get_parameter('frame_width').value
        fh = self.get_parameter('frame_height').value
        rate = self.get_parameter('scan_rate_hz').value
        self.show_preview = self.get_parameter('show_preview').value

        # Open camera
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            self.get_logger().error(
                f'Cannot open camera /dev/video{camera_id}')
            raise RuntimeError(f'Camera /dev/video{camera_id} not available')

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, fw)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, fh)
        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.get_logger().info(
            f'Camera opened: /dev/video{camera_id} @ {actual_w}x{actual_h}')

        # QR code detector
        self.detector = cv2.QRCodeDetector()

        # Preview window
        if self.show_preview:
            try:
                cv2.namedWindow('Camera Preview', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Camera Preview', actual_w // 2, actual_h // 2)
            except cv2.error:
                self.get_logger().warn(
                    'OpenCV GUI not available (missing GTK/QT). '
                    'Install opencv-python: pip install opencv-python')
                self.show_preview = False

        # Scan loop timer
        self.scan_timer = self.create_timer(1.0 / rate, self.scan_once)
        self.get_logger().info(
            f'QR scanner started (rate={rate} Hz, preview={self.show_preview}). '
            f'Waiting for QR codes...')

    def scan_once(self):
        """Grab one frame and attempt QR decode."""
        ret, frame = self.cap.read()
        if not ret:
            return

        data, pts, _ = self.detector.detectAndDecode(frame)
        if data:
            self.get_logger().info(f'QR detected: [{data}]')
            print(data, flush=True)

        # Show preview
        if self.show_preview:
            display = frame.copy()
            if data and pts is not None:
                pts_int = pts.astype(int)
                for i in range(len(pts_int)):
                    cv2.line(display, tuple(pts_int[i][0]),
                             tuple(pts_int[(i + 1) % len(pts_int)][0]),
                             (0, 255, 0), 3)
            cv2.imshow('Camera Preview', display)
            cv2.waitKey(1)

    def destroy_node(self):
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main():
    rclpy.init()
    try:
        node = QRScannerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        print(f'[ERROR] {e}', flush=True)
    finally:
        if 'node' in locals():
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
