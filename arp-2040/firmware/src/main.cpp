#include <Arduino.h>
#include "common/common_types.h"
#include "hal/ISensor.h"
#include "hal/IRadio.h"
#include "hal/ICrypto.h"
#include "hal/IStorage.h"
#include "hal/IPower.h"
#include "hal/IAudio.h"
#include "ai/TFLiteMicroRuntime.h"

void setup() {
  Serial.begin(921600);
  while (!Serial && millis() < 3000) { delay(10); }
  Serial.println(F("ARP-2040 Connect minimal boot OK"));
}

void loop() {
  delay(1000);
}
