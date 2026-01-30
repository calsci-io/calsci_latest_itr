# 🧮 CalSci – The Programmable Scientific Calculator Built on ESP32-S3

**CalSci** is a **programmable scientific calculator** designed from scratch for engineers, students, and makers.  
It runs entirely on **MicroPython**, powered by the **ESP32-S3 N16R8**, combining the simplicity of a calculator with the flexibility of a microcontroller.

---

## 🚀 Overview

CalSci is not just a calculator — it’s a **mini embedded computing platform**.  
You can write, save, and run MicroPython apps directly on the calculator. Each feature — from scientific computation to GPIO control — is implemented in MicroPython, making CalSci **hackable, extensible, and educational**.

---

## ⚙️ Hardware

| Component | Description |
|------------|-------------|
| **MCU** | ESP32-S3 N16R8 (dual-core, 240 MHz, 16 MB Flash, 8 MB PSRAM) |
| **Display** | Monochrome graphical LCD (ST7565 driver) |
| **Input** | 40+ key matrix keypad |
| **Storage** | Internal Flash + microSD card support |
| **Connectivity** | USB, Wi-Fi, Bluetooth |
| **Power** | Li-ion battery with power management |
| **Expansion** | GPIO headers for sensors and I/O projects |

---

## 💡 Key Features

- 🧮 **Full Scientific Calculator** – Supports trigonometric, logarithmic, matrix, and symbolic math (via MicroPython libraries).  
- 💻 **Programmable in MicroPython** – Write your own apps directly on-device.  
- 🧠 **Modular App System** – Multiple apps run in a scheduler loop (e.g., calculator, graph plotter, GPIO monitor).  
- 🔌 **Sensor & GPIO Access** – Interface with sensors, modules, and actuators via ESP32 pins.  
- ☁️ **Cloud Integration** – Sync and download new apps via Wi-Fi (planned).  
- ⚡ **Fast Boot and Low Power** – Optimized for responsiveness and portability.  
- 🔐 **Protected System Files** – Core apps (like `main.py`) are integrated into firmware for security.

---

## 🧱 Software Architecture

+-----------------------------------+
| CalSci UI / App Framework |
| - Calculator App |
| - Graphing App |
| - GPIO Tool |
| - File Manager |
+-----------------------------------+
| MicroPython Runtime (ESP32-S3) |
| - Framebuffer Display Driver |
| - Keypad Scanner |
| - Thread-safe App Scheduler |
| - Power & Memory Manager |
+-----------------------------------+
| ESP-IDF / Hardware Abstraction |
+-----------------------------------+

software architecture needs to be edited
