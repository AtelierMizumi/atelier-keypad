/*
 * Atelier rev 2.0: buttons read as libhmk keys (issue #12). GPL-3.0-or-later.
 */
#include "digital_keys.h"

#include "at32f402_405.h"
#include "eeconfig.h"
#include "hardware/hardware.h"

typedef struct {
  gpio_type *port;
  uint16_t pin;
} digital_pin_t;

static const digital_pin_t pins[] = DIGITAL_KEYS_PINS;

_Static_assert(DIGITAL_KEYS_FIRST + M_ARRAY_SIZE(pins) == NUM_KEYS,
               "every key after the analog ones needs a pin");

static debounce_t debounce[M_ARRAY_SIZE(pins)];

void digital_keys_init(void) {
  gpio_init_type init;

  crm_periph_clock_enable(CRM_GPIOA_PERIPH_CLOCK, TRUE);
  crm_periph_clock_enable(CRM_GPIOB_PERIPH_CLOCK, TRUE);
  crm_periph_clock_enable(CRM_GPIOC_PERIPH_CLOCK, TRUE);
  for (uint32_t i = 0; i < M_ARRAY_SIZE(pins); i++) {
    gpio_default_para_init(&init);
    init.gpio_pins = pins[i].pin;
    init.gpio_mode = GPIO_MODE_INPUT;
    init.gpio_pull = GPIO_PULL_UP; // the button closes to GND
    gpio_init(pins[i].port, &init);
  }
}

uint16_t digital_keys_adc(uint32_t key) {
  const uint32_t i = key - DIGITAL_KEYS_FIRST;
  const bool raw = gpio_input_data_bit_read(pins[i].port, pins[i].pin) == RESET;
  const bool pressed = debounce_update(&debounce[i], raw, timer_read());
  return digital_key_value(pressed, eeconfig->calibration.initial_rest_value,
                           ADC_MAX_VALUE);
}
