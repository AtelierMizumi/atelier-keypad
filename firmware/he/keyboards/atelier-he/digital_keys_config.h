/* Atelier rev 2.0: Esc (SW1) and Retry (SW2), see hardware/he/circuit.py BUTTON_PINS. */
#pragma once

// Keys 0-2 are the Hall keys; keys 3 and 4 are these buttons, in this order.
#define DIGITAL_KEYS_FIRST 3
#define DIGITAL_KEYS_PINS                                                      \
  {                                                                            \
    {GPIOB, GPIO_PINS_12}, /* SW1 Esc   */                                     \
    {GPIOB, GPIO_PINS_5},  /* SW2 Retry */                                     \
  }
