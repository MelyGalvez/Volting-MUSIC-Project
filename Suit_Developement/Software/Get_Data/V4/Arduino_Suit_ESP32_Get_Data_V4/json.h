#pragma once

#include <Arduino.h>

#include "types.h"


// ================================================
// JSON.h
// ================================================


/**
 * @brief Serialize a snapshot into a fixed buffer.
 *
 * Allocation-free. See PROTOCOL.md at the repository root
 * for the packet format (protocol v2).
 *
 * @return payload length, or 0 if the buffer was too small.
 */
size_t buildJson(
    char* buf,
    size_t cap,
    const Snapshot& snap,
    SystemState state
);
