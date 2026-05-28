cmake_minimum_required(VERSION 3.5)
project(origincar_qr)

# C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(OpenCV REQUIRED)

# Find zbar via pkg-config (no CMake config file provided by libzbar-dev)
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZBAR REQUIRED IMPORTED_TARGET zbar)

# === C++ node ===
add_executable(qr_scanner_node src/qr_scanner_node.cpp)
ament_target_dependencies(qr_scanner_node rclcpp)
target_link_libraries(qr_scanner_node
  ${OpenCV_LIBS}
  PkgConfig::ZBAR
)
target_include_directories(qr_scanner_node PRIVATE
  ${OpenCV_INCLUDE_DIRS}
)

install(TARGETS qr_scanner_node
  DESTINATION lib/${PROJECT_NAME}
)

# === Python node ===
ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS scripts/qr_scanner_py_node
  DESTINATION lib/${PROJECT_NAME}
)

# === Launch files ===
install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)

# === Tests ===
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
