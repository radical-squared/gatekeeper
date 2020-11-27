#!/usr/bin/env python3

# import daemon

from ds import *
from ha import *
from dahua import *
from ipc import *
from gk import *
from time import sleep


RTSP_STREAM = "rtsp://admin:admimn@192.168.1.100:554/cam/realmonitor?channel=1&subtype=0"


def main():

    cameraControl = Dahua()
    hac = HAConnect(cameraControl)
    gk = GateKeeper(cameraControl, hac)

    ds_fr = DeepStack("192.168.1.200:5000", Mode.FR, gk.process)
    ds_od = DeepStack("192.168.1.201:5001", Mode.OD, gk.process)

    front = IPC(RTSP_STREAM, cameraControl, ds_fr, ds_od, hac)
    
    while True:
        print(datetime.now().strftime("%H:%M:%S")+": Front: %.1f" % front.fps +" OD: %.1f" % ds_od.fps +" FR: %.1f" %ds_fr.fps,end="\r") 
        d = {}
        d["ipc"] = front.fps
        d["od"] = ds_od.fps
        d["fr"] = ds_fr.fps
        hac.send("ai/stats",json.dumps(d))
        sleep(10)
 

if __name__ == "__main__":
    main()


# with daemon.DaemonContext():
#     main()



