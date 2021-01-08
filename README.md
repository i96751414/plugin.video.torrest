# plugin.video.torrest
[![Build Status](https://github.com/i96751414/plugin.video.torrest/workflows/build/badge.svg)](https://github.com/i96751414/plugin.video.torrest/actions?query=workflow%3Abuild)

Another torrent streaming engine for Kodi. It uses the [torrest service](https://github.com/i96751414/torrest), which provides an API specially made for streaming.

## Supported platforms

- Windows 32/64 bits (starting Vista)
- Linux 32/64 bits
- Linux ARM (ARMv7 and ARM64)
- OS X 64 bits
- Android (5.x and later) ARM, x86 and x64

Minimum supported Kodi version: 16 (Jarvis)

## Download

Get the [latest release](https://github.com/i96751414/plugin.video.torrest/releases/latest).  **Do NOT use the `Download ZIP` button on this page.**

## Installation

Just like any other add-on. No extra steps are required.

## Calling torrest from other addon

One can call torrest from other addons. To do so, simply use torrest API:

|Url|Description|
|---|-----------|
|`plugin://plugin.video.torrest/play_magnet?magnet=<magnet>`|Plays the provided `<magnet>`|
|`plugin://plugin.video.torrest/play_url?url=<url>`|Plays the provided torrent file `<url>`|

##  Screenshots
![screenshots](resources/screenshots/screenshots.gif)

