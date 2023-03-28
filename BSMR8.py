# Dit programma verwerkt data die uit een SmartDigitalMeter komt geschikt voor Blegië
# De data komt binnen op de UART0 = RX pin10 = GPIO15 
# OPGELET: zet eerst serial interface aan. 'sudo raspi-config', nr3 'interface options' en bij 'Serial port' zet UIT 'login shell' en AAN 'port hardware'
# OPTIE:
# autostart: 'sudo nano /etc/rc.local' deze lijn aanbrengen 'sudo python /home/pi/Python3/DSMR/BSMRx.py'
# check of het programma loopt:     "ps aux | grep /home/pi/Python3/DSMR" of "kort ps aux | grep /DSMR"
# stop het lopende programma:       "sudo kill xxx"
# Stoppen van de recorder via GIO   https://www.deviceplus.com/raspberry-pi/using-raspberry-pi-gpio-pins-with-the-rpi-gpio-python-library/
# Werking:
# Eerst wordt de telegram gelezen en wordt getest op eventuele fouten. Enkel getallen toegelaten zoniet fout
# Daarna wordt de data verwerkt als fout = 0 en telegram einde = 1 
# BSMR3 Eerste verwerking: vermogen gemiddelde berekenen
# BSMR4 Tweede bewerking is kwartier bekijken en verloop voorspellen + save file met data voor de plot 'BSMRplotData'
# BSMR4d ander programma voorspellingen
# BSMR5 controle met tellerstanden (edt1-ert1) + (edt2-ert2) + onthouden pieken 'kwpk' en 'dagpk'
# BSMR6 MQTT zendt iedere 10 seconden update voorspelling. Dit gebeurt met een 'json' bewerking
# BSMR7 MQTT uitgeschakeld
# BSMR8 MQTT in treading. Nu is eer tijd genoeg omalles optijd te laten werken.

import serial                    # raspi-config serial ON. Zie hierboven lijn 4
import json
import time
import RPi.GPIO as GPIO
import numpy as np
from threading import Thread     # https://www.geeksforgeeks.org/start-and-stop-a-thread-in-python/

# import array as arr            # https://www.geeksforgeeks.org/python-arrays/

import paho.mqtt.client as mqtt	 # sudo pip install paho-mqtt
mqtt_topic = "esp32/json"        # https://randomnerdtutorials.com/how-to-install-mosquitto-broker-on-raspberry-pi/
mqtt_server_ip = "192.168.0.248"  # server = rpifravan64 = lokale Server
# mqtt_server_ip = "192.168.1.105" # server = rpifra64cv = Server CV
client = mqtt.Client()           # check of het hier op de juiste plaats staat  !!!!!!!!!!!!!!!!!!!!

GPIO.setmode(GPIO.BCM)          # BCM = GPIO nummers / BOARD = PIN nummers
stopRPI = 17                    # GPIO 17            / PIN 11    
GPIO.setup(stopRPI, GPIO.IN, pull_up_down=GPIO.PUD_UP)    # GPIO input met pull-up
SERIAL_PORT = "/dev/serial0"    # GPIO15 = RX (pin10) / GPIO14 = TX (pin8)    
path = "/home/pi/Python3/DSMR/forcast.csv" 
running = True                  # mogelijkheid om programma te stoppen met CTRL + C
einde = 0                       # vlag 0 = telegram loopt binnen 1 = binnen
vlag1x = 0                      # vlag 0 = programma niet uitvoeren vlag = 1 wel uitvoeren
loper30 = 0                     # gebruikt bij berekenen power gemiddeld
loper1x = 0                     # loper die 1x doorlopen wordt zolang er nog geen 30 berichten binnen zijn 
pgtot = 0                       # power totaal van de laatse 30 seconden
pg = 0                          # gemiddeld vermogen v/d laaste 30 seconden
pg30arr = np.zeros(31, dtype=int)           # https://numpy.org/doc/stable/reference/generated/numpy.zeros.html
                                            # https://www.geeksforgeeks.org/how-to-create-an-array-of-zeros-in-python/   # https://www.geeksforgeeks.org/python-arrays/
