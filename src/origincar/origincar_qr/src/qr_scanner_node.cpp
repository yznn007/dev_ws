// qr_scanner_node.cpp — QR code scanner for OriginCar.
// Uses OpenCV for camera capture and libzbar for QR decoding.
// Prints decoded QR data to stdout.

#include <iostream>
#include <string>
#include <memory>

#include <rclcpp/rclcpp.hpp>
#include <opencv2/opencv.hpp>
#include <zbar.h>

class QRScannerNode : public rclcpp::Node
{
public:
  QRScannerNode()
  : Node("qr_scanner_node")
  {
    // Declare parameters
    this->declare_parameter("camera_id", 0);
    this->declare_parameter("frame_width", 640);
    this->declare_parameter("frame_height", 480);
    this->declare_parameter("scan_rate_hz", 10.0);
    this->declare_parameter("show_preview", false);

    int camera_id = this->get_parameter("camera_id").as_int();
    int fw = this->get_parameter("frame_width").as_int();
    int fh = this->get_parameter("frame_height").as_int();
    double rate = this->get_parameter("scan_rate_hz").as_double();
    show_preview_ = this->get_parameter("show_preview").as_bool();

    // Open camera
    cap_.open(camera_id);
    if (!cap_.isOpened()) {
      RCLCPP_ERROR(this->get_logger(),
        "Cannot open camera /dev/video%d", camera_id);
      throw std::runtime_error("Camera not available");
    }
    cap_.set(cv::CAP_PROP_FRAME_WIDTH, fw);
    cap_.set(cv::CAP_PROP_FRAME_HEIGHT, fh);
    int actual_w = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH));
    int actual_h = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT));
    RCLCPP_INFO(this->get_logger(),
      "Camera opened: /dev/video%d @ %dx%d", camera_id, actual_w, actual_h);

    // ZBar scanner
    scanner_.set_config(zbar::ZBAR_NONE, zbar::ZBAR_CFG_ENABLE, 1);

    // Preview window
    if (show_preview_) {
      cv::namedWindow("Camera Preview", cv::WINDOW_NORMAL);
      cv::resizeWindow("Camera Preview", actual_w / 2, actual_h / 2);
    }

    // Scan timer
    int period_ms = static_cast<int>(1000.0 / rate);
    timer_ = this->create_wall_timer(
      std::chrono::milliseconds(period_ms),
      std::bind(&QRScannerNode::scan_once, this));

    RCLCPP_INFO(this->get_logger(),
      "QR scanner started (rate=%.1f Hz, preview=%s). Waiting for QR codes...",
      rate, show_preview_ ? "true" : "false");
  }

  ~QRScannerNode() override
  {
    if (cap_.isOpened()) {
      cap_.release();
    }
    cv::destroyAllWindows();
  }

private:
  void scan_once()
  {
    cv::Mat frame;
    cap_ >> frame;
    if (frame.empty()) {
      return;
    }

    // Convert to grayscale for zbar
    cv::Mat gray;
    cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

    // Wrap in zbar image
    zbar::Image zbar_img(gray.cols, gray.rows, "Y800",
      gray.data, gray.cols * gray.rows);
    scanner_.scan(zbar_img);

    // Iterate results
    bool found = false;
    for (auto it = zbar_img.symbol_begin(); it != zbar_img.symbol_end(); ++it) {
      if (it->get_type() == zbar::ZBAR_QRCODE) {
        std::string data = it->get_data();
        RCLCPP_INFO(this->get_logger(), "QR detected: [%s]", data.c_str());
        std::cout << data << std::endl;
        found = true;
      }
    }

    // Show preview
    if (show_preview_) {
      cv::imshow("Camera Preview", frame);
      cv::waitKey(1);
    }
  }

  cv::VideoCapture cap_;
  zbar::ImageScanner scanner_;
  rclcpp::TimerBase::SharedPtr timer_;
  bool show_preview_ = false;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  try {
    auto node = std::make_shared<QRScannerNode>();
    rclcpp::spin(node);
  } catch (const std::exception & e) {
    std::cerr << "[ERROR] " << e.what() << std::endl;
  }
  rclcpp::shutdown();
  return 0;
}
