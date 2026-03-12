# Android ADB Monitor

This Python script monitors an Android device through `adb` and records basic system stats over time.

## What it tracks
- CPU usage
- Load average
- RAM usage
- Battery percentage
- Battery temperature
- Battery voltage
- Top running processes

## Requirements
- Python 3
- `adb` installed and available in PATH
- Android device connected with USB debugging enabled

## Run
```bash
python monitor.py
