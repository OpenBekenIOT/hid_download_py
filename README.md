> ❗ BEWARE <br/>
> THIS REPO HAS MOVED TO https://github.com/OpenBekenIOT

# What is this?

This repo is a fork of a Beken repo which can program BK7231x series devices over serial (UART / SPI) using the serial bootloader.

The HID support has been disabled in this fork. You no longer need to install the required libraries. **Using on Microsoft Windows is therefore easier now**

Improvements in this repository:

1. Ability to read out the flash
2. "Unpackaging" and decrryption of encrypted flash images
3. Addition of `spiprogram`: this works on a Raspberry Pi using itss native SPI.   
   See [SPIFlash.md](https://github.com/OpenBekenIOT/hid_download_py/blob/master/SPIFlash.md) and [rpi3install.md](https://github.com/OpenBekenIOT/hid_download_py/blob/master/rpi3install.md)

This Python flasher is intended to be used with the OpenBeken project software:

- openshwprojects / [OpenBK7231T_App](https://github.com/openshwprojects/OpenBK7231T_App)
- openshwprojects / [OpenBK7231N](https://github.com/openshwprojects/OpenBK7231N) – for BK7231<u>N</u>
- openshwprojects / [OpenBK7231T](https://github.com/openshwprojects/OpenBK7231T) – for BK7231<u>T</u>

# Installation

## Debian / Ubuntu

```bash
$ apt install python3-hid python3-serial python3-tqdm
$ python3 setup.py install --user
```

## Windows

```batch
pip install hid pyserial tqdm
python setup.py install
```


# SPI Usage

(disabled by default in this repo)

```bash
hidprogram -h
usage: hidprogram [-h] [-c {bk7231,bk7231s,bk7231u,bk7221u,bk7251}] [-m {soft,hard}] filename

Beken HID Downloader.

positional arguments:
  filename              specify file_crc.bin

optional arguments:
  -h, --help            show this help message and exit
  -c {bk7231,bk7231s,bk7231u,bk7221u,bk7251}, --chip {bk7231,bk7231s,bk7231u,bk7221u,bk7251}
                        chip type
  -m {soft,hard}, --mode {soft,hard}
```

# Uart downloader Usage

```bash
usage: uartprogram [-h] [-d DEVICE] [-s STARTADDR] [-l LENGTH] [-b BAUDRATE]
                   [-u] [-r] [-w] [-p]
                   filename

Beken Uart Downloader.

positional arguments:
  filename              specify file_crc.bin

optional arguments:
  -h, --help            show this help message and exit
  -d DEVICE, --device DEVICE
                        Uart device, default /dev/ttyUSB0
  -s STARTADDR, --startaddr STARTADDR
                        burn flash address, defaults to 0x11000
  -l LENGTH, --length LENGTH
                        length to read, defaults to 0x1000
  -b BAUDRATE, --baudrate BAUDRATE
                        burn uart baudrate, defaults to 1500000
  -u, --unprotect       unprotect flash first, used by BK7231N
  -r, --read            read flash
  -w, --write           read flash
  -p, --unpackage       unPackage firmware
```

_For __BK7231T__: the download start address defaults to `0x11000`. **Do not** set the `--unprotect` option._<br/>
_For __BK7231N__: set the download start address to `0x0` by passing the argument `-s 0x0`. **Do** set the `--unprotect` option._


_The baud rate can be modified for faster/slower, e.g. `--baudrate 115200` for more reliable with dodgy connections_

## flashing

Run the following, replacing `<path_to_image.bin>` with the path to your image, and `<COM>` with your serial port number. Re-power the unit or briefly ground CEN (Chip ENable), repeating until the flashing starts.

`python uartprogram <path_to_image.bin> --device <COM> --write`

## reading

Run the following, replacing `<path_to_image.bin>` with the path where you'd like to save the image, and `<COM>` with your serial port number. Re-power the unit or briefly ground CEN (Chip ENable), repeating until the reading starts.

`python uartprogram <path_to_image.bin> --device <COM> --read`

# unpackage

Replace `<path_to_image.bin>` with the path to your image.

`python uartprogram <path_to_image.bin> --unpackage`

 # Detailed examples of flashing Beken chips

Please see our detailed step by step guides for more information:

[LED WiFi RGBCW Tuya - teardown, BK7231N, programming with my Tasmota replacement](https://www.elektroda.com/rtvforum/topic3880540.html)<br/>
[Garden Tuya CCWFIO232PK Double Relay - BK7231T - Programming](https://www.elektroda.com/rtvforum/topic3875654.html)<br/>
[Qiachip Smart Switch - BK7231N / CB2S - interior, programming](https://www.elektroda.com/rtvforum/topic3874289.html)<br/>