pg900tot = 0                    # opgeteld vermogen tot 900s
loper900 = 0                    # tijd binnen een kwartier in sec 
pg90arr = np.zeros(91, dtype=int) # Om de 10 seconden wordt een pg900tot opgeslagen
pv90arr = np.zeros(91, dtype=int) # om de 10 seconden wordt een umulatie opgeslagen
losts = 0                       # verloren seconden of verloren telegramen 
kw = 0                          # '00 - 15 - 30 - 45' = '0000 - 900 - 1800 - 2700' = 'kw1 - kw2 - kw3 - kw4' kw0 is synchroniseren
fout = 0                        # fout 0 = geen  1= fout gevonden
fouttel = 0                     # fouten teller
limiet = 1000                   # limiet 1000W = 4KWh = rode lijn op curve
alarmh = 1100                   # curve alarm hoog in het begin
alarml = 900                    # curve alarm laag op het einde
alarm = 0                       # loopt van alarmh tot alarml ifv loper900, alarm gebruikt als er niets automatisch kan uitgeschakeld worden
kwpk = 0                        # kwartierpiek = energy teller wordt genoteerd begin kwartier (edt1-ert1) + (edt2-ert2) 
kwpkold = 0                     # kwartierpiek vorig kwartier energy teller
dagpk = 0                       # piek berekend uit (kwpk - kwpkold) hoogste wordt onthouden

startkw = 0                     # start kwartier op 00 - 15 - 30 - 45
   
# global dt, td, ws 
# global edt1, edt2, ert1, ert2, pd, pr, gd
# global vl1, vl2, vl3, cl1, cl, cl3
dt = 0; td = 0; ws = ''; tdm = 0; tds = 0; tdss = 0; tdsoud = 0
edt1 = 0; edt2 = 0; ert1 = 0; ert2 = 0; pd = 0; pr = 0; gd = 0
vl1 = 211; vl2 = 221; vl3 = 231; cl1 = 1; cl2 = 2; cl3 = 3

#=======================================================================
# Neem telegram binnen 

