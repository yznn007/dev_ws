// qr_scanner_node.cpp — QR code scanner for OriginCar.
// Uses OpenCV for camera capture + preprocessing, libzbar for QR decoding.
// Multi-pass: CLAHE → adaptive binary → multi-resolution downscale pyramid.
// Prints decoded QR data to stdout.

#include <iostream>
#include <string>
#include <memory>
#include <vector>
#include <algorithm>

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
    this->declare_parameter("frame_width", 1280);
    this->declare_parameter("frame_height", 720);
    this->declare_parameter("scan_rate_hz", 10.0);
    this->declare_parameter("show_preview", false);
    this->declare_parameter("enable_multiscale", true);
    this->declare_parameter("clahe_clip_limit", 2.0);
    this->declare_parameter("clahe_tile_size", 8);

    int camera_id = this->get_parameter("camera_id").as_int();
    fw_ = this->get_parameter("frame_width").as_int();
    fh_ = this->get_parameter("frame_height").as_int();
    double rate = this->get_parameter("scan_rate_hz").as_double();
    show_preview_ = this->get_parameter("show_preview").as_bool();
    enable_multiscale_ = this->get_parameter("enable_multiscale").as_bool();
    double clahe_clip = this->get_parameter("clahe_clip_limit").as_double();
    int clahe_tile = this->get_parameter("clahe_tile_size").as_int();

    // ── Open camera ──
    cap_.open(camera_id);
    if (!cap_.isOpened()) {
      RCLCPP_ERROR(this->get_logger(),
        "Cannot open camera /dev/video%d", camera_id);
      throw std::runtime_error("Camera not available");
    }
    cap_.set(cv::CAP_PROP_FRAME_WIDTH, fw_);
    cap_.set(cv::CAP_PROP_FRAME_HEIGHT, fh_);
    // Also try MJPG format for higher FPS at HD resolution
    cap_.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
    actual_w_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_WIDTH));
    actual_h_ = static_cast<int>(cap_.get(cv::CAP_PROP_FRAME_HEIGHT));
    RCLCPP_INFO(this->get_logger(),
      "Camera opened: /dev/video%d @ %dx%d", camera_id, actual_w_, actual_h_);

    // ── CLAHE (Contrast Limited Adaptive Histogram Equalization) ──
    // Enhances local contrast → zbar sees QR finder patterns better at distance
    clahe_ = cv::createCLAHE(clahe_clip, cv::Size(clahe_tile, clahe_tile));

    // ── ZBar: enable QR only ──
    scanner_.set_config(zbar::ZBAR_NONE, zbar::ZBAR_CFG_ENABLE, 0);
    scanner_.set_config(zbar::ZBAR_QRCODE, zbar::ZBAR_CFG_ENABLE, 1);

    // ── Preview window ──
    if (show_preview_) {
      cv::namedWindow("Camera Preview", cv::WINDOW_NORMAL);
      cv::resizeWindow("Camera Preview",
        std::min(actual_w_ / 2, 640), std::min(actual_h_ / 2, 360));
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
  // ── Try decode one image with zbar ──
  // Returns true if at least one QR code was found.
  bool try_decode(const cv::Mat& gray_img, const std::string& pass_name)
  {
    // zbar is read-only on the buffer, const_cast is safe
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

  // ── Preprocessing: CLAHE on grayscale ──
  cv::Mat preprocess_clahe(const cv::Mat& gray)
  {
    cv::Mat enhanced;
    clahe_->apply(gray, enhanced);
    return enhanced;
  }

  // ── Preprocessing: adaptive threshold → binary ──
  // Sharp black/white helps zbar when contrast is poor.
  cv::Mat preprocess_binary(const cv::Mat& gray)
  {
    cv::Mat binary;
    cv::adaptiveThreshold(gray, binary, 255,
      cv::ADAPTIVE_THRESH_GAUSSIAN_C, cv::THRESH_BINARY, 15, 3);
    return binary;
  }

  // ── Sharpening kernel ──
  cv::Mat preprocess_sharpen(const cv::Mat& gray)
  {
    cv::Mat sharp;
    cv::GaussianBlur(gray, sharp, cv::Size(0, 0), 3.0);
    cv::addWeighted(gray, 1.5, sharp, -0.5, 0, sharp);
    return sharp;
  }

  // ── Main scan loop ──
  void scan_once()
  {
    cv::Mat frame;
    cap_ >> frame;
    if (frame.empty()) {
      return;
    }

    // Convert to grayscale once
    cv::Mat gray;
    cv::cvtColor(frame, gray, cv::COLOR_BGR2GRAY);

    bool found = false;

    // ─── Pass 1: CLAHE enhanced grayscale ───
    // Best general-purpose: fixes uneven lighting, exposes QR patterns
    cv::Mat clahe_img = preprocess_clahe(gray);
    found = try_decode(clahe_img, "CLAHE");

    // ─── Pass 2: CLAHE + sharpen ───
    // Extra edge enhancement for distant/blurry codes
    if (!found && enable_multiscale_) {
      cv::Mat sharp = preprocess_sharpen(clahe_img);
      found = try_decode(sharp, "CLAHE+Sharp");
    }

    // ─── Pass 3: Adaptive binary ───
    // Pure black/white; zbar sometimes prefers this
    if (!found && enable_multiscale_) {
      cv::Mat binary = preprocess_binary(gray);
      found = try_decode(binary, "Binary");
    }

    // ─── Pass 4: Adaptive binary on CLAHE'd input ───
    if (!found && enable_multiscale_) {
      cv::Mat bin_clahe = preprocess_binary(clahe_img);
      found = try_decode(bin_clahe, "CLAHE+Binary");
    }

    // ─── Pass 5–6: Downscale pyramid ───
    // When QR is very close/large, downscaling reduces noise
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

    // ── Show camera preview ──
    if (show_preview_) {
      cv::Mat display = frame.clone();

      // Mark detection status
      cv::Scalar status_color = found ? cv::Scalar(0, 255, 0)
                                      : cv::Scalar(0, 0, 255);
      int radius = found ? 20 : 10;
      cv::circle(display, cv::Point(30, 30), radius, status_color, -1);

      // Overlay resolution and status text
      std::string info = std::to_string(actual_w_) + "x" +
        std::to_string(actual_h_) + (found ? " FOUND" : " scanning...");
      cv::putText(display, info, cv::Point(60, 36),
        cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(255, 255, 255), 2);

      cv::imshow("Camera Preview", display);
      cv::waitKey(1);
    }
  }

  cv::VideoCapture cap_;
  zbar::ImageScanner scanner_;
  rclcpp::TimerBase::SharedPtr timer_;
  cv::Ptr<cv::CLAHE> clahe_;

  bool show_preview_ = false;
  bool enable_multiscale_ = true;
  int fw_ = 1280;
  int fh_ = 720;
  int actual_w_ = 0;
  int actual_h_ = 0;
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
