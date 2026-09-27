/*
 * PulseNet BLE manager
 *
 * BLE is implemented entirely in main.cpp for the current ESP32 prototype.
 * This file is intentionally kept empty to avoid having a second,
 * incompatible BLE implementation using NimBLE and different UUIDs.
 *
 * Do not add another BLE server implementation here unless the project
 * is intentionally refactored so that main.cpp no longer owns BLE.
 */