def getData(dsmr):                      # 
    global dt, td, ws, tdm, tds, tdss 
    global edt1, edt2, ert1, ert2, pd, pr, gd
    global vl1, vl2, vl3, cl1, cl, cl3 
    global einde, fout, fouttel, vlag1x 
      
    data = dsmr.readline()
    # print (data)                      # We zien de data voorbij komen
    
    message = data[0:5]  # /FLU5        # de eerste karakters tellen niet mee (b')
    # print (message)                   # We zien de eerste 6 karakters
    if (message == b'/FLU5'):           # b' start telegram 
        # print ('start telegram') 
        # print (data)                  # print de volledige regel 
        einde = 0                       # vlag 0 = telegram loopt binnen, 1 = telegram is binnen
                            
        
    message = data[0:10]
    
    if message == b'0-0:96.1.4':        # P1 versie
        # print (data)
        pass
        
    if message == b'0-0:96.1.1':        # equipment ID
        # print (data)    
        pass
        
    message = data[0:9]                 # filter 'X-X:X.X.X'
    
    if (message == b'0-0:1.0.0'):       # timestamp
        try:
            dt = int(data[10:16])       # datum YYMMDD
            td = int(data[16:22])       # tijd HHMMSS
            tdm= int(data[18:20])       # tijd minuten selectie in minuten 0-60
            tds= int(data[20:22])       # tijd seconden max: 60s
            tdss = tdm*60 + int (tds)   # tijd in seconden voor 1 uur max: 3600s
            print ('tijdseconden: ', tdss)
            #print ('tijdseconden: ', tdm)
            if (data[22] == 87):            # winter zomer 
                ws = 'W'
            else:
                ws = 'S'                    #
            # print ('datum: ',dt,' datum: ',td, ws)
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:1.8.1'):       # energy deliverd tariff1
        try:
            edt1 = float(data[10:20]) 
            edt1 = int(edt1*1000)
            # print ('energy delivered tariff1: ',edt1,'Wh')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
    
    if (message == b'1-0:1.8.2'):       # energy delivered tariff2
        try:
            edt2 = float(data[10:20]) 
            edt2 = int(edt2*1000)
            # print ('energy delivered tariff2: ',edt2,'Wh')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
        
    if (message == b'1-0:2.8.1'):       # energy returned tariff1
        try:
            ert1 = float(data[10:20]) 
            ert1 = int(ert1*1000)
            # print ('energy returned tariff1: ',ert1,'Wh')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:2.8.2'):       # energy returned tariff2
        try:
            ert2 = float(data[10:20]) 
            ert2 = int(ert2*1000)
            # print ('energy returned tariff2: ',ert2,'Wh')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
    
    if (message == b'1-0:1.7.0'):       # power delivered
        try:
            pd = float(data[10:16])
            pd = int(pd*1000)
            # print ('power delivered: ',pd,'W')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
                 
    if (message == b'1-0:2.7.0'):       # power returned
        try:
            pr = float(data[10:16])
            pr = int(pr*1000)
            # print ('power returned: ',pr,'W')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass

    message = data[0:10]  # 1-0:31.7.0    # selecteer
    
    if (message == b'1-0:32.7.0'):       # voltage L1
        try:
            vl1 = float(data[11:16])
            # print ('voltage L1: ',vl1,'V')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:52.7.0'):       # voltage L2
        try:
            vl2 = float(data[11:16])
            # print ('voltage L2: ',vl2,'V')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
        
    if (message == b'1-0:72.7.0'):       # voltage L3
        try:
            vl3 = float(data[11:16])
            # print ('voltage L3: ',vl3,'V')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:31.7.0'):       # current L1
        try:
            cl1 = float(data[11:17])
            # print ('current L1: ',cl1,'A')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:51.7.0'):       # current L2
        try:
            cl2 = float(data[11:17])
            # print ('current L1: ',cl2,'A')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'1-0:71.7.0'):       # current L3
        try:
            cl3 = float(data[11:17])
            # print ('current L1: ',cl3,'A')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    if (message == b'0-1:24.2.3'):       # gas delivered
        try:
            gd = float(data[26:35])
            # print ('gas delivered: ',gd,'m³')
        except:
            fout = 1
            fouttel = fouttel + 1
            pass
            
    message = data[0:1]                 # selecteer '!'
    if  (message == b'!'):
        einde = 1                       # '!' op de juiste plaats = telegram einde
        vlag1x =1                       # deze telegram 1x verwerken
        # print ('einde: !')   
        # print ('------------------------------------------------------')

# ----------------------------------------------------------------------

def printData():

    print ('datum: ',dt,' datum: ',td, ws) 
    print ('energy delivered tariff1: ',edt1,'Wh')
    print ('energy delivered tariff2: ',edt2,'Wh')
    print ('energy returned tariff1: ',ert1,'Wh')
    print ('energy returned tariff2: ',ert2,'Wh')
    print ('power delivered: ',pd,'W')
    print ('power returned: ',pr,'W')
    print ('voltage L1: ',vl1,'V')
    print ('voltage L2: ',vl2,'V')
    print ('voltage L3: ',vl3,'V')
    print ('current L1: ',cl1,'A')
    print ('current L2: ',cl2,'A')
    print ('current L3: ',cl3,'A')
    print ('gas delivered: ',gd,'m³')
    print ('foutteller: ',fouttel)
    print ('------------------------------------------------------')

#=======================================================================

