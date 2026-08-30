#include <WiFiManager.h> // https://github.com/tzapu/WiFiManager


void setup() {
    
    // WiFi.mode(WIFI_STA); // explicitly set mode, esp defaults to STA+AP
    // it is a good practice to make sure your code sets wifi mode how you want it.

    // put your setup code here, to run once:
    Serial.begin(115200);
    
    //WiFiManager, Local intialization. Once its business is done, there is no need to keep it around
    WiFiManager wm;

    // Test de reset ssid et mdp précédents
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
    }

    //Setup Nichoir

}

void loop() {
    // Nichoir  
}
