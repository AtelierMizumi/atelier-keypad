/*
Copyright 2012 Jun Wako <wakojun@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#pragma once

#include "config_common.h"

/* USB Device descriptor parameter */
#define VENDOR_ID       0xFEED
#define PRODUCT_ID      0x6060
#define DEVICE_VER      0x0001
#define MANUFACTURER    thuanc177
#define PRODUCT         alter6k
#define DESCRIPTION     The Alter6k keypad

/* key matrix size */
#define MATRIX_ROWS 3
#define MATRIX_COLS 3

/* key matrix pins */
#define MATRIX_ROW_PINS { D5, D6, D7 }
#define MATRIX_COL_PINS { D1, D2, D3 }
#define UNUSED_PINS { B0, B1, B2, B3, B5, B6, B7, C6, C6, D4, E6, F0, F1, F4, F5, F6, F7  }

/* COL2ROW or ROW2COL */
#define DIODE_DIRECTION COL2ROW

/* number of backlight levels */
#define BACKLIGHT_PIN B4
#define BACKLIGHT_LEVELS 8

/* Set 0 if debouncing isn't needed */
#define DEBOUNCING_DELAY 5

/* Mechanical locking support. Use KC_LCAP, KC_LNUM or KC_LSCR instead in keymap */
#define LOCKING_SUPPORT_ENABLE

/* Locking resynchronize hack */
#define LOCKING_RESYNC_ENABLE

/* key combination for command */
#define IS_COMMAND() ( \
    keyboard_report->mods == (MOD_BIT(KC_LSHIFT) | MOD_BIT(KC_RSHIFT)) \
)

/* prevent stuck modifiers */
#define PREVENT_STUCK_MODIFIERS

/*Extra stuffs I added myself */
#define USB_POLLING_INTERVAL_MS 1
#define FORCE_NKRO
#define BOOTMAGIC_LITE_ROW 0
#define BOOTMAGIC_LITE_COLUMN 0

/*RGB config and shits*/
#define RGB_DI_PIN D0
#define RGBLIGHT_ANIMATIONS
#define RGBLED_NUM 6
#define RGBW
#define RGBLIGHT_HUE_STEP 12
#define RGBLIGHT_SAT_STEP 25
#define RGBLIGHT_VAL_STEP 8
#define RGBLIGHT_EFFECT_BREATHING
#define RGBLIGHT_EFFECT_RAINBOW_MOOD
#define RGBLIGHT_EFFECT_RAINBOW_SWIRL
#define RGBLIGHT_EFFECT_GRADIENT
#define RGBLIGHT_DEFAULT_MODE RGBLIGHT_MODE_RAINBOW_MOOD

#define USB_MAX_POWER_CONSUMPTION 500