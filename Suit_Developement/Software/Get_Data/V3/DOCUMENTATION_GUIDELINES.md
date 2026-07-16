# Documentation Guidelines

## Goal

Your objective is to reverse engineer the project and produce a README that explains **how the project works internally**, not simply what it does.

The documentation is intended for someone who:

- has never seen the project before;
- is not necessarily an experienced programmer;
- wants to understand the complete logic of the software before reading the source code.

The README should therefore teach the project progressively.

---

# Writing Style

The README must be educational.

Always explain:

- WHY something exists
- THEN HOW it works
- THEN WHERE it is implemented

Never immediately dive into code.

Avoid assuming the reader already understands:

- object-oriented programming
- networking
- embedded programming
- robotics
- HTTP
- JSON
- multithreading

Every technical concept should be introduced naturally.

Imagine explaining the project to a new engineering student.

---

# General Principle

The reader should be able to understand the software without opening a single source file.

Every important mechanism must be explained.

Every important file must appear.

Nothing important should remain "magic".

---

# Repository Philosophy

This repository is responsible only for acquiring, processing and exposing sensor data.

It is **not** responsible for displaying, visualizing or interpreting that data.

Its purpose is to provide a stable and generic HTTP API that can be consumed by any external application.

The repository should therefore be documented as a **data provider**, not as a complete application.

Do **not** assume that a Python client exists.

If examples of external software are useful, present them only as examples of applications that consume the API.

Typical consumers include:

- Python
- Unity
- TouchDesigner
- Max/MSP
- Processing
- Unreal Engine
- Web applications
- Any software capable of sending HTTP requests

The API should always be described independently of any particular client implementation.

---

# Required Structure

## 1. Project Overview

Explain:

- What the project is.
- Why it exists.
- Global objective.
- Hardware involved.
- Software involved.
- High-level architecture.

---

## 2. Global Workflow

Explain the complete lifecycle.

Example:

Power on

↓

Hardware initialization

↓

Sensor detection

↓

Calibration

↓

HTTP server starts

↓

Continuous sensor acquisition

↓

Data processing

↓

JSON generation

↓

External application requests the data

↓

Application-specific processing

Use diagrams whenever useful.

---

## 3. Folder Structure

Explain every folder.

For each one:

- purpose
- contents
- interaction with the rest of the project

---

## 4. File Explanation

For every important file explain:

- Purpose
- Responsibilities
- Main functions
- Main classes
- Dependencies
- Inputs
- Outputs
- Interaction with other files

Never simply list functions.

Explain why the file exists.

---

## 5. Communication Between Files

Explain the project as if it were a conversation.

Use real examples from the project.

Describe how information moves between internal modules before being exposed through the HTTP API.

Example:

Sensor manager acquires raw measurements.

↓

Processing module computes orientations.

↓

Calibration module adjusts reference values.

↓

HTTP server builds the JSON response.

↓

An external application requests the endpoint.

↓

The JSON data is received and interpreted by that application.

Avoid describing a specific client unless it is actually part of the repository.

This section should make the architecture immediately understandable.

---

## 6. Execution Flow

Describe what happens from startup until shutdown.

Follow the execution order.

Mention every important function involved.

---

## 7. Data Flow

Follow the data from its physical origin to its final destination.

Example:

IMU

↓

I²C bus

↓

Sensor library

↓

Orientation computation

↓

Calibration

↓

Quaternion and/or Euler computation

↓

JSON generation

↓

HTTP API

↓

External application

↓

Application-specific processing

Explain every important transformation.

---

## 8. Initialization

Explain everything that happens before the system becomes operational.

Include:

- Hardware initialization
- Sensor initialization
- Sensor detection
- Calibration
- Network initialization
- HTTP server initialization

---

## 9. Runtime

Explain the main loop.

Describe:

- what repeats continuously
- how often
- what data is updated
- what data is transmitted
- what data is received
- what triggers each operation

---

## 10. Communication Protocols

Explain every protocol used.

Examples:

- HTTP
- JSON
- Wi-Fi
- I²C
- Serial

For each protocol explain:

- why it is used
- what information is exchanged
- which modules use it

Remember that the repository acts as a generic data server.

The communication API must be documented independently of any client implementation.

---

## 11. Algorithms

Explain important algorithms using simple language.

Avoid mathematics unless necessary.

Explain the intuition behind:

- calibration
- orientation computation
- filtering
- coordinate transformations
- quaternion handling
- Euler angle conversion
- any other important processing

---

## 12. Error Handling

Explain:

- missing sensors
- initialization failures
- communication failures
- timeouts
- invalid values
- recovery mechanisms

---

## 13. Configuration

Explain every configurable parameter.

Examples:

- Pins
- Timing
- Wi-Fi configuration
- Calibration parameters
- Constants
- Sensor mappings
- Thresholds

Explain why each parameter exists.

---

## 14. Architecture Summary

End with a concise summary of the architecture.

The reader should now understand:

- where the data originates;
- how it moves through the software;
- how it is processed;
- how it is exposed through the HTTP API;
- how any external application can consume it.

Present the repository as a reusable sensor data server rather than as an application tied to a particular client.

---

# Diagrams

Whenever possible, generate Mermaid diagrams.

Prefer:

- Flowcharts
- Sequence diagrams
- Dependency graphs
- State diagrams

Diagrams should simplify understanding, not replace explanations.

---

# Writing Rules

Always introduce concepts before using them.

Always explain abbreviations.

Avoid jargon whenever possible.

Avoid unnecessary code snippets.

Prefer explanations over implementation details.

Keep paragraphs relatively short.

Cross-reference sections whenever appropriate.

Write progressively, starting from high-level concepts before moving into technical details.

---

# Important

Do NOT document the code line by line.

Explain:

- the architecture;
- the execution flow;
- the communication between modules;
- the reasoning behind the design choices.

The documentation should progressively build the reader's understanding.

Someone completely new to the project should finish the README with a clear mental model of:

- how the software is organized;
- how information flows through it;
- how each component contributes to the overall system;
- how external applications can use the exposed data.