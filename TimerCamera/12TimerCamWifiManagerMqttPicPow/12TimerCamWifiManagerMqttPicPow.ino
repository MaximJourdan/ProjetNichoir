#include <WiFi.h>
#include <PubSubClient.h>

#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

#include "M5TimerCAM.h"

#include <WiFiManager.h> // https://github.com/tzapu/WiFiManager

// ===== CONFIGURATION WiFi =====
//const char* ssid = "Asus2.4Max";
//const char* password = "2025ProjetSmarttt";

// ===== CONFIGURATION MQTT =====
const char* mqtt_server = "192.168.1.168";  // IP du Raspberry Pi
const int mqtt_port = 1883;
const char* mqtt_topic_image = "nichoir/camera/image";
const char* mqtt_topic_metadata = "nichoir/camera/metadata";
const char* mqtt_client_id = "M5TimerCAM";

// ===== PINS CAMÉRA (M5Stack TimerCAM) =====
#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM 15
#define XCLK_GPIO_NUM 27
#define SIOD_GPIO_NUM 25
#define SIOC_GPIO_NUM 23
#define Y9_GPIO_NUM 19
#define Y8_GPIO_NUM 36
#define Y7_GPIO_NUM 18
#define Y6_GPIO_NUM 39
#define Y5_GPIO_NUM 5
#define Y4_GPIO_NUM 34
#define Y3_GPIO_NUM 35
#define Y2_GPIO_NUM 32
#define VSYNC_GPIO_NUM 22
#define HREF_GPIO_NUM 26
#define PCLK_GPIO_NUM 21

// ===== VARIABLES GLOBALES =====
WiFiClient espClient;
PubSubClient mqttClient(espClient);

int photoCounter = 0;
unsigned long lastPhotoTime = 0;
const unsigned long PHOTO_INTERVAL = 60000; // 1 minute


void setup() {
    
    Serial.begin(115200);
    Serial.println("\n--- Démarrage M5Stack TimerCAM (MQTT) ---");

    // Désactiver le brownout detector
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    // LED interne
    pinMode(2, OUTPUT);
    digitalWrite(2, LOW);

    // Configuration de la caméra
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;

    if(psramFound()){
        config.frame_size = FRAMESIZE_SVGA; // 800x600
        config.jpeg_quality = 12;
        config.fb_count = 2;
        Serial.println("PSRAM détectée - Haute qualité");
    } else {
        config.frame_size = FRAMESIZE_VGA; // 640x480
        config.jpeg_quality = 15;
        config.fb_count = 1;
        Serial.println("Pas de PSRAM - Qualité standard");
    }

    // Initialisation de la caméra
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("❌ Erreur caméra: 0x%x\n", err);
        ESP.restart();
    }
    Serial.println("✅ Caméra initialisée");

    //Connexion WiFi
    connectWiFi();

    // INITIALISATION TIMER CAM (OBLIGATOIRE)
    TimerCAM.begin();
    Serial.println("TimerCAM initialisé");
    getBatteryLevel();

    // Configuration MQTT
    mqttClient.setServer(mqtt_server, mqtt_port);
    mqttClient.setBufferSize(40000); // Augmenter la taille du buffer pour les images

    // Connexion MQTT
    connectMQTT();

    Serial.println("--- Système prêt - Capture automatique toutes les minutes ---");

    // Première photo au démarrage
    delay(2000);
    Serial.println("\n📸 Capture de la première photo...");
    captureAndSendPhoto();
    lastPhotoTime = millis();

}

void loop() {
    // Maintenir la connexion MQTT
    if (!mqttClient.connected()) {
        connectMQTT();
    }
    mqttClient.loop();

    unsigned long currentTime = millis();

    // Vérifier si 1 minute s'est écoulée
    if (currentTime - lastPhotoTime >= PHOTO_INTERVAL) {
        Serial.println("\n⏰ 1 minute écoulée - Capture automatique");

        if(captureAndSendPhoto()) {
            photoCounter++;
            Serial.printf("✅ Photo #%d envoyée avec succès\n", photoCounter);
            Serial.printf("⏳ Prochaine photo dans 1 minute...\n");
        } else {
            Serial.println("❌ Échec de l'envoi - Nouvelle tentative dans 1 minute");
        }

        lastPhotoTime = currentTime;
    }

    //Vérifier si le PIR détecte, allumer la LED et ensuite Photo

    delay(100);
}

