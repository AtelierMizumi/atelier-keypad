// Copyright 2026 thuanc177
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// One byte of keyboard settings in emulated EEPROM: the debounce time.
#define EECONFIG_KB_DATA_SIZE 1

// Needed by the key-reactive lighting effects.
#define RGB_MATRIX_KEYPRESSES

// Bump when via.json menus change in a way older firmware cannot serve.
#define VIA_FIRMWARE_VERSION 1
