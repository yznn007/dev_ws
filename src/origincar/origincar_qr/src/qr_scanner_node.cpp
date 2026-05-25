// qr_scanner_node.cpp — QR code scanner for OriginCar.
// Uses OpenCV (V4L2 backend) for camera capture + preprocessing,
// libzbar for QR decoding.
// Multi-pass: CLAHE → CLAHE+Sharpen → Adaptive Binary → downscale pyramid.
// Auto-detects max camera resolution (set frame_width=0 / frame_height=0).
// Low-latency preview shows the CLAHE-enhanced image.

#include <iostream>
#include <string>
#include <memory>

#include <rclcpp/rclcpp.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/imgproc.hpp>
#include <zbar.h>

class QRScannerNode : public rclcpp::Node
{
public:
  QRScannerNode()
  : Node("qr_scanner_node")
  {
    // ── Declare parameters ──
    this->declare_parameter("camera_id", 0);
    this->declare_parameter("frame_width", 0);   // 0 = auto-detect max
    this->declare_parameter("frame_height", 0);
    this->declare_parameter("scan_rate_hz", 10.0);
    this->declare_parameter("show_preview", false);
    this->declare_parameter("enable_multiscale", true);
    this->declare_parameter("clahe_clip_limit", 2.0);
    this->declare_parameter("clahe_tile_size", 8);

    int camera_id   = this->get_parameter("camera_id").as_int();
    int req_w       = this->get_parameter("frame_width").as_int();
    int req_h       = this->get_parameter("frame_height").as_int();
    double rate     = this->get_parameter("scan_rate_hz").as_double();
    show_preview_   = this->get_parameter("show_preview").as_bool();
    enable_multiscale_ = this->get_parameter("enable_multiscale").as_bool();
    double clahe_clip = this->get_parameter("clahe_clip_limit").as_double();
    int clahe_tile  = this->get_parameter("clahe_tile_size").as_int();

    // ── Open camera (force V4L2 backend — avoids GStreamer issues) ──
    cap_.open(camera_id, cv::CAP_V4L2);
    if (!cap_.isOpened()) {
      // Fallback: try default backend
      cap_.open(camera_id);
    }
    if (!cap_.isOpened()) {
      RCLCPP_ERROR(this->get_logger(),
        "Cannot open camera /dev/video%d", camera_id);
      throw std::runtime_error("Camera not available");
    }

    // MJPG fourcc – most USB cameras support higher resolutions with MJPG
    cap_.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));

    // ── Single-frame buffer: eliminate preview latency ──
    cap_.set(cv::CAP_PROP_BUFFERSIZE, 1);

    // ── Resolution: auto-detect or explicit ──
    if (req_w > 0 && req_h > 0) {
      cap_.set(cv::CAP_PROP_FRAME_WIDTH,  req_w);
      cap_.set(cv::CAP_PROP_FRAME_HEIGHT, req_h);
    } else {
      // Auto-detect: set impossibly high → V4L2 clamps to max supported
      cap_.set(cv::CAP_PROP_FRAME_WIDTH,  10000);
      cap_.set(cv::CAP_PROP_FRAME_HEIGHT, 10000);
    }
    actual_w_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH));
    actual_h_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT));

    // Sanity check
    if (actual_w_ > 3840 || actual_h_ > 2160 ||
        actual_w_ <= 0 || actual_h_ <= 0) {
      RCLCPP_WARN(this->get_logger(),
        "Resolution probe returned %dx%d, falling back to 1920x1080",
        actual_w_, actual_h_);
      cap_.set(cv::CAP_PROP_FRAME_WIDTH,  1920);
      cap_.set(cv::CAP_PROP_FRAME_HEIGHT, 1080);
      actual_w_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH));
      actual_h_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT));
    }

    RCLCPP_INFO(this->get_logger(),
      "Camera ready: /dev/video%d @ %dx%d",
      camera_id, actual_w_, actual_h_);

    // ── CLAHE ──
    clahe_ = cv::createCLAHE(clahe_clip, cv::Size(clahe_tile, clahe_tile));

    // ── ZBar: QR only ──
    scanner_.set_config(zbar::ZBAR_NONE, zbar::ZBAR_CFG_ENABLE, 0);
    scanner_.set_config(zbar::ZBAR_QRCODE, zbar::ZBAR_CFG_ENABLE, 1);

    // ── Preview window ──
    if (show_preview_) {
      cv::namedWindow("QR Scanner (CLAHE view)", cv::WINDOW_NORMAL);
      int pw = std::min(actual_w_, 960);
      int ph = std::min(actual_h_, 540);
      if (pw > 0 && ph > 0) {
        cv::resizeWindow("QR Scanner (CLAHE view)", pw, ph);
      }
    }

    // ── Scan timer ──
    int period_ms = static_cast<int>(1000.0 / rate);
    timer_ = this->create_wall_timer(
      std::chrono::milliseconds(period_ms),
      std::bind(&QRScannerNode::scan_once, this));

    RCLCPP_INFO(this->get_logger(),
      "QR scanner started | rate=%.1f Hz | %dx%d | "
      "multiscale=%s | CLAHE=%.1f/%d | preview=%s",
      rate, actual_w_, actual_h_,
      enable_multiscale_ ? "on" : "off",
      clahe_clip, clahe_tile,
      show_preview_ ? "on" : "off");
  }

  ~QRScannerNode() override
  {
    if (cap_.isOpened()) {
      cap_.release();
    }
    cv::destroyAllWindows();
  }

