#pragma once


// ================================================
// SERVER.h
// ================================================


/**
 * @brief Initialize routes and start the HTTP server.
 */
void initializeServer();


/**
 * @brief Service pending HTTP clients (call from loop).
 */
void serverHandleClient();