def procesGem():
    global loper30, loper1x, pgtot, pg
    # print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 
    if pgtot == 0:                      # opstart
        print('hier voorbij 1')
        loper1x = 1                     # 1x doorlopen = 1 daarna loper1x = 0
        loper30 = 0                     # klaar voor eerste element in array
        pg30arr[0] = pd-pr              # eerste waarde in array
        pgtot = pg30arr[0]              # eerste data
        pg = pgtot                      # berekening onnodig
        loper30 = loper30 +1            # start met 0 daarna 1-30, loper klaar voor 2de input
        print (pg30arr)                 # print array
        print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x)
        return
        
    if loper30 <= 28 and loper1x == 1:
        print('hier voorbij 2')
        pg30arr[loper30] = pd-pr        # plaats laatste vermogen op juiste plaats in array
        loper30 = loper30 +1            # hier loper verhogen zodat we delen door het juiste getal, is array positie +1
        pgtot = np.sum(pg30arr)         # som van de array
        pg = int(pgtot/loper30)         # som array delen door aantal elementen in array, geen commagetallen
        print (pg30arr)                 # print array
        print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 
        return
        
    if loper30 == 29 and loper1x == 1:  # laatste in de rij 
        print('hier voorbij 3')
        pg30arr[loper30] = pd-pr        # plaats laatste vermogen op juiste plaats in array
        pgtot = np.sum(pg30arr)
        pg = int(pgtot/30)              # vanaf nu hebben we 30 waarden, # som array delen door aantal elementen in array, geen commagetallen
        loper30 = 0                     # herbegin lus loper met positie [0]
        loper1x = 0                     # vanaf nu zijn er 30 pg's nu delen door 30  
        print (pg30arr)                 # print array
        print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 
        return
        
    if loper30 <= 28 and loper1x == 0:
        print('hier voorbij 4')
        pg30arr[loper30] = pd-pr        # plaats laatste vermogen op juiste plaats in array
        pgtot = np.sum(pg30arr)         # som array delen door aantal elementen in array, geen commagetallen
        loper30 = loper30 +1
        pg = int(pgtot/30)              # oplossing zoeken voor delen door 30
        print (pg30arr)
        print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 
        return
        
    if loper30 == 29 and loper1x == 0:  # laatste in de rij 
        print('hier voorbij 5')
        pg30arr[loper30] = pd-pr        # plaats laatste vermogen op juiste plaats in array
        pgtot = np.sum(pg30arr)
        pg = int(pgtot/30)              # vanaf nu hebben we 30 waarden, geen commagetallen
        loper30 = 0                     # herbegin lus loper
        loper1x = 0                     # vanaf nu zijn er 30 pg's nu delen door 30
        print (pg30arr)
        print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 
        return
        
    else:
        pass
    #print ('pgtot: ',pgtot,'pg: ',pg,'loper30: ',loper30, 'loper1x: ',loper1x) 


#=======================================================================

def proces900():                    # verwerk gegevens gedurende 900s start op '00 - 15 - 30 - 45' = '0000 - 900 - 1800 - 2700' = 'kw1 - kw2 - kw3 - kw4' kw0 is synchroniseren
    
    global tdss, pg900tot, loper900, pg, losts, kw, kwpkold
    loper900ld = 0; tdssld = 0 
    print('tdss: ', tdss, 'loper900: ', loper900)
    
    if kw == 0:                               # als er nog geen start gevonden is
        if tdss >= 898 and tdss <= 899:       # zoek einde kwartier met reserve 2x
            kw =1                             # klaar start nieuw kwartier
            return                            # einde routine volgende seconde is kw =1 anders behandeld 'voorspel' nog een keer
        if tdss >= 1798 and tdss <= 1799:
            kw =1 
            return       
        if tdss >= 2698 and tdss <= 2699:
            kw =1
            return        
        if tdss >= 3598 and tdss <= 3599:
            kw =1 
            return           
    
    if kw == 1:                               # kwart loopt 
        if tdss >= 0 and tdss <= 1:           # test op begin van kwartier met reserve 2x
            loper900 = tdss                   # eerste kwartier 4x gelijk zetten
            pg900tot = 0                      # cumul resetten
            kwpkold = (edt1-ert1)+(edt2-ert2) # bewaar de energiemeters begin kwartier
            print ('\n','kwpkold:',kwpkold,'kwpk:',kwpk,'dagpk:',dagpk,'\n','************************************************************************')
            
            #voorspel()
 
        if tdss >= 900 and tdss <= 901:       # test op begin van kwartier met reserve
            loper900 = tdss -900              # eerste kwartier 4x gelijk zetten
            pg900tot = 0                      # cumul resetten
            kwpkold = (edt1-ert1)+(edt2-ert2) # bewaar de energiemeters begin kwartier
            #voorspel()

        if tdss >= 1800 and tdss <= 1801:     # test op begin van kwartier met reserve
            loper900 = tdss -1800             # eerste kwartier 4x gelijk zetten
            pg900tot = 0                      # cumul resetten
            kwpkold = (edt1-ert1)+(edt2-ert2) # bewaar de energiemeters begin kwartier
            #voorspel()
            
        if tdss >= 2700 and tdss <= 2701:     # test op begin van kwartier met reserve
            loper900 = tdss -2700             # eerste kwartier 4x gelijk zetten
            pg900tot = 0                      # cumul resetten
            kwpkold = (edt1-ert1)+(edt2-ert2) # bewaar de energiemeters begin kwartier
            #voorspel()
        else:
            voorspel()

