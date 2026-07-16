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

HTTP server

↓

Python connection

↓

Data processing

↓

Application

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

Purpose

Responsibilities

Main functions

Main classes

Dependencies

Inputs

Outputs

Interaction with other files

Never simply list functions.

Explain why the file exists.

---

## 5. Communication Between Files

Explain the project as if it were a conversation.

Example:

main.py asks network.py to download data.

network.py sends an HTTP request.

ESP32 answers.

network.py parses JSON.

The parsed data is returned.

main.py updates the display.

This section should make the architecture obvious.

---

## 6. Execution Flow

Describe what happens from startup until shutdown.

Follow the execution order.

Mention every important function involved.

---

## 7. Data Flow

Follow the data.

For example:

IMU

↓

I2C

↓

Sensor library

↓

Quaternion

↓

Euler conversion

↓

Calibration

↓

JSON

↓

HTTP

↓

Python

↓

Display

Follow every important transformation.

---

## 8. Initialization

Explain everything that happens before the program becomes operational.

---

## 9. Runtime

Explain the main loop.

Explain:

what repeats

how often

what updates

what is transmitted

what is received

---

## 10. Communication Protocols

Explain every protocol.

Examples:

HTTP

JSON

Wi-Fi

I2C

Serial

For each protocol explain why it is used.

---

## 11. Algorithms

Explain important algorithms using simple language.

Avoid mathematics unless necessary.

Explain the intuition.

---

## 12. Error Handling

Explain:

missing sensors

communication failures

timeouts

invalid values

recoveries

---

## 13. Configuration

Explain every configurable parameter.

Pins

Timing

Wi-Fi

Calibration

Constants

Mappings

---

## 14. Architecture Summary

End with a concise summary of the software architecture.

The reader should now understand:

- where data comes from;
- how it moves;
- who processes it;
- who displays it.

---

# Diagrams

Whenever possible, generate Mermaid diagrams.

Prefer flowcharts.

Use sequence diagrams when explaining communication.

Use dependency diagrams when explaining architecture.

---

# Writing Rules

Always introduce concepts before using them.

Always explain abbreviations.

Avoid jargon.

Avoid unnecessary code.

Prefer explanations over implementation details.

Keep paragraphs relatively short.

Cross-reference sections whenever appropriate.

---

# Important

Do NOT document line by line.

Explain the architecture.

Explain the logic.

Explain the reasoning behind the design.

The documentation should progressively build the reader's understanding.

Someone completely new to the project should finish the README with a clear mental model of how everything works.