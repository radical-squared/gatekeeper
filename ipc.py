#!/usr/bin/env python3

import numpy as np
import cv2
import queue, threading, time
from datetime import datetime
from time import sleep
import itertools, enum


class Areas(enum.Enum):
    Pavement = 1
    Car_A = 2
    Car_B = 3

    def __str__(self):
        return self.name


class IPC:

    def __init__(self, name, cam, fr, od, hac):
        self._cap = cv2.VideoCapture(name)
        self._name = name
        self._fr = fr
        self._od = od
        self._hac = hac
        self._zoom = False
        self._camera = cam
        self._fps = 0
        self._thread = threading.Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()

    def loop(self):
        i = 0
        begin = time.time()
        for area in itertools.cycle(Areas):
            i += 1
            ret, new_frame = self._cap.read()
            if not ret:
                print(datetime.now().strftime("%H:%M:%S")+": IPC read() error. Waiting 5 minutes.", file=open("dahua.log", "a"))
                print(datetime.now().strftime("%H:%M:%S")+": IPC read() error. Waiting 5 minutes.")
                self._camera.lock(60)
                # sleep(5)
                self._cap.release()                
                sleep(60)
                self._cap = cv2.VideoCapture(self._name)
                sleep(5)
                continue

            if self._camera.zoom:

                crop = new_frame[0:600, 600:1600]
                self._fr.process_frame(crop, Areas.Pavement)
                ha_frame = new_frame[0:700, 400:1400]

            else:
                
                if area == Areas.Pavement:
                    crop = new_frame[580: 900, 1208: 1528]
                    
                elif area == Areas.Car_A:
                    crop = new_frame[585: 1001, 1492: 1908]

                else:
                    crop = new_frame[572: 1100, 1834: 2362]
                    
                self._od.process_frame(crop, area)  

                ha_frame = new_frame[683: 931, 1143: 1517]  #[0:300, 2000:3000]  #
            
            self._hac.set_frame(ha_frame.copy())

            if time.time() - begin >= 10:
                self._fps = int(i/10)
                i = 0
                begin = time.time()

    @property
    def fps(self):
        return self._fps


class SimpleIPC:

    def __init__(self, name, fd):
        self._cap = cv2.VideoCapture(name)
        self._name = name
        self._fd = fd
        self._fps = 0
        self._thread = threading.Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()

    def loop(self):
        i = 0
        begin = time.time()
        while True:
            i += 1
            ret, new_frame = self._cap.read()
            if not ret:
                print(datetime.now().strftime("%H:%M:%S")+": Furtka cv2.read() error")
                self.cap.release()
                sleep(60)
                self.cap = cv2.VideoCapture(self._name)
                sleep(60)
                continue

            self._fd.process_frame(new_frame, None)

            if time.time() - begin >= 60:
                self._fps = int(i/60)
                i = 0
                begin = time.time()

    @property
    def fps(self):
        return self._fps