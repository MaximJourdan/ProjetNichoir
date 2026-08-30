#include "M5TimerCAM.h"  

#include <WiFi.h>
#include <PubSubClient.h>

#include <base64.h>

// ---------- WIFI ----------
const char* ssid     = "Asus2.4Max";
const char* password = "2025ProjetSmarttt";

// ---------- MQTT ----------
const char* mqtt_server = "192.168.1.168";
WiFiClient espClient;
PubSubClient client(espClient);

// ---------- WIFI CONNECT ----------
void setupWiFi() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
}

// ---------- MQTT RECONNECT ----------
void reconnectMQTT() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("TimerCamTestClient")) {   // clientID
      Serial.println("connected!");
    } else {
      Serial.print("failed rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 2s");
      delay(2000);
    }
  }
}

// -------------- My camera init --------------
void myCamInit(){
   if (!TimerCAM.Camera.begin()) {
      Serial.println("Camera Init Fail");
      return;
  }
  Serial.println("Camera Init Success");

  TimerCAM.Camera.sensor->set_pixformat(TimerCAM.Camera.sensor, PIXFORMAT_JPEG);
  // 2MP Sensor
  TimerCAM.Camera.sensor->set_framesize(TimerCAM.Camera.sensor, FRAMESIZE_UXGA);
  // 3MP Sensor
  // TimerCAM.Camera.sensor->set_framesize(TimerCAM.Camera.sensor, FRAMESIZE_QXGA);

  TimerCAM.Camera.sensor->set_vflip(TimerCAM.Camera.sensor, 1);
  TimerCAM.Camera.sensor->set_hmirror(TimerCAM.Camera.sensor, 0);
}

// ------------ My Picture Function------------
void TakePictureFct(){
  if (TimerCAM.Camera.get()) {

    size_t len = TimerCAM.Camera.fb->len;
    String myLen = String(TimerCAM.Camera.fb->len);
    uint8_t* buf = TimerCAM.Camera.fb->buf;

    Serial.printf("Captured JPG: %d bytes\n", len);

    // ----------- PUBLISH PICTURE -----------
    // IMPORTANT: binary-safe MQTT publish
    bool ok = client.publish("picture", buf, len);
    
    String encodedImg = base64::encode(buf,len);
    bool okBase64 = client.publish("picture64", encodedImg.c_str());
    client.publish("picsize", myLen.c_str());

    if (ok)
        Serial.println("MQTT: Picture sent!");
    else
        Serial.println("MQTT: Failed to send picture!");

    if (okBase64)
        Serial.println("MQTT: Picture64 sent!");
    else
        Serial.println("MQTT: Failed to send picture64!");

    // free frame buffer
    TimerCAM.Camera.free();
  }
}

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  TimerCAM.begin(true);
  myCamInit();

  setupWiFi();

  client.setServer(mqtt_server, 1883);
  reconnectMQTT();

 
}

// ============================================================
//  LOOP
// ============================================================
unsigned long lastMsg = 0;

void loop() {
  if (!client.connected()) reconnectMQTT();
  client.loop();

  unsigned long now = millis();
  if (now - lastMsg > 5000) {
    lastMsg = now;

    //Send Battery Voltage and Level
    Serial.printf("Bat Voltage: %dmv\r\n", TimerCAM.Power.getBatteryVoltage());
    Serial.printf("Bat Level: %d%%\r\n", TimerCAM.Power.getBatteryLevel());

    String volt = String(TimerCAM.Power.getBatteryVoltage());
    String levl = String(TimerCAM.Power.getBatteryLevel());

    client.publish("Volt", volt.c_str());
    client.publish("Levl", levl.c_str());
    Serial.println("Published: Voltage and Level");
    TakePictureFct();
  }
}
