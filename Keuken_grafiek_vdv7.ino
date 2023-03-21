/*
https://randomnerdtutorials.com/nextion-display-with-arduino-getting-started/ 
 
Configure Library for Arduino ESP32
This library is configured for Arduino MEGA2560 by default. To make it work for Arduino Uno, you need to do the following:

1. Open the ITEADLIB_Arduino_Nextion folder

2. There should be a NexConfig.h file – open that file.

3. Comment line 27, so that it stays as follows:
#define DEBUG_SERIAL_ENABLE         // for ESP32

4. Comment line 32:
#define dbSerial Serial             // for ESP32

5. Change line 37, so that you have the following:
#define nexSerial Serial2           // for ESP32
6. Save the NexConfig.h file.
 */ 
// 
 
//https://raw.githubusercontent.com/RuiSantosdotme/Random-Nerd-Tutorials/master/Projects/ESP32-MQTT/ESP32_MQTT_Publish_Subscribe.ino

// Deze unit werkt draadloos via WiFi en MQTT(json). De Rasberry Pi kan ook de server zijn maar het mag ook een andere server zijn.
// ESP32 serial2 aangesloten op NextionDisplay type: NX3224K028 enkel TX is voldoende. RX niet nodig zo zijn er geen problemen met aanpassing 3V3 en 5V. 
// Werkt samen met display file "NewGrafiekNum1PageV2.HMI" 

// Gebruik Arduino Mega of Mega 2560  Keuken_grafiek_vdv3
// Nu voor ESP32 aangepast            Keuken_grafiek_vdv4
// MQTT (sub) voor ESP32 toegevoegd   Keuken_grafiek_vdv5
// MQTT (sub) met x items uitgebreid  Keuken_grafiek_vdv6   Werkt samen met HMI-display prog: "NewGrafiekNum1PageV2.hmi"   

#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include <ArduinoJson.h> 
#include "Nextion.h"

NexWaveform s0 = NexWaveform(0, 4, "s0");   // page 0, ID, s0  
NexNumber n0 = NexNumber(0, 2, "n0");        //ID niet belangrijk enkel n0 of n1
NexNumber n1 = NexNumber(0, 3, "n1");        //ID niet belangrijk enkel n0 of n
NexNumber n2 = NexNumber(0, 15, "n2");       //ID niet belangrijk enkel n0 of n
NexNumber n3 = NexNumber(0, 16, "n3");       //ID niet belangrijk enkel n0 of n
NexNumber n4 = NexNumber(0, 17, "n4");       //ID niet belangrijk enkel n0 of n
NexNumber n5 = NexNumber(0, 18, "n5");       //ID niet belangrijk enkel n0 of n
NexNumber n6 = NexNumber(0, 9, "n6");        //ID niet belangrijk enkel n0 of n
NexNumber n7 = NexNumber(0, 20, "n7");       //ID niet belangrijk enkel n0 of n
NexNumber n8 = NexNumber(0, 23, "n8");       //ID niet belangrijk enkel n0 of n
NexNumber n9 = NexNumber(1, 24, "n9");       //ID niet belangrijk enkel n0 of n       

// Replace the next variables with your SSID/Password combination
const char* ssid = "VDV Communicatie";
const char* password = "hertsberge";

// Add your MQTT Broker IP address:
//const char* mqtt_server = "192.168.1.105";
const char* mqtt_server = "192.168.0.248";

WiFiClient espClient;
PubSubClient client(espClient);

// float heeft geen zin, werkt niet met commas naa de display
int tdss = 190258;               // tijd in seconden
int loper900 = 134;              // teller 0 - 900
int limiet = 1000;               // rood
int alarm1 = 900;                // blauw                             INT?
float pv = 645.8;                // geel gemiddeld vermogen op kwartier basis
float pg900tot = 721;            // groen cummul gemiddeld vermogen
int pd = 1;                      // vermogen deliverd in W op uur basis
int pr = 1;                      // vermogen return
int pg = 1;                      // vermogen gemiddeld
int vl1 = 1;                     // spanning L1
int vl2 = 1;                     // spanning L2
int vl3 = 1;                     // spanning L3
int cl1 = 1;                     // stroom L1
int cl2 = 1;                     // stroom L2
int cl3 = 1;                     // stroom L3
StaticJsonDocument<300> berichtjson;  // toegevoed voor json      !!! Buffer !!!
const int ledPin = 2;            // Blauwe led ingebouwd

