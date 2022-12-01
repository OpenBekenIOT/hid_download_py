# encoding: utf8
#
# UART Download Tool
#
# Copyright (c) BekenCorp. (chunjian.tian@bekencorp.com).  All rights reserved.
#
# This software may be distributed under the terms of the BSD license.
# See README for more details.

import time
from .boot_intf import CBootIntf
import serial 
from serial import Timeout
#from serial import serialutil
import binascii
from tqdm import tqdm
from .flash_list import *

debug = False


# make crc32 table
crc32_table = []
for i in range(0,256):
    c = i
    for j in range(0,8):
        if c&1:
            c = 0xEDB88320 ^ (c >> 1)
        else:
            c = c >> 1
    crc32_table.append(c)

# print(crc32_table)

def crc32_ver2(crc, buf):
    for c in buf:
        crc = (crc>>8) ^ crc32_table[(crc^c)&0xff]
    return crc

class UartDownloader(object):
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, unprotect=False):
        # self.bootItf = CBootIntf(port, 115200, 0.01)

        self.target_baudrate = baudrate
        self.unprotect = unprotect
        self.pbar = None
        self.bootItf = CBootIntf(port, 115200, 0)
        self.log("UartDownloader....")
        
    def log(self, text):
        """
        print text to tqdm progress bar
        """
        if not self.pbar:
            print("{}".format(text))
        else:
            self.pbar.set_description("{:<16}".format(text))

    def do_reset_signal(self):
        self.bootItf.ser.dtr = 0
        self.bootItf.ser.rts = 1
        time.sleep(0.2)
        self.bootItf.ser.rts = 0

    def read(self, filename, startAddr=0x11000, length=0x119000):
        self.do_reset_signal()
        self.log("Read Getting Bus...")
        timeout = Timeout(10)

        fileBuf = b''
        total_num = length # 0x1000
        #self.pbar = tqdm(total=total_num, ascii=True, ncols=80, unit_scale=True,
        #        unit='k', bar_format='{desc}|{bar}|[{rate_fmt:>8}]')

        # Step2: Link Check
        count = 0
        while True:
            r = self.bootItf.LinkCheck()
            if r:
                break
            if timeout.expired():
                self.log('Cannot get bus.')
                self.pbar.close()
                return
            count += 1
            if count > 500:
                self.bootItf.Start_Cmd(b"reboot\r\n")
                count = 0
            # time.sleep(0.01)

        self.log("Gotten Bus...")
        time.sleep(0.1)
        self.bootItf.Drain()

        # Step3: set baudrate, delay 100ms
        if self.target_baudrate != 115200:
            if not self.bootItf.SetBR(self.target_baudrate, 20):
                self.log("Set baudrate failed")
                #self.pbar.close()
                return
            self.log("Set baudrate successful")

        if self.unprotect:
            # Get Mid
            mid = self.bootItf.GetFlashMID()
            # print("\n\n mid: {:x}\n\n".format(mid))
            if self._Do_Boot_ProtectFlash(mid, True) != 1:
                self.log("Unprotect Failed")
                return
            # unprotect flash first

        # Step: Read data
        i = 0
        ss = startAddr & 0xfffff000     # 4K aligned address (translated)
        self.log("len: {:x}".format(length))
        self.log("startAddr: {:x}".format(ss))
        
        while i < length:
            # self.log("Reading: Sector {:x}".format(ss+i))
            data = self.bootItf.ReadSector(ss+i)
            if data:
                if len(data) == 0x1000:
                    self.log("ReadSector Success: Sector {:x},".format(ss+i) + " Length {:x}".format(len(data)))
                else:
                    self.log("ReadSector Failed: Length not 0x1000 {:x}".format(len(data)))
                    return
                
                fileBuf += data
                if self.pbar:
                    self.pbar.update(1)
            else:
                #self.pbar.close()
                self.log("ReadSector Failed: {:x}".format(ss+i))
                return
            i += 0x1000

        #self.pbar.close()
        self.pbar = None
        
        if self.unprotect:
            self._Do_Boot_ProtectFlash(mid, False)

        success, crc = self.bootItf.ReadCRC(startAddr, ss+i)
        self.log("----- CRC check ------")
        self.log("CRC should be {:x}".format(crc))
        fileCrc = crc32_ver2(0xffffffff, fileBuf)
        self.log("CRC is {:x}".format(fileCrc))

        if fileCrc == crc:
            f = open(filename, "wb")
            f.write(fileBuf)
            f.close()
            self.log("--- CRC check PASSED ---")
            self.log("Wrote {:x} bytes to ".format(i) + filename)
        else:
            f = open(filename, "wb")
            f.write(fileBuf)
            f.close()
            self.log("--- CRC check FAILED. ---")
            self.log("If device is a BK7231N, ignore this error.")
            self.log("Wrote {:x} bytes to ".format(i) + filename)

        return


    def programm(self, filename, startAddr=0x11000):
        self.log("programm....")

        # Step1: read file into system memory
        # TODO: sanity check
        with open(filename, "rb") as f:
            pfile = f.read()
        fileLen = filOLen = len(pfile)
        padding_len = 0x100 - (fileLen & 0xff)
        if padding_len:
            pfile += b'\xff'*padding_len
            fileLen += padding_len
            filOLen += padding_len
            # print("fileLen{}, padding_len {}".format(fileLen, padding_len))
            # print("FILE: ", binascii.b2a_hex(pfile, b' '))
        fileCrc = crc32_ver2(0xffffffff, pfile)
        total_num = filOLen // 0x1000


        self.do_reset_signal()
        # reboot = "reboot"
        # self.bootItf.Start_Cmd(reboot)
        # time.sleep(0.1)
        self.pbar = tqdm(total=total_num, ascii=True, ncols=80, unit_scale=True,
                unit='k', bar_format='{desc}|{bar}|[{rate_fmt:>8}]')
        self.log("Getting Bus... (waiting for connection)")
        timeout = Timeout(10)

        # Step2: Link Check
        count = 0
        while True:
            r = self.bootItf.LinkCheck()
            if r:
                break
            if timeout.expired():
                self.log('Cannot get bus. (cannot connect)')
                self.pbar.close()
                return
            count += 1
            if count > 500:
                self.bootItf.Start_Cmd(b"reboot\r\n")
                count = 0
            # time.sleep(0.01)

        self.log("Gotten Bus... (connected)")
        time.sleep(0.01)
        self.bootItf.Drain()

        # Step3: set baudrate, delay 100ms
        if self.target_baudrate != 115200:
            if not self.bootItf.SetBR(self.target_baudrate, 20):
                self.log("Set baudrate failed")
                self.pbar.close()
                return
            self.log("Set baudrate successful")

        if self.unprotect:
            # Get Mid
            mid = self.bootItf.GetFlashMID()
            # print("\n\n mid: {:x}\n\n".format(mid))
            if self._Do_Boot_ProtectFlash(mid, True) != 1:
                self.log("Unprotect Failed")
                return
            # unprotect flash first

        # Step4: erase
        # Step4.1: read first 4k if startAddr not aligned with 4K
        eraseAddr = startAddr
        ss = s0 = eraseAddr & 0xfffff000     # 4K aligned address (translated)
        filSPtr = 0

        if eraseAddr & 0xfff:
            self.log("Aligning Flash Address...")

            # Read 4K from flash
            buf = self.bootItf.ReadSector(s0)
            l = 0x1000 - (eraseAddr & 0xfff)
            fl = l if l < fileLen else fileLen
            buf[eraseAddr&0xfff:eraseAddr&0xfff+fl] = pfile[:fl]
            self.bootItf.EraseBlock(0x20, s0)
            if not self.bootItf.WriteSector(s0, buf):
                self.log("WriteSector FAILED")
                self.pbar.close()
                return
            filOLen -= fl
            filSPtr = fl
            s0 += 0x1000
            ss = s0

            if filOLen <= 0:
                # TODO: goto crc check
                return


        # Step4.2: handle the last 4K
        # now ss is the new eraseAddr.
        # file end address (translated)
        filEPtr = fileLen
        s1 = eraseAddr + fileLen

        # If not 4K aligned, read the last sector, fill the data, write it back
        if s1 & 0xfff:
            # print("Handle file end...")
            buf = bytearray(b'\xff'*4096)   # fill with 0xFF
            buf[:s1&0xfff] = pfile[filEPtr-(s1&0xfff):]  # copy s1&0xfff len
            # print(time.time())
            for _ in range(4):
                if self.bootItf.EraseBlock(0x20, s1&0xfffff000):
                    break
                time.sleep(0.05)
            # time.sleep(0.1)

            # for _ in range(10):
            #    tt = self.bootItf.Read()
            #    print(tt)
            #print(time.time())
            if not self.bootItf.WriteSector(s1&0xfffff000, buf):
                self.log("WriteSector FAILED")
                self.pbar.close()
                return
            # print(time.time())

            filEPtr = filEPtr - (s1&0xfff)
            filOLen = filOLen - (s1&0xfff)
            if filOLen <= 0:
                # TODO: goto crc check
                pass

        # print("Handle file end done")

        # Step4.3: Aligned to 64KB, if the erased area is smaller than 64KB (translated)
        len1 = ss + filOLen
        len0 = s0 & 0xffff0000
        if s0 & 0xffff:
            len0 += 0x10000
        if filOLen > len0 - s0:
            while s0 < len0:
                self.bootItf.EraseBlock(0x20, s0)
                s0 += 0x1000

        # print("fileOLen: {}, filSPtr: {}".format(filOLen, filSPtr))
        # Step4.4: Erase 64k, 4k, etc.
        # Erase according to 64KB/4K block (translated)
        len1 = ss + filOLen
        while s0 < len1:
            self.log("Erasing")
            rmn = len1 - s0
            if rmn > 0x10000:                       # 64K erase
                self.bootItf.EraseBlock(0xd8, s0)
                s0 = s0+0x10000
            else:                                   # erase 4K
                self.bootItf.EraseBlock(0x20, s0)
                s0 = s0 + 0x1000


        # Step5: Write data
        i = 0
        while i < filOLen:
            self.log("Writing")
            for _ in range(4):
                if self.bootItf.WriteSector(ss+i, pfile[filSPtr+i:filSPtr+i+4*1024]):
                    self.pbar.update(1)
                    break
            else:
                self.log("WriteSector {:x} FAILED".format(1))
                self.pbar.close()
                return
            i += 0x1000


        # Step6: CRC check
        self.log("Verifing")
        if fileLen & 0xff:
            l2 = (fileLen & ~0xff) + 0x100
        else:
            l2 = fileLen
        ret,crc = self.bootItf.ReadCRC(startAddr, startAddr+l2-1)
        if not ret:
            self.log("Read CRC Failed")
            self.pbar.close()
            return
        if crc != fileCrc:
            self.log("CRC not equal")
            self.pbar.close()
            return

        if self.unprotect:
            self._Do_Boot_ProtectFlash(mid, False)

        self.log("Write Successful")

        for i in range(3):
            time.sleep(0.01)
            self.bootItf.SendReboot()

        self.pbar.close()

    def _Do_Boot_ProtectFlash(self, mid:int, unprotect:bool):
        # 1. find flash info
        flash_info = GetFlashInfo(mid)
        if flash_info is None:
            return -1
        if debug:
            print(flash_info.icNam, flash_info.manName)

        timeout = Timeout(1)

        # 2. write (un)protect word
        cw = flash_info.cwUnp if unprotect else flash_info.cwEnp
        while True:
            sr = 0

            # read sr register
            for i in range(flash_info.szSR):
                f = self.bootItf.ReadFlashSR(flash_info.cwdRd[i])
                if f[0]:
                    sr |= f[2] << (8 * i)
                    if debug: print("sr: {:x}".format(sr))

            if debug:
                print("final sr: {:x}".format(sr))
                print("msk: {:x}".format(flash_info.cwMsk))
                print("cw: {:x}, sb: {}, lb: {}".format(cw, flash_info.sb, flash_info.lb))
                print("bfd: {:x}".format(BFD(cw, flash_info.sb, flash_info.lb)))

            # if (un)protect word is set
            if (sr & flash_info.cwMsk) == BFD(cw, flash_info.sb, flash_info.lb):
                return 1
            if timeout.expired():
                return -2
            # // set (un)protect word
            srt = sr & (flash_info.cwMsk ^ 0xffffffff)
            srt |= BFD(cw, flash_info.sb, flash_info.lb)
            f = self.bootItf.WriteFlashSR(flash_info.szSR, flash_info.cwdWr[0], srt & 0xffff)

            time.sleep(0.01)

        return 1


if __name__ == '__main__':
    downloader = UartDownloader()
