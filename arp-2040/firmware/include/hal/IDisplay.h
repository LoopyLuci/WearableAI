/**
 * @file IDisplay.h
 * @brief Display interface — frozen contract
 */

#ifndef HAL_IDISPLAY_H
#define HAL_IDISPLAY_H

#include "common_types.h"
#include <cstdint>
#include <cstddef>

namespace arp::hal {

struct DisplayConfig {
  uint16_t width;
  uint16_t height;
  uint8_t  color_depth_bits;  // 1=mono, 8=grayscale, 16=RGB565, 24=RGB888
  bool     inverted;
};

struct DisplayRect {
  uint16_t x, y, width, height;
};

class IDisplay {
public:
  virtual ~IDisplay() = default;

  virtual ErrorCode init() = 0;
  virtual ErrorCode configure(const DisplayConfig& config) = 0;
  virtual ErrorCode clear(uint32_t color) = 0;
  virtual ErrorCode draw_pixel(uint16_t x, uint16_t y, uint32_t color) = 0;
  virtual ErrorCode draw_rect(const DisplayRect& rect, uint32_t color) = 0;
  virtual ErrorCode draw_text(const char* text, uint16_t x, uint16_t y, uint32_t color) = 0;
  virtual ErrorCode draw_bitmap(const uint8_t* bitmap, uint16_t x, uint16_t y,
                                uint16_t width, uint16_t height) = 0;
  virtual ErrorCode set_brightness(uint8_t brightness_pct) = 0;
  virtual ErrorCode set_inverted(bool inverted) = 0;
  virtual void     refresh() = 0;
  virtual DisplayConfig get_config() const = 0;
};

} // namespace arp::hal

#endif // HAL_IDISPLAY_H
