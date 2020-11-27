#!/usr/bin/env python3

import queue, threading, time
import requests, json, random, logging
import numpy as np
import cv2
import enum
from datetime import datetime
import itertools
import math

from time import sleep

# from videocapture import VideoCapture
from ha import HAConnect
from dahua import Dahua
from ipc import *
from gk import *


gt_pad, gb_pad, gs_pad = 30, 20, 10


def timestamp():
    t = datetime.now()
    s = t.strftime('%m%d_%H%M%S%f')
    return s[:-4]


class QueuedFrame:
    def __init__(self, frame, area):
        self._frame = frame
        self._area = area
    
    @property
    def frame(self):
        return self._frame
    
    @property
    def area(self):
        return self._area


class DeepStack:
    def __init__(self, address, mode, handler):
        self._FR_request = "http://"+address+"/v1/vision/face/recognize"
        self._FD_request = "http://"+address+"/v1/vision/face"
        self._OD_request = "http://"+address+"/v1/vision/detection"
        self._mode = mode
        self._handler = handler
        self._fps = 0
        self._queue = queue.Queue()

        self._thread = threading.Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()

    def loop(self):
        begin = time.time()
        i = 0
        
        while (True):
            i += 1
            try:
                qf = self._queue.get(True, 10)
            except:
                qf = None
                pass
            
            if qf:
                _, buf = cv2.imencode(".jpg", qf.frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])

                if self._mode == Mode.FR:
                    response = requests.post(self._FR_request, files={"image":buf.tobytes()}).json()
                    self.FR_parse(response, qf.frame, qf.area)
                    
                elif self._mode == Mode.OD:
                    response = requests.post(self._OD_request, files={"image":buf.tobytes()}).json()
                    self.OD_parse(response, qf.frame, qf.area)

                elif self._mode == Mode.FD:
                    response = requests.post(self._FD_request, files={"image":buf.tobytes()}).json()
                    self.FD_parse(response, qf.frame, qf.area)
                

            if time.time() - begin >= 10:
                self._fps = float(i/10)
                i = 0
                begin = time.time()

    @property
    def fps(self):
        return self._fps

    @property
    def processed(self):
        return 0

    def process_frame(self, frame, area):
        # print (area)
        qf = QueuedFrame(frame, area)
        if not self._queue.empty():
            try:
                self._queue.get_nowait()   
            except queue.Empty:
                pass
        self._queue.put(qf)

    def FR_parse(self, response, frame, area):

        try:
            if not bool(response["success"]): 
                return False

            if not len(response["predictions"]) > 0:
                return False


            h, w, c = frame.shape
            
            for face in response["predictions"]:
                y_max = int(face["y_max"])
                y_min = int(face["y_min"])
                x_max = int(face["x_max"])
                x_min = int(face["x_min"])
                confidence = float(face["confidence"])
                user = face["userid"]
                

                if float(y_min/h) > 0.7:
                    return True


                t_pad, b_pad, s_pad = gt_pad, gb_pad, gs_pad
                
                if t_pad > y_min: t_pad = y_min

                if (y_max - y_min < 90) or (x_max - x_min < 90):
                    continue
                
                self._handler(Recognition(Mode.FR, frame[y_min - t_pad:y_max + b_pad, x_min - s_pad:x_max + s_pad], user, confidence, area))
            
            return True

        except Exception as e:
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())
            return False

    def FD_parse(self, response, frame, area):

        try:
            if not bool(response["success"]): 
                return

            if not len(response["predictions"]) > 0:
                return
            
            h, w, c = frame.shape
            
            for face in response["predictions"]:
                y_max = int(face["y_max"])
                y_min = int(face["y_min"])
                x_max = int(face["x_max"])
                x_min = int(face["x_min"])
                confidence = float(face["confidence"])
                

                if float(y_min/h) > 0.7:
                    return True

                if confidence < FACE_THRESHOLD or confidence > 1.0: 
                    continue

                t_pad, b_pad, s_pad = gt_pad, gb_pad, gs_pad

                if t_pad > y_min: t_pad = y_min
              
                self._handler(Recognition(Mode.FD, frame[y_min - t_pad:y_max + b_pad, x_min - s_pad:x_max + s_pad], "face", confidence, area))

        except Exception as e:
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())
            return


    def OD_parse(self, response, frame, area):

        try:
            if not bool(response["success"]): 
                return
            if not len(response["predictions"]) > 0:
                return
            
            h, w, c = frame.shape

            for prediction in response["predictions"]:
                    label = prediction["label"]
                    confidence  = float(prediction["confidence"])
                    y_max = int(prediction["y_max"])
                    y_min = int(prediction["y_min"])
                    x_max = int(prediction["x_max"])
                    x_min = int(prediction["x_min"])

                    if label == "person":

                        if (float(y_max/h) < 0.2):
                            continue

                        if area == Areas.Chodnik:
                            if float(y_min/h) > 0.87:
                                continue
                        elif area == Areas.Tiguan:
                            if float(y_min/h) > 0.50:
                                continue
                        elif area == Areas.Touareg:
                            if (float(y_min/h) > 0.60):
                                continue

                        self._handler(Recognition(Mode.OD, frame[y_min:y_max, x_min:x_max], label, confidence, area))

                    elif label in VEHICLES:

                        if (float(y_max/h) < 0.4) or (float(x_min/w) > 0.52):
                            continue

                        self._handler(Recognition(Mode.OD, frame[y_min:y_max, x_min:x_max], label, confidence, area))


        except Exception as e:
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())            
            # sleep(1)
            return





