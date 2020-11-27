#!/usr/bin/env python3

from ds import *

PERSON_THRESHOLD = 0.8
VEHICLE_THRESHOLD = 0.5
AUTHORIZATION_THRESHOLD = 0.80
FACE_THRESHOLD = 0.9


AUTHORIZED = ['Luke', 'Dorothy', 'Caroline']
VEHICLES =['car', 'truck']

FILE_NAME = "detection.log"


# Using enum class create enumerations
class Mode(enum.Enum):
    OD = 1
    FD = 2
    FR = 3
    NO = 4


class Presence:
    def __init__(self, name):
        self._last_seen = time.time() 
        self._arrived = time.time()-100
        self._name = name
    
    def seen(self):
        if (time.time() - self._last_seen > 600.0):
            self._arrived = time.time()
            print("| "+datetime.now().strftime("%H:%M:%S") +"| "+self._name+" arrived. |", file=open(FILE_NAME,"a"))
            print(datetime.now().strftime("%H:%M:%S") +": "+self._name+" arrived. Zooming in.")
        self._last_seen = time.time()
        
    @property
    def present(self):
        return (time.time() - self._last_seen < 300.0)
    
    @property
    def arriving(self):
        return (time.time() - self._arrived < 60.0)


class GateKeeper:
    def __init__(self, lock, hac):
        self._lock = lock
        self._hac = hac
        self._queue = queue.Queue()
        self._car_a = Presence("Car A")
        self._car_b = Presence("Car B")
        
        self._last_status = 0

        self._thread = threading.Thread(target=self.loop)
        self._thread.daemon = True
        self._thread.start()
    
    def log(self, msg, write_to_file=True):
        print(datetime.now().strftime("%H:%M:%S") +": "+msg.id+" ("+str(int(msg.confidence*100)) +"%) recognized at "+str(msg.area)+".")
        if write_to_file:
            print("| "+datetime.now().strftime("%H:%M:%S") +"| "+msg.id+" ("+str(int(msg.confidence*100)) +"%) @ "+str(msg.area)+". |", file=open(FILE_NAME, "a"))
    
    def loop(self):
        while True:

            try:
                msg = self._queue.get(True, 10)
            except:
                msg = Recognition(Mode.NO, None, None, 0, Areas.Pavement)
                pass
            # print (msg.id, msg.confidence, msg.area)
            if msg.mode == Mode.FR:
                if msg.confidence > AUTHORIZATION_THRESHOLD:
                    if msg.id in AUTHORIZED:
                        self._lock.unlock()
                        data = {}
                        data['user'] = msg.id
                        data['confidence'] = msg.confidence
                        json_data = json.dumps(data)
                        hac.send("cv/front/unlocked", json_data)
                        self.log(msg)
                else:
                    self.log(msg, False)
                
                self._lock.zoom_in()
                if msg.frame.size > 0:
                    cv2.imwrite(msg.id+'_'+timestamp()+'_'+str(int(msg.confidence*100))+'.jpg', msg.frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                
            elif msg.mode == Mode.OD:
                if msg.id == "person" and msg.confidence > PERSON_THRESHOLD:
                    self.log(msg)
                    # if msg.frame.size > 0:
                    #     cv2.imwrite(msg.id+'_'+timestamp()+'_'+str(int(msg.confidence*100))+'.jpg', msg.frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                    self._lock.zoom_in()

                elif msg.id in VEHICLES and msg.confidence > VEHICLE_THRESHOLD:
                    if msg.area == Areas.Car_A:
                        self._car_a.seen()
                    elif msg.area == Areas.Car_B:
                        self._car_b.seen()
                    
                    if (self._car_a.arriving or self._car_a.arriving):
                        self._lock.zoom_in()

            elif msg.mode == Mode.FD:
                
                if msg.confidence > FACE_THRESHOLD and msg.confidence <= 1.0:
                
                    self.log(msg)

                    if msg.frame.size > 0:
                        cv2.imwrite(msg.id+'_'+timestamp()+'_'+str(int(msg.confidence*100))+'.jpg', msg.frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                
                    self._lock.zoom_in()
            
            if time.time() - self._last_status > 10:
                self._hac.send("cv/presence/car_a", self._car_a.present)
                self._hac.send("cv/presence/car_b", self._car_b.present)
                self._last_status = time.time()

                # print(msg.id, msg.confidence, msg.area)

    def process(self, msg):
        self._queue.put(msg)


class Recognition:
    def __init__(self, mode, frame, id, confidence, area):
        self._mode = mode
        self._id = id
        self._confidence = confidence
        self._area = area
        self._frame = frame

    @property
    def mode(self):
        return self._mode

    @property
    def frame(self):
        return self._frame

    @property
    def id(self):
        return self._id

    @property
    def confidence(self):
        return self._confidence

    @property
    def area(self):
        return self._area