private:
  // ── Try decode with zbar ──
  bool try_decode(const cv::Mat& gray_img, const std::string& pass_name)
  {
    zbar::Image zbar_img(gray_img.cols, gray_img.rows, "Y800",
      const_cast<uchar*>(gray_img.data), gray_img.cols * gray_img.rows);
    scanner_.scan(zbar_img);

    bool found = false;
    for (auto it = zbar_img.symbol_begin(); it != zbar_img.symbol_end(); ++it) {
      if (it->get_type() == zbar::ZBAR_QRCODE) {
        std::string data = it->get_data();
        RCLCPP_INFO(this->get_logger(),
          "✓ QR [%s]: %s", pass_name.c_str(), data.c_str());
        std::cout << data << std::endl;
        found = true;
      }
    }
    return found;
  }

  // ── Preprocessing ──
  cv::Mat preprocess_clahe(const cv::Mat& gray)
  {
    cv::Mat enhanced;
    clahe_->apply(gray, enhanced);
    return enhanced;
  }

  cv::Mat preprocess_sharpen(const cv::Mat& gray)
  {
    cv::Mat blurred;
    cv::GaussianBlur(gray, blurred, cv::Size(0, 0), 3.0);
    cv::Mat sharp;
    cv::addWeighted(gray, 1.5, blurred, -0.5, 0, sharp);
    return sharp;
  }

  cv::Mat preprocess_binary(const cv::Mat& gray)
  {
    cv::Mat binary;
    cv::adaptiveThreshold(gray, binary, 255,
      cv::ADAPTIVE_THRESH_GAUSSIAN_C, cv::THRESH_BINARY, 15, 3);
    return binary;
  }

  // ── Main scan loop ──
  void scan_once()
  {
    // BUFFERSIZE=1 ensures at most one stale frame; read() gets the latest
    cv::Mat frame;
    cap_ >> frame;
    if (frame.empty()) {
      return;
    }

    // Convert to grayscale once
    cv::Mat gray;
    cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

    bool found = false;

    // ─── Pass 1: CLAHE ───
    cv::Mat clahe_img = preprocess_clahe(gray);
    found = try_decode(clahe_img, "CLAHE");

    // ─── Pass 2: CLAHE + sharpen ───
    if (!found && enable_multiscale_) {
      cv::Mat sharp = preprocess_sharpen(clahe_img);
      found = try_decode(sharp, "CLAHE+Sharp");
    }

    // ─── Pass 3: Adaptive binary ───
    if (!found && enable_multiscale_) {
      cv::Mat binary = preprocess_binary(gray);
      found = try_decode(binary, "Binary");
    }

    // ─── Pass 4: CLAHE + binary ───
    if (!found && enable_multiscale_) {
      cv::Mat bin_clahe = preprocess_binary(clahe_img);
      found = try_decode(bin_clahe, "CLAHE+Binary");
    }

    // ─── Pass 5–6: Downscale pyramid ───
    if (!found && enable_multiscale_) {
      for (double scale : {0.75, 0.5}) {
        cv::Mat down;
        cv::resize(clahe_img, down, cv::Size(), scale, scale,
          cv::INTER_AREA);
        found = try_decode(down,
          "CLAHE@" + std::to_string(static_cast<int>(scale * 100)) + "%");
        if (found) break;
      }
    }

    // ── Preview: CLAHE-enhanced image ──
    if (show_preview_) {
      cv::Mat preview;
      cv::cvtColor(clahe_img, preview, cv::COLOR_GRAY2BGR);

      cv::Scalar status_color = found ? cv::Scalar(0, 255, 0)
                                      : cv::Scalar(0, 0, 255);
      int radius = found ? 16 : 8;
      cv::circle(preview, cv::Point(24, 24), radius, status_color, -1);

      std::string info = std::to_string(actual_w_) + "x" +
        std::to_string(actual_h_) +
        "  CLAHE  " + (found ? "FOUND" : "scanning...");
      cv::putText(preview, info, cv::Point(48, 30),
        cv::FONT_HERSHEY_SIMPLEX, 0.55, cv::Scalar(255, 255, 255), 2);

      cv::imshow("QR Scanner (CLAHE view)", preview);
      cv::waitKey(1);
    }
  }

  cv::VideoCapture cap_;
  zbar::ImageScanner scanner_;
  rclcpp::TimerBase::SharedPtr timer_;
  cv::Ptr<cv::CLAHE> clahe_;

  bool show_preview_ = false;
  bool enable_multiscale_ = true;
  int actual_w_ = 1280;
  int actual_h_ = 720;
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
