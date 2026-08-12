/**
 * @file HALFactory.cpp
 * @brief Factory for creating HAL implementations
 */
#include "HALFactory.h"
#include "NINARadio.h"
#include "RP2040Sensor.h"
#include "MockStorage.h"

namespace arp::hal {

std::unique_ptr<IRadio> HALFactory::create_radio() {
  return std::make_unique<NINARadio>();
}

std::unique_ptr<ISensor> HALFactory::create_sensor() {
  return std::make_unique<RP2040Sensor>();
}

std::unique_ptr<IStorage> HALFactory::create_storage() {
  return std::make_unique<MockStorage>();
}

}  // namespace arp::hal
