#include <WiFi.h>
#include <PubSubClient.h>

#include <Adafruit_AHTX0.h>

// ---------- Temp Humi ----------
Adafruit_AHTX0 aht;

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

// ============================================================
//  SETUP
// ============================================================
void setup() {
  Serial.begin(115200);

  if (! aht.begin()) {
    Serial.println("Could not find AHT? Check wiring");
    while (1) delay(10);
  }
  Serial.println("AHT10 or AHT20 found");

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

    sensors_event_t humidity, temp;
    aht.getEvent(&humidity, &temp);// populate temp and humidity objects with fresh data
    Serial.print("Temperature: "); Serial.print(temp.temperature); Serial.println(" degrees C");
    Serial.print("Humidity: "); Serial.print(humidity.relative_humidity); Serial.println("% rH");

    String t = String(temp.temperature,2);
    String h = String(humidity.relative_humidity,2);
    client.publish("temp", t.c_str());
    client.publish("humi", h.c_str());
    Serial.println("Published: Temp and Humidity");
  }
}
