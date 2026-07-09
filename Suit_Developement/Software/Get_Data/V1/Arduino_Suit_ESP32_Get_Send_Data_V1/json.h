#pragma once

#include <Arduino.h>


// ================================================
// JSON.h
// ================================================


// ------------------ Json functions --------------


/**
 * @brief Build the JSON response containing all sensor data.
 *
 * @return JSON string.
 */
String buildJson();