# Multi-Module Vision System for Real-Time Person Identification and Threat Detection

## Overview

This system is an intelligent security prototype based on real-time image analysis. It enables face recognition from camera footage and detects potential threats, such as the presence of dangerous objects.

## Key Features

- **Real-time Identification:** instant face recognition and verification powered by **Azure Face API** for high accuracy and scalability.
- **Threat Detection:** automated detection of dangerous objects, specifically tuned to identify **pistols** and **knives**.
- **Incident Management:** automatic recording of security events, including image snapshots and video clips stored in **Azure Blob Storage**.
- **Security Interface:** a functional Electron-based UI designed specifically for monitoring and managing alerts in real-time.

## Tech Stack

- **Backend:** Python, OpenCV
- **Frontend:** Electron (JavaScript, HTML, CSS)
- **AI & Cloud Services:**
  - **Azure Face API**
  - **Azure Blob Storage** (incident data & media storage)
  - **Local AI Model** (real-time weapon detection)