#-----------------------------------------------------------------------

def voorspel():                                         # voorspellingen over lopend kwartier + bewaren energietellers en kwartierpiek
    
    global tdss, loper900, pg, path, kwpk, kwpkold, dagpk, limiet, alarm, pv, pg900tot, pd, pr, vl1, vl2, vl3, cl1, cl2, cl3
    if loper900 <= 898:         
        pg900tot = pg900tot + (pg/3600)                 # pg900tot updaten
        pv = pg900tot + (900-loper900) * (pg/3600)      # power imulatie = cumul (pg900tot) + (900-loper900)xpg/3600
        loper900 = loper900 +1                          # loper +1
        loper900ld = int(repr(loper900)[-1])            # laatste cijfer van loper300loperld 
        if loper900ld == 5:                             # iedere 10s wordt de info bekeken voor grafiek
            x = int(loper900/10)                        # komt in de array een voor een ipv per 10
            pg90arr[x] = pg900tot                       # bewaar waarde van pg900tot zo worden er 90 per 900s bewaard dus iedere 10sec. 
            pv90arr[x] = pv                             # vermogen voorspelling 
            beslis()                                    # iedere 10 seconden wordt beslist of er iets moet gebeuren 
            t = Thread(target = mqttPub, args=(loper900, limiet, alarm, pv, pg900tot, pd, pr, pg, vl1, vl2, vl3, cl1, cl2, cl3))
            t.start()                                   # Laat op 2de cpu thread lopen
            # mqttPub(tdss,loper900,limiet,alarm,pg,pv,pg900tot) # # tdss en pg niet gebruikt voor plot
            filedata = "{0}, {1}, {2}, {3}, {4}, {5}, {6}, {7} \n".format(tdss, loper900, limiet, alarm, pg, pv, pg900tot, dagpk) # iedere 10s
            fileW(filedata)                             # schrijf iedere 10 seconden data weg voor de plot
            print('pg90arr: ', pg90arr, '\n', 'pv90arr: ', pv90arr, 'kwpkold: ',kwpkold,'kwpk: ',kwpk, 'dagpk: ', dagpk, 'alarm: ', alarm)
					
        else:                                           # niets doen tussen de 10sec
            print(pg90arr, pv90arr)
 
    else:                                               # nu loper op 899 + bewaar tellerstanden
        kwpk = (edt1-ert1) + (edt2-ert2) - kwpkold      # verschil in verbruik van begin tov einde kwartier
        if kwpk >= dagpk:
            dagpk = kwpk
        kwpkold = kwpk                                  # bewaar de tellerstand op einde kwartier
        
        print ('\n','kwpk:',kwpk,'dagpk',dagpk,'\n','************************************************************************')
        loper900 = loper900 +1


# Thread start ----------------------------------------------------------------------
# Convert Python to JSON			# w3schools.com/python/python_json.asp

