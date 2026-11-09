/*
  Kit Smart Agri92 - firmware prototype
  Carte : Adafruit ESP32-S3 Feather (produit 5323)
  Bibliotheques : Adafruit BME280 (+ Unified Sensor), TFT_eSPI
  Ecran : TFT SPI 3.5" 480x320 tactile (pins a declarer dans TFT_eSPI/User_Setup.h)

  Fonctions :
   - humidite du sol (capteur capacitif) + arrosage automatique avec seuils
   - temperature / humidite / pression de l'air (BME280)
   - NPK (capteur RS485 Modbus via module MAX485)
   - alertes : engrais manquant ou plante malade -> ecran + buzzer + LED
   - fonctionnement hors ligne : point d'acces Wi-Fi + mini page locale
*/
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <Adafruit_BME280.h>
#include <TFT_eSPI.h>

// ---------- Broches (Feather ESP32-S3) ----------
#define PIN_SOL       5    // capteur humidite sol (ADC1, compatible Wi-Fi)
#define PIN_BUZZER    6
#define PIN_RS485_DE  11   // DE + RE du MAX485 relies ensemble
#define PIN_RELAIS    12   // module relais de la pompe
#define PIN_LED       13   // LED d'alerte
#define PIN_RX_NPK    44
#define PIN_TX_NPK    43
// I2C BME280 : SDA = GPIO3, SCL = GPIO4 (connecteur STEMMA QT)

// ---------- Etalonnage capteur sol (a mesurer sur le terrain) ----------
int ADC_SEC = 3200;        // capteur dans l'air
int ADC_EAU = 1400;        // capteur plonge dans l'eau

// ---------- Reglages (modifiables via app / site) ----------
int seuilStart = 30;       // % : l'arrosage demarre en dessous
int seuilStop  = 60;       // % : l'arrosage s'arrete au dessus
int seuilN = 20, seuilP = 10, seuilK = 80;   // mg/kg, a etalonner par culture
const unsigned long POMPE_MAX_MS = 10UL * 60UL * 1000UL;  // securite : 10 min

struct Mesures { float sol, temp, hum, pres; int n, p, k; bool pompe; };
Mesures m = {0, 0, 0, 0, 0, 0, 0, false};

Preferences prefs;
Adafruit_BME280 bme;
TFT_eSPI tft;
WebServer server(80);

bool alerteEngrais = false;
bool alertePlante  = false;     // mise a jour par l'IA (ESP-CAM)
bool npkOk = false;
unsigned long pompeDepuis = 0, dernierCycle = 0, dernierBip = 0;

// ---------- Lecture des capteurs ----------
float lireSol() {
  long s = 0;
  for (int i = 0; i < 10; i++) { s += analogRead(PIN_SOL); delay(5); }
  int v = s / 10;
  float pct = (float)(ADC_SEC - v) * 100.0 / (ADC_SEC - ADC_EAU);
  return constrain(pct, 0, 100);
}

bool lireNPK() {
  // Trame Modbus courante pour capteur NPK 3 en 1 (verifier la fiche technique)
  const uint8_t req[8] = {0x01, 0x03, 0x00, 0x1E, 0x00, 0x03, 0x65, 0xCD};
  uint8_t rep[11];
  while (Serial1.available()) Serial1.read();
  digitalWrite(PIN_RS485_DE, HIGH);
  Serial1.write(req, 8);
  Serial1.flush();
  digitalWrite(PIN_RS485_DE, LOW);
  if (Serial1.readBytes(rep, 11) != 11) return false;
  if (rep[0] != 0x01 || rep[1] != 0x03) return false;
  m.n = (rep[3] << 8) | rep[4];
  m.p = (rep[5] << 8) | rep[6];
  m.k = (rep[7] << 8) | rep[8];
  return true;
}

// ---------- Logique ----------
void gererPompe() {
  if (!m.pompe && m.sol <= seuilStart) {
    m.pompe = true;
    pompeDepuis = millis();
  } else if (m.pompe && (m.sol >= seuilStop || millis() - pompeDepuis > POMPE_MAX_MS)) {
    m.pompe = false;
  }
  digitalWrite(PIN_RELAIS, m.pompe ? HIGH : LOW);
}

void gererAlertes() {
  alerteEngrais = npkOk && (m.n < seuilN || m.p < seuilP || m.k < seuilK);
  bool alerte = alerteEngrais || alertePlante;
  digitalWrite(PIN_LED, (alerte && ((millis() / 500) % 2)) ? HIGH : LOW);
  if (alerte && millis() - dernierBip > 10000) {   // un bip toutes les 10 s
    tone(PIN_BUZZER, 2000, 250);
    dernierBip = millis();
  }
}