void connectWiFi() {
    //WiFiManager, Local intialization. Once its business is done, there is no need to keep it around
    WiFiManager wm;
    // WiFi.mode(WIFI_STA); // explicitly set mode, esp defaults to STA+AP
    
    // Test avec un reset ssid et mdp save en NVS précédents
    //wm.resetSettings();

    // Automatically connect using saved credentials,
    // if connection fails, it starts an access point with the specified name ( "AutoConnectAP"),
    // if empty will auto generate SSID, if password is blank it will be anonymous AP (wm.autoConnect())
    // then goes into a blocking loop awaiting configuration and will return success result

    bool res;
    // res = wm.autoConnect(); // auto generated AP name from chipid
    // res = wm.autoConnect("AutoConnectAP"); // anonymous ap
    res = wm.autoConnect("NichoirMaxMod","password"); // password protected ap

    if(!res) {
        Serial.println("WifiManager Failed to connect\n");
        ESP.restart();
    } else {
        //Wifi Connecté   
        Serial.println("WifiManager connected\n");
        Serial.print("Adresse IP: ");
        Serial.println(WiFi.localIP());
    }
}


void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Connexion MQTT...");
    
    if (mqttClient.connect(mqtt_client_id)) {
      Serial.println("✅ MQTT connecté");
    } else {
      Serial.print("❌ Échec, code erreur: ");
      Serial.print(mqttClient.state());
      Serial.println(" - Nouvelle tentative dans 5s");
      delay(5000);
    }
  }
}

bool captureAndSendPhoto() {
  // Vérification WiFi
  if(WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi déconnecté");
    connectWiFi();
    return false;
  }

  // Vérification MQTT
  if(!mqttClient.connected()) {
    connectMQTT();
    return false;
  }

  // Allumer la LED
  digitalWrite(2, HIGH);

  // Capture de l'image
  camera_fb_t * fb = esp_camera_fb_get();
  if(!fb) {
    Serial.println("❌ Échec capture caméra");
    digitalWrite(2, LOW);
    return false;
  }

  Serial.printf("📸 Image capturée: %d octets\n", fb->len);

  // Envoi des métadonnées
  String metadata = "{";
  metadata += "\"photo_id\":" + String(photoCounter) + ",";
  metadata += "\"timestamp\":" + String(millis()) + ",";
  metadata += "\"size\":" + String(fb->len) + ",";
  metadata += "\"battery\":" + String(getBatteryLevel()) + ",";
  metadata += "\"source\":\"AUTO\"";
  metadata += "}";
  
  mqttClient.publish(mqtt_topic_metadata, metadata.c_str());
  Serial.println("📤 Métadonnées envoyées");

  // Envoi de l'image en plusieurs morceaux si nécessaire
  bool success = sendImageMQTT(fb);

  // Libération de la mémoire
  esp_camera_fb_return(fb);
  digitalWrite(2, LOW);

  return success;
}

bool sendImageMQTT(camera_fb_t * fb) {
  const int CHUNK_SIZE = 8192; // 8KB par paquet
  int totalChunks = (fb->len + CHUNK_SIZE - 1) / CHUNK_SIZE;
  
  Serial.printf("📤 Envoi de l'image en %d morceaux...\n", totalChunks);

  for(int i = 0; i < totalChunks; i++) {
    int start = i * CHUNK_SIZE;
    int remaining = fb->len - start;
    int chunkSize = (remaining < CHUNK_SIZE) ? remaining : CHUNK_SIZE;
    
    // Publier le morceau
    bool published = mqttClient.publish(mqtt_topic_image, 
                                        fb->buf + start, 
                                        chunkSize, 
                                        false);
    
    if(!published) {
      Serial.printf("❌ Échec envoi morceau %d/%d\n", i+1, totalChunks);
      return false;
    }
    
    Serial.printf("✓ Morceau %d/%d envoyé\n", i+1, totalChunks);
    delay(50); // Petit délai entre les morceaux
  }
  
  // Signal de fin d'image
  mqttClient.publish(mqtt_topic_metadata, "{\"status\":\"complete\"}");
  Serial.println("✅ Image complète envoyée");
  
  return true;
}

int getBatteryLevel() {
    Serial.printf("Bat Voltage: %dmv\r\n", TimerCAM.Power.getBatteryVoltage());
    Serial.printf("Bat Level: %d%%\r\n", TimerCAM.Power.getBatteryLevel());

    String volt = String(TimerCAM.Power.getBatteryVoltage());
    String levl = String(TimerCAM.Power.getBatteryLevel());
    mqttClient.publish("Volt", volt.c_str());
    mqttClient.publish("Levl", levl.c_str());
    
    return TimerCAM.Power.getBatteryLevel(); //int envoyé vers mqtt
}