def mqttPub(loper900, limiet, alarm, pv, pg900tot, pd, pr, pg, vl1, vl2, vl3, cl1, cl2, cl3):
    bericht = {"loper900": loper900,"limiet":limiet,"alarm":alarm,"pv":pv,"pg900tot":pg900tot,"pd":pd,"pr":pr,"pg":pg,"vl1":vl1,"vl2":vl2,"vl3":vl3,"cl1":cl1,"cl2":cl2,"cl3":cl3}
    berichtjson = json.dumps(bericht)
    try: 
        client.connect (mqtt_server_ip, 1883)
        client.publish (mqtt_topic ,berichtjson)
        client.disconnect()
    except:
        print("FOUT connect SERVER MQTT")
  
# Thread stop ----------------------------------------------------------------------

def beslis():                                           # hier schakelen we toestellen in en uit en wordt een alarm gegeven
    global path, limiet, alarm, alarmh, alarml
    
    alarm = alarmh-((alarmh-alarml) / 900 * loper900)   # in de loop van het kwartier verandert alarmniveau van alarmh naar alarml
    # print ('alarm: ', alarm)
    
#-----------------------------------------------------------------------

def fileW(filedata):                                    # schrijf de meegegeven data op SD kaart
    
    fo = open(path, "a")                                # open file volgens pad, indien onbestaand maak aan
    fo.write (filedata)                                 # Er wordt geschreven in opgegeven pad en voeg nieuwe data toe
    fo.close()                                          # Close opend file
    
#=======================================================================      

# START PROGRAMMA ------------------------------------------------------

print ("Application started!")
dsmr = serial.Serial(SERIAL_PORT, baudrate = 115200, timeout = 0.5)
alarm = alarmh

while running:
    try:                                    # check of er data binnenkomt
        # pass
        getData(dsmr)                       # neem een lijn uit de telegram en filter + foutdetectie   
        # test hier op einde telegram en fout = 0
        # print ('LOOP')                    # komt hier iedere lijn of meerdere malen tussen de telegrams
    except KeyboardInterrupt:               # Ctrl + C
        running = False
        gps.close()
        print ("Application closed!")
    if einde == 1 & vlag1x == 1:            # telegram binnen en hier 1x doorlopen
        vlag1x = 0 
        if fout == 0:                       # als er geen fouten zijn mag de verwerking doorgaan
            print('Fout: ',fout)
            printData()                     # alle gevonden variabelen afdrukken
            procesGem()                     # maak gemiddelden van (pd-pr) + prognose kwartier + check edtx
            proces900()                     # voorspel verloop v/h kwartier + store voor plot + MQTTjson
        else:
            print ('fout gedetecteerd in telegram, neem volgende telegram')
            fout = 0                        # reset fout
    else:
        pass

# EINDE ================================================================

# Voorbeeld Telegram DSMR
'''
/FLU5\253769484_A

0-0:96.1.4(50216)
0-0:96.1.1(3153414733313030333438373435)
0-0:1.0.0(221127120537W)
1-0:1.8.1(003594.884*kWh)
1-0:1.8.2(003108.404*kWh)
1-0:2.8.1(000000.304*kWh)
1-0:2.8.2(000000.149*kWh)
0-0:96.14.0(0002)
1-0:1.7.0(00.264*kW)
0*kW)
1-0:22.7.0(00.000*kW)
1-0:42.7.0(00.000*kW)
1-0:62.7.0(00.000*kW)
1-0:32.7.0(229.0*V)V)
1-0:72.7.0(230.9*V)
1-0:31.7.0(000.99*A)
1-0:51.7.0(001.02*A)
1-0:71.7.0(001.38*A)
0-0:96.3.10(1)
0-0:17.0.0(999.9*kW)
1-0:31.4.0(999*A)
0-0:96.13.0()
0-1:24.1.0(003)
0-1:96.1.1(37464C4F32313231303630353130)
0-1:24.4.0(1)
0-1:24.2.3(221127120500W)(01577.216*m3)
!CB90
'''
    
