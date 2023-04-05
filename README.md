# BSMR-BelgiumSmartMeter-DSMR
Dit programma kan gebruikt worden om de data die iedere seconde uit de Vlaamse Fluvius elektronische elektriciteitsteller komt binnen te nemen en de nodige parameters te verwerken.
Deze data gaan we gebruiken om energiepieken te voorspellen en eventueel in te grijpen om een vermogenpiek te voorkomen. De gegevens worden door een Raspberry Pi binnengenomen via de serial0 poort en de nodige data wordt opgeslagen op de SD-kaart. Intussen wordt ook data via MQTT opgezonden naar een afzonderlijke display die de grafiek van het lopende kwartier zichtbaar maakt samen met de vermogens, fasespanningen en fasestromen. De Raspberry Pi doet dus ook dienst als MQTT-server maar dat mag ook een afzonderlijke server zijn.

De Belgium Smart Meter BSMR, gebaseerd op de Dutch Smart Meter Requirements of DSMR, mits aangepaste parameters. Zie document "e-MUCS_P1_Ed_1_4".

Dit project bestaat uit verschillende onderdelen die moeten samenwerken. 
NOTA:
Voor wie geen SmartMeter heeft is er een simulatie van 20 minuten beschikbaar. 
"telegram20min.txt" is een voorbeeld van een opname van 20 minuten data die ierdere seconde uit een Belgische teller komt. De simulatie komt uit een ESP32 via poort TX0. Dit kan gebruikt worden indien geen teller voor handen is.

DEEL1:


Iedere SmartTeller heeft een P1 aansluiting RJ12 (6 geleiders) waarop onze RPI wordt aangesloten via een kleine aanpassing naar Serial0. Schema zie "Aanpassing P1-RJ12"
Die data noemen we een telegram en komt iedere seconde uit de P1 connector met een snelheid 115200. Telegrammen worden binnengenomen in een Raspberry Pi via de serial0. Het programma "BSMR9.py" verwerkt deze data. Dit betekent: neemt de nodige data uit de telegram en verwerkt die zodat deze bruikbaar worden om grafieken te maken en belastingen te schakelen.

DEEL2:


Een tweede deel bestaat uit een ESP32 en een Nextion HMI-dispaly NX3224K028 die draadloos de nuttige gegevens zichtbaar maken alook een grafiek rond het kwartierverloop. Hiervoor is het Arduinoprogramma "keuken_grafiek_vdv8.ino" en display programma "NewGrafiekNum2PageV4.HMI" van toepassing. Het eerste wordt in een ESP32 geplaatst en het tweede is het formateren van de display in de gewenste layout. De display is van het type Nextion NX3224K028 met een 2.8" scherm. Om dit te doen is een aangepast programma nodig die moet geinstallerd worden van Nextion https://nextion.tech/nextion-editor/#_section1

Wie niet wenst te werken met de display kan de grafiek ook bekomen op het scherm van de Raspberry Pi door "BSMRplotData1.py" te laten lopen. Deze kijkt naar de file "forcast.csv" die "BSMR9.py" genereerde en plot deze op het scherm.