//------------------------------------------------------------------------------
void setup(void)
{
    nexInit();        // Serial = 9600  Serial1 = 9600
    delay(2000);
    setup_wifi();
    client.setServer(mqtt_server, 1883);
    client.setCallback(callback);
    pinMode(ledPin, OUTPUT);
    dbSerialPrintln("setup done");
}
//------------------------------------------------------------------------------
void loop(void){
  
  if (!client.connected()) {
    reconnect();
  }
  client.loop();            // Callback kijkt of er een bericht binnen is.
}

//===============================================================================
void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println(""); Serial.println("WiFi connected"); 
  Serial.println("IP address: "); Serial.println(WiFi.localIP());
}

//----------------------------------------------------------------------------------------
void SendToNextion(){
      
// stuur 4 volgende punten naar de grafiek + 9 getallen   
    digitalWrite(ledPin, HIGH);       // led aan
    s0.addValue(0, limiet/10);        // rood
    s0.addValue(1, alarm1/10);        // blauw
    s0.addValue(2, pv/10);            // geel    
    s0.addValue(3, pg900tot/10);      // groen          // groen  MAX = 149 dan plafond
    n0.setValue(pg900tot);            // getal 0 naar page 0
    n1.setValue(pv);                  // getal 1 naar page 0 
    n2.setValue(vl1);                 // getal 2 naar page 0
    n3.setValue(cl1);                 // getal 3 naar page 0
    n4.setValue(vl2);                 // getal 4 naar page 0
    n5.setValue(cl2);                 // getal 5 naar page 0
    n6.setValue(vl3);                 // getal 6 naar page 0
    n7.setValue(cl3);                 // getal 7 naar page 0
    n8.setValue(pd);                  // getal 8 naar page 0     
    n9.setValue(pr);                  // getal 0 naar page 1 
    Serial.print(cl3);                   
    digitalWrite(ledPin, LOW);        // led uit
    
}

//-------------------------------------------------------------------------------

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageRX;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageRX += (char)message[i];
  }
  Serial.println();

  // Feel free to add more if statements to control more GPIOs with MQTT

  // If a message is received on the topic esp32/output, you check if the message is either "on" or "off". 
  // Changes the output state according to the message
  if (String(topic) == "esp32/json") {
    //Serial.println(messageRX);
    DeserializationError error = deserializeJson(berichtjson, messageRX);
    // Test if parsing succeeds.
    if (error) {                    // kan eventueel weggelaten worden
      Serial.print(F("deserializeJson() failed: "));
      Serial.println(error.f_str());
      return;
    }

    loper900 = berichtjson["loper900"];     // niet nodig
    limiet = berichtjson["limiet"]; 
    alarm1 = berichtjson["alarm"]; 
    pv = berichtjson["pv"];
    pg900tot = berichtjson["pg900tot"];
    pd = berichtjson["pd"];
    pr = berichtjson["pr"];
    vl1 = berichtjson["vl1"];
    vl2 = berichtjson["vl2"];
    vl3 = berichtjson["vl3"];
    cl1 = berichtjson["cl1"];
    cl2 = berichtjson["cl2"];
    cl3 = berichtjson["cl3"];

    SendToNextion();
    Serial.println("Stuur data naar Nextion display");
  }
}

//------------------------------------------------------------------------------
void reconnect() {
  
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Attempt to connect
    if (client.connect("ESP8266Client")) {
      Serial.println("connected");
      // Subscribe
      client.subscribe("esp32/json");   // topic aangepast
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}

// EINDE========================================================================
