/**
 * @file HALFactory.h
 * @brief Factory interface for HAL implementations
 */
#ifndef HAL_HAL_FACTORY_H
#define HAL_HAL_FACTORY_H

#include "IRadio.h"
#include "ISensor.h"
#include "IStorage.h"
#include <memory>

namespace arp::hal {

class HALFactory {
public:
  static std::unique_ptr<IRadio> create_radio();
  static std::unique_ptr<ISensor> create_sensor();
  static std::unique_ptr<IStorage> create_storage();
};

} // namespace arp::hal

#endif // HAL_HAL_FACTORY_H
