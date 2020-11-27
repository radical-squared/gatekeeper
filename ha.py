#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import queue, threading, time
# import logging
from datetime import datetime
import numpy as np
import cv2

from time import sleep

from dahua import Dahua



class HAConnect:
    def __init__(self, cam):
        self._camera = cam
        self._last_stream = 0
        self._last_status = 0
        self._last_zoom_status = 0
        self._connection = False

        self._client = mqtt.Client()
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_message = self.on_message
        self._client.username_pw_set("mqtt", "my_password")
        self._client.connect("localhost",1883,60)
        self._client.loop_start()
        self._frame = None

        t = threading.Thread(target=self.update)
        t.daemon = True
        t.start()

    def on_connect(self, client, userdata, flags, rc):
        # print ("on_connect")
        self._connection = True
        self._client.subscribe("cv/front/set")

    def on_disconnect(self, client, userdata, rc):
        print ("on_disconnect")
        self._connection = False

    def on_message(self, client, userdata, msg):
        payload = int(msg.payload.decode())
        if payload == 1:
            self._camera.zoom_in()
        elif payload == 0:
            self._camera.zoom_out()
        else:
            print ("other")


    
    def update(self):

        while True:
            try:
                if self._frame is None: 
                    sleep (2)
                    continue
                timestamp = datetime.timestamp(datetime.now())
                

                if not self._connection:
                    print("Client disconnected. Reconnecting...")
                    self._client.reconnect()
                    sleep(2)
                
                if (timestamp - self._last_stream > 1):
                    ret, mid = self._client.publish("cv/front/stream", self.export_frame, 0, False)
                    if ret == 0:
                        self._client.publish("cv/front/status", datetime.now().strftime("%H:%M:%S"), 0, False)  #
                        self._last_status = timestamp
                    self._last_stream = timestamp
                        
                    
            

                if (timestamp - self._last_zoom_status > 5):
                    if self._camera.zoom: p = 1 
                    else: p = 0
                    
                    self._client.publish("cv/front/zoom", p, 1)
                    self._last_zoom_status = timestamp
            
                sleep(1)
            except Exception as e:
                print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())  
                sleep(5)
                continue

    def set_frame(self, frame):      
        w, h, c = frame.shape
        if w == 248:
            s_pad = 2
            fontScale = 0.4
        else:
            s_pad = 10
            fontScale = 1   
        font = cv2.FONT_HERSHEY_SIMPLEX        
        fontColor = (255,255,255)
        lineType = 1
        txt = datetime.now().strftime("%H:%M:%S")
        text_width, text_height = cv2.getTextSize(txt, font, fontScale, lineType)[0]
        bottomLeftCornerOfText = (0,text_height+s_pad)
        
        cv2.putText(frame,txt,bottomLeftCornerOfText,font,fontScale,fontColor,lineType)

        self._frame = frame

    @property
    def export_frame(self):
        f = None
        try:
            s, r = cv2.imencode(".jpg", self._frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            z = r.tobytes()
        except Exception as e:
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())  
            z = None
        return z

    def send(self, topic, msg):
        if self._connection:
            self._client.publish(topic, msg, 1)  #
