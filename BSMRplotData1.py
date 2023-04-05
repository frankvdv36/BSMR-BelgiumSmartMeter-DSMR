# https://stackoverflow.com/questions/20928892/python-numpy-array-reading-from-text-file-to-2d-array

# Dit programma werkt los van de BSMR verie x
# Leest de file 'forcast.csv' in en maakt die klaar voor PLOT
# Converter file to array
# berekening doen op ieder element
# maar er een list van
# PLOT 4 lijnen

# berekent de 4 y-assen en de x-as.
# De lengte van de tabel is = aantal lijnen inde tabel

# https://stackoverflow.com/questions/70828615/converting-data-file-into-numpy-arrays0

# Programma neemt 'forcast.csv' en PLOT
# Resultaat is een float
# 'BSMRplotData1.py' aangepast voor variabele filename via input

import time
import numpy as np
import matplotlib.pyplot as plt             # to install; open LX terminal, cd Desktop, pip install matplotlib    # DOE DIT EERST

path = '/home/pi/Python3/DSMR/forcast.csv'
path1= '/home/pi/Python3/DSMR/forcast'
fname = ""
np.set_printoptions(formatter={'float': '{: 0.1f}'.format})     # formaat van printen

# START ----------------------------------------------------------------

# Input + check
fname = str(input("Input filename forcastx.csv (x = extra): "))     # gebruik als er letters/cijfers zijn (str)
try:
    fname = open(path1+fname+'.csv', "r")    # path + file name  /home/pi/Python3/DSMR 
    # print('fname',fname)
except:
    print ('File bestaat niet, probeer opnieuw')    # https://maschituts.com/how-to-restart-a-program-in-python-explained/
    time.sleep(2)
    quit()

# Maak array van ieder element    
data =[]                       # format(tdss, loper900, limiet, alarm, pg, pv, pg900tot)
for line in fname.readlines():
    data.append(np.fromstring(line,sep=','))
data_array = np.array(data)
x = data_array [:,1]           # 1Darray loper900
y1 = data_array[:,2]           # 1Darray limiet         ROOD
y2 = data_array[:,3]           # 1Darray alarm          BLAUW
y3 = data_array[:,5]           # 1Darray pv             GEEL
y4 = data_array[:,6]           # 1Darray pg900tot       GROEN
                             
# Bepaal lengte lijst voor x-as
lengte = 0
for i in x:
    lengte = lengte + 1
    
print("Lengte van de tabel: " + str(lengte))

# Maak van de array een list
X  = x.tolist()               # array to list
Y1 = y1.tolist()              # array to list   ROOD
Y2 = y2.tolist()              # array to list   BLAUW
Y3 = y3.tolist()              # array to list   GEEL
Y4 = y4.tolist()              # array to list   GROEN
  
# PLOT -----------------------------------------------------------------

# https://www.geeksforgeeks.org/simple-plot-in-python-using-matplotlib/
# to install; open LX terminal, cd Desktop, pip install matplotlib

plt.plot(Y1,'r')
plt.plot(Y2, "b")     # bepaal kleur r, g, or, y, b
plt.plot(Y3, "y")     # bepaal kleur r, g, or, y, b
plt.plot(Y4, 'g')     # idem           # 4th is 4de lijn
  
# naming the x-axis
plt.xlabel('tijd/10sec.')              # tekst x-as
  
# naming the y-axis
plt.ylabel('power (W/15min)')                 # tekst y-as
  
# get current axes command
ax = plt.gca()
  
# get command over the individual
# boundary line of the graph body
ax.spines['right'].set_visible(False)   # geen kader rond grafiek
ax.spines['top'].set_visible(False)
#ax.spines['right'].set_visible(True)   # wel kader rond grafiek
#ax.spines['top'].set_visible(True)
  
# set the range or the bounds of 
# the left boundary line to fixed range
ax.spines['left'].set_bounds(0, 1500)    # lengte lijn y-as
  
# set the interval by  which 
# the x-axis set the marks
plt.xticks(list(range(0, lengte+5, 10)))         # X-as van 0 tot 90 per 10sec (laatste element niet)
  
# set the intervals by which y-axis
# set the marks
plt.yticks(list(range(0, 1600, 100)))            # Y-as van 0 tot 1500 W/15min (laatste element niet)
  
# legend denotes that what color 
# signifies what
ax.legend(['limiet', 'alarm', 'cumul', 'voorspelling'])   # legende in minikader naast grafiek
  
# annotate command helps to write
# ON THE GRAPH any text xy denotes 
# the position on the graph
plt.annotate('IEDER STREEPJE = 100sec', xy = (30, -9))  # tekst boven x-as extra uitleg + coordinaten (1.01, -2.15)
  
# gives a title to the Graph
plt.title('Vermogen per kwartier')             # titel bovenaan
  
plt.show()

# END ==================================================================


