#!/usr/bin/env python3
import requests, json, random
import queue, threading, time
from datetime import datetime
from time import sleep
import configparser


focus_in = "0.923810"
focus_out = "0.134319"
zoom_in = "1"
zoom_out = "0"

class Dahua:
    def __init__(self):
        self._username = "admin"
        self._password = "admin"
        self._last_checked = 0
        self._last_autofocus = 0
        self._last_zoom = time.time()
        self._last_unlocked = 0
        self._autofocus_ctr = 0
        self._lock = 0
        self._zoom = self.get_zoom()
        self._thread = threading.Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()        
    
    def loop(self):
        while True:
            timestamp = time.time()
            if (timestamp - self._last_checked > 10):
                self._zoom = self.get_zoom()
            if (self._zoom and (timestamp - self._last_zoom > 300)):
                self.zoom_out()
            if (self._autofocus_ctr >= 30):
                print(datetime.now().strftime("%H:%M:%S")+": IPC autofocus error. Rebooting.")
                print(datetime.now().strftime("%H:%M:%S")+": IPC autofocus error. Rebooting.", file=open("dahua.log", "a"))
                self.lock(300)
                self.reboot()
            
            if self._lock:
                sleep(self._lock)
                self._lock = 0

            sleep(1)

    def lock(self, t):
        self._lock = t

    def reboot(self):
        try:
            self.lock(120)
            requests.get("http://192.168.1.100/cgi-bin/magicBox.cgi?action=reboot", auth=requests.auth.HTTPDigestAuth(self._username,self._password)) 
            sleep(60)
        except Exception as e: 
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())
        
        self._autofocus_ctr = 0


    @property
    def zoom(self):
        return self._zoom

    def zoom_in(self):
        
        if not self._zoom:
            self._zoom = True
            print(datetime.now().strftime("%H:%M:%S")+": zoom in.                                ")
            self.request(focus_in, zoom_in)
            
        self._last_zoom = time.time()
        self._last_checked = time.time()+10
        # self._last_auto_focus = time.time()


        
    
    def zoom_out(self):
        if self._zoom:
            print(datetime.now().strftime("%H:%M:%S")+": zoom out.                               ")            
            self.request(focus_out, zoom_out)
            self._zoom = False
            self._last_checked = time.time()+5
    
    def get_zoom(self):

        if time.time() - self._last_checked < 10:
            return self.zoom
        else:
            try:
                z = False
                zoom = False
                r = "[top]\n" +requests.get("http://192.168.1.100/cgi-bin/devVideoInput.cgi?action=getFocusStatus",auth=requests.auth.HTTPDigestAuth(self._username,self._password)).text
                # print(datetime.now().strftime("%H:%M:%S")+": Get_Zoom().")
                cp = configparser.RawConfigParser()
                cp.read_string(r)

                zoom = cp.getfloat('top','status.Zoom') 
                focus = cp.getfloat('top','status.Focus')

                if not self.in_focus(zoom, focus):
                    self.autofocus()
    
                z = (zoom > 0.5)
                self._last_checked = time.time()
            
            except Exception as e:
                print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())
                self.lock(300)
                # self.reboot()
                # sleep(120)
                print(datetime.now().strftime("%H:%M:%S")+": get_zoom error. Sleeping 5 minutes. ")
                print(datetime.now().strftime("%H:%M:%S")+": get_zoom error. Sleeping 5 minutes.", file=open("dahua.log", "a"))

                    
            return z

    def request(self, focus, zoom):
        try:
            requests.get("http://192.168.1.100/cgi-bin/devVideoInput.cgi?action=adjustFocus&focus="+focus+"&zoom="+zoom, auth=requests.auth.HTTPDigestAuth(self._username,self._password)) 
        except Exception as e: 
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())
            

    def autofocus(self):
        try:
            requests.get("http://192.168.1.100/cgi-bin/devVideoInput.cgi?action=autoFocus", auth=requests.auth.HTTPDigestAuth(self._username,self._password))
            if time.time() - self._last_autofocus < 20:
                self._autofocus_ctr += 1
            else:
                self._autofocus_ctr = 0

            self._last_autofocus = time.time()
            print(datetime.now().strftime("%H:%M:%S")+": autofocus.")
        except Exception as e: 
            print(datetime.now().strftime("%H:%M:%S")+" "+e.__str__())

    def in_focus(self, zoom, focus):
        if zoom == 0:
            return bool(focus < 0.2)
        elif zoom == 1:
            return bool(focus > 0.9)
        else:
            return False            

    def unlock(self):
        timestamp = time.time()
        if (timestamp - self._last_unlocked > 4):
            self._last_unlocked = timestamp
            requests.get("http://192.168.1.101/cgi-bin/accessControl.cgi?action=openDoor&channel=1&UserID=101&Type=Remote", auth=requests.auth.HTTPDigestAuth(self._username,self._password))  
