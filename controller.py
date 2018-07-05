import mosquitto
import time, threading, requests, json
import RPi.GPIO as GPIO
import datetime as dt
#from calTimer import setTime #hitung timer

END_POINT = "http://139.99.47.91:8000/api/"

broker = "test.mosquitto.org"
topic = "/TA-ferdi/status/smart-lamp"
job1 = []
job2 = []
njob1 = 0
njob2 = 0
timer_on = 0
timer_off = 0
lamp_pin = 18
time1 = 0
time2 = 0
timer = 0

class Job(threading.Thread):
    duration = 0
    status = ''
 
    def __init__(self, dura, status):
        threading.Thread.__init__(self)
        #cara ribet logikanya
        self.duration = setDura(dura)
        #cara mudah logikanya
        #
        #self.duration = dura
        self.shutdown_flag = threading.Event()
        self.status = status

    def run(self):
        print('Thread #%s started' % self.ident)
        print('durasi job '+str(self.duration)+' status '+self.status)
    
        # dibawah cara ribet logikanya
        i=0
        while not self.shutdown_flag.is_set():
            if (i != self.duration):
                i += 1
                time.sleep(1)
                print(i)
            else:
                self.shutdown_flag.set()
        # cara mudah logikanya
        #
        # while not self.shutdown_flag.is_set():
        #     t = dt.datetime.now().time()
        #     seconds = (t.hour * 60 + t.minute) * 60 + t.second
        #     if (seconds != self.duration):
        #         i += 1
        #         time.sleep(1)
        #         print(seconds)
        #     else:
        #         self.shutdown_flag.set()       
        setLamp(self.status)
        print('Thread #%s stopped' % self.ident)


def setDura(durasi):

    t = dt.datetime.now().time()
    seconds = (t.hour * 60 + t.minute) * 60 + t.second
    if ((seconds <= durasi) & (durasi > 64800) ):
        #bila durasi menunjukkan dibawah pukul 00:00 atau puncak durasi 23:59:59
        alarm = durasi - seconds
    elif ((durasi <= 64800) & (durasi >= 21600)):
        #bila durasi menunjukkan kurang dari pukul 18:00 dan diatas pukul 06:00
        #untuk mengantisipasi auto on/off pukul 06:00 dan 18:00 
        #lebih tepatnya untuk job2, job1 kondisi ini tidak bakal terpakai harusnya hhe
        #selain itu job2 berfungsi untuk melakukan alaram nyala lampu
        alarm = 21590
    else:
        #kondisi durasi dari pukul 00:00 - 05:59:59
        # kenapa alarm = (86400 - seconds) + durasi
        # karena job2 dijalankan bersamaan dengan job1
        alarm = (86400 - seconds) + durasi
    
    return alarm

def stop_job(njob):
    job1[njob].shutdown_flag.set()
    job2[njob].shutdown_flag.set()
    job1[njob].join()
    job2[njob].join()

def on_connect(mosq, obj, rc):
    mosq.subscribe("$SYS/#", 0)
    print("rc: "+str(rc))

def on_message(mosq, obj, msg):
    #print(msg.payload)
    
    global job1, job2, njob1, njob2
    print("get message: "+ msg.payload)
    
    setTimer(parsing_msg(msg.payload))
    if (timer == False):
        print(job1[njob1].is_alive())
        #set lamp bila payload hanya berisi string "on" atau "off"
        if ((job1[njob1].is_alive() == True) | (job2[njob2].is_alive() == True)):
        
        ##if (job1[njob1].is_alive() == True):
            stop_job(njob1)
        setLamp(msg.payload)
        print('manual')
    elif (timer == True):
        print(job1[njob1].is_alive())
        #set alarm wit threa
        if ((job1[njob1].is_alive() == True) | (job2[njob2].is_alive() == True)):
            stop_job(njob1)            
        njob1 += 1
        njob2 += 1
        job1.append(Job(timer_off,'off'))
        job2.append(Job(timer_on,'on'))
        
        job1[njob1].start()
        job2[njob2].start()
        print("hello")

def on_publish(mosq, obj, mid):
    print("mid: "+str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

def last_status():
    url = END_POINT+'status'
    response = requests.get(url=url)

    if response.ok:
        print(response.content)
        data = json.loads(response.content)
        if data["data"][0]["status"] == 'on':
            return True
        elif data["data"][0]["status"] == None:
            return False
        else:
            return False
    else:
        return False

def parsing_msg(msg):
    global time1,time2

    #ini format lama msg harus "time1:2018-02-21 10:31:30/time2:2018-02-21 10:31:00"
    # format baru kalau ada timer maka formatnya waktustart&waktuend
    # contoh msg nya "8791&3923"
    if ((msg == "on") | (msg == "off")):
        
        print(msg)
        #msg = "auto"
    else:
        wkt = msg.split('&')

        if len(wkt) == 2:
            time1 = int(wkt[0])
            time2 = int(wkt[1])
            msg ="auto"

    return msg

def setTimer(msg):
    global timer, timer_off, timer_on

    print (len(msg))
    if ((len(msg) == 2) | (len(msg) == 3)):
        #tanpa timer
        timer = False
    else:
        #dengan timer
        timer_off = time1
        timer_on = time2
        #timer_off = setTime(time1[0:10],time1[11:20])
        #timer_on = setTime(time2[0:10],time2[11:20])
        timer = True

def setLamp(status):
    global lamp_pin
    if (status == "on"):
        GPIO.cleanup()
        GPIO.setmode(GPIO.BCM)
        #GPIO.setwarnings(False)
        GPIO.setup(lamp_pin, GPIO.OUT)
        GPIO.output(lamp_pin, GPIO.LOW)
    elif (status == "off"):
        GPIO.cleanup()
        #GPIO.setmode(GPIO.BCM)
        #GPIO.setwarnings(False)
        #GPIO.setup(lamp_pin, GPIO.OUT)
        #GPIO.output(lamp_pin, GPIO.HIGH)
    print('status '+status)

def main():
    
    GPIO.setmode(GPIO.BCM)
    #GPIO.setwarnings(False)
    GPIO.setup(lamp_pin, GPIO.OUT)
    ltst = last_status()
    if ltst:
        GPIO.output(lamp_pin, GPIO.LOW)
        #setLamp('on')
        #status_lampu = 'on'
        print("lampu hidup")
    else:
        GPIO.output(lamp_pin, GPIO.HIGH)
        #setLamp('off')
        #status_lampu = 'off'
        print("lampu mati")

    mqtt = mosquitto.Mosquitto()
    mqtt.on_message = on_message
    mqtt.on_subscribe = on_subscribe
    
    print("Menjalankan server...")

    print("Menghubungkan ke broker")
    mqtt.connect(broker, 1883, 60)
    mqtt.subscribe(topic, 0)

    mqtt.loop_forever()

if __name__ == "__main__":
    job1.append(Job(timer_off,''))
    print(job1[njob1].is_alive())
    job2.append(Job(timer_on,''))
    main()