// ---------- Ecran ----------
void ligne(int y, String t, uint16_t c = TFT_WHITE) {
  tft.setTextColor(c, TFT_BLACK);
  tft.setTextPadding(460);
  tft.drawString(t, 10, y, 4);
}

void afficher() {
  ligne(5,   "Sol : " + String(m.sol, 0) + " %");
  ligne(40,  "Temp : " + String(m.temp, 1) + " C   Air : " + String(m.hum, 0) + " %");
  ligne(75,  "Pression : " + String(m.pres, 0) + " hPa");
  ligne(110, "N " + String(m.n) + "  P " + String(m.p) + "  K " + String(m.k) + " mg/kg");
  ligne(145, m.pompe ? "Pompe : MARCHE" : "Pompe : arret", m.pompe ? TFT_GREEN : TFT_WHITE);
  ligne(190, alerteEngrais ? "ALERTE : sol pauvre en engrais" : "Engrais : OK",
        alerteEngrais ? TFT_RED : TFT_GREEN);
  ligne(225, alertePlante ? "ALERTE : plante malade" : "Plantes : OK",
        alertePlante ? TFT_RED : TFT_GREEN);
}

// ---------- Serveur local ----------
String json() {
  String s = "{";
  s += "\"sol\":" + String(m.sol, 1) + ",\"temp\":" + String(m.temp, 1);
  s += ",\"hum\":" + String(m.hum, 1) + ",\"pres\":" + String(m.pres, 1);
  s += ",\"n\":" + String(m.n) + ",\"p\":" + String(m.p) + ",\"k\":" + String(m.k);
  s += ",\"pompe\":" + String(m.pompe ? "true" : "false");
  s += ",\"alerteEngrais\":" + String(alerteEngrais ? "true" : "false");
  s += ",\"alertePlante\":" + String(alertePlante ? "true" : "false");
  s += ",\"seuilStart\":" + String(seuilStart) + ",\"seuilStop\":" + String(seuilStop) + "}";
  return s;
}

const char PAGE[] PROGMEM =
  "<meta name=viewport content='width=device-width'><h2>Smart Agri92</h2>"
  "<pre id=d>...</pre><script>setInterval(()=>fetch('/data').then(r=>r.text())"
  ".then(t=>d.textContent=t),3000)</script>";

void routes() {
  server.on("/", []() { server.send_P(200, "text/html", PAGE); });
  server.on("/data", []() { server.send(200, "application/json", json()); });
  server.on("/seuils", []() {             // /seuils?start=30&stop=60
    if (server.hasArg("start")) seuilStart = server.arg("start").toInt();
    if (server.hasArg("stop"))  seuilStop  = server.arg("stop").toInt();
    prefs.putInt("start", seuilStart);
    prefs.putInt("stop", seuilStop);
    server.send(200, "application/json", json());
  });
  server.on("/plante", []() {             // appele par l'IA : /plante?etat=1
    alertePlante = server.arg("etat") == "1";
    server.send(200, "application/json", json());
  });
  server.begin();
}

// ---------- Programme ----------
void setup() {
  pinMode(PIN_RELAIS, OUTPUT);   digitalWrite(PIN_RELAIS, LOW);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_RS485_DE, OUTPUT); digitalWrite(PIN_RS485_DE, LOW);
  analogSetAttenuation(ADC_11db);

  Serial1.begin(4800, SERIAL_8N1, PIN_RX_NPK, PIN_TX_NPK);
  Serial1.setTimeout(300);

  Wire.begin();
  if (!bme.begin(0x76) && !bme.begin(0x77)) { /* BME280 absent : valeurs a 0 */ }

  tft.init();
  tft.setRotation(1);            // paysage 480x320
  tft.fillScreen(TFT_BLACK);

  prefs.begin("agri92", false);
  seuilStart = prefs.getInt("start", seuilStart);
  seuilStop  = prefs.getInt("stop",  seuilStop);

  WiFi.mode(WIFI_AP);
  WiFi.softAP("SmartAgri92", "changez-moi-92");   // a personnaliser
  routes();
}

void loop() {
  server.handleClient();
  if (millis() - dernierCycle >= 2000) {
    dernierCycle = millis();
    m.sol  = lireSol();
    m.temp = bme.readTemperature();
    m.hum  = bme.readHumidity();
    m.pres = bme.readPressure() / 100.0;
    npkOk  = lireNPK();
    gererPompe();
    afficher();
  }
  gererAlertes();
}
