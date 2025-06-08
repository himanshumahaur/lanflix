# PIPEMESH: Decentralized LAN-Based File Distribution and Streaming System

> A peer-to-peer real-time file streaming solution for local area networks (LAN).

## Overview

**PIPEMESH** is a lightweight, decentralized application that enables efficient distribution and real-time streaming of files across devices in a LAN. The system leverages custom protocols and media chunking to eliminate centralized bottlenecks and provide seamless playback.

Developed as part of the **Design Lab** course at MNIT Jaipur, this project focuses on practical applications in environments like distributed AI training, where localized data access is critical.

## Features

- **Dynamic Peer Discovery** using broadcast-based DSC messages
- **Chunk-Based Distribution** with FFmpeg for 10s segments
- **Real-Time Streaming** powered by OpenCV rendering
- **Multi-threaded Transfers** for simultaneous chunk handling
- **Redundancy and Fault Tolerance** through random peer allocation
- **Throughput** of ~850–900 Mbps on LAN

## Architecture

- **Peer Network Layer**: Manages device connections and peer list.
- **Streaming Engine**: Handles segmentation, buffering, and playback.
- **Distribution Manager**: Coordinates chunk uploads, downloads, and error recovery.

## Technologies Used

- **Python 3**
- **FFmpeg CLI** – For segmenting MP4 files
- **OpenCV** – For video rendering
- **Socket Programming** – Custom TCP protocol
- **Multithreading** – For concurrent data streams
- **Bash** – For auxiliary scripts

## Protocol Design

| Flag | Mnemonic | Description             |
|------|----------|-------------------------|
| 0x00 | REQ      | Request a chunk         |
| 0x01 | RES      | Send a video frame      |
| 0x02 | UPL      | Upload a new chunk      |
| 0x03 | TBL      | Share distribution info |
| 0x04 | DSC      | Peer discovery packet   |

## Prerequisites
- Python 3.x
- FFmpeg installed and added to `PATH`
- OpenCV (`pip install opencv-python`)
