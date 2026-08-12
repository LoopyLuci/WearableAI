cmake_minimum_required(VERSION 3.20)
project(arp-2040 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ─────────────────────────────────────────────────────────────────────────────
# Top-level targets
# ─────────────────────────────────────────────────────────────────────────────

add_custom_target(firmware ALL
  COMMAND ${CMAKE_COMMAND} -E echo "Building firmware via PlatformIO..."
  COMMAND pio run -e nano_rp2040_connect
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/firmware
  USES_TERMINAL
)

add_custom_target(host-tools ALL
  COMMAND ${CMAKE_COMMAND} -E echo "Building host tools..."
  COMMAND python -m pip install -r requirements.txt
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/host-tools
  USES_TERMINAL
)

add_custom_target(mobile-server ALL
  COMMAND ${CMAKE_COMMAND} -E echo "Building mobile server (Flutter)..."
  COMMAND flutter pub get
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/mobile-server
  USES_TERMINAL
)

add_custom_target(desktop-server ALL
  COMMAND ${CMAKE_COMMAND} -E echo "Building desktop server..."
  COMMAND npm install
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/desktop-server
  USES_TERMINAL
)

add_custom_target(test ALL
  DEPENDS firmware host-tools
  COMMAND ctest --output-on-failure
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
)

enable_testing()
add_subdirectory(tests)
