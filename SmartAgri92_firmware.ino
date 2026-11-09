/*
  Kit Smart Agri92 - firmware prototype (v1.1 : corrections de l'audit securite)
  Carte : Adafruit ESP32-S3 Feather (produit 5323)
  Bibliotheques : Adafruit BME280 (+ Unified Sensor), TFT_eSPI
  Ecran : TFT SPI 3.5" 480x320 tactile (pins a declarer dans TFT_eSPI/User_Setup.h)

  Fonctions :
   - humidite du sol (capteur capacitif) + arrosage automatique avec seuils
   - temperature / humidite / pression de l'air (BME280)
   - NPK (capteur RS485 Modbus via module MAX485)
   - alertes : engrais manquant, plante malade, defaut pompe ou capteur -> ecran + buzzer + LED
   - fonctionnement hors ligne : point d'acces Wi-Fi + mini page locale

  Securite :
   - mot de passe Wi-Fi et jeton API uniques par kit, crees au 1er demarrage (memoire NVS)
     et affiches 60 s sur l'ecran a chaque demarrage : les noter
   - API locale :
       GET  /         page de consultation
       GET  /data     mesures et etats (JSON)
       POST /seuils?start=30&stop=60   en-tete X-Agri-Token obligatoire
       POST /plante?etat=1 (malade) ou 0 (sain)   en-tete X-Agri-Token obligatoire
   - pour regenerer les identifiants : effacer la flash (Outils > Erase All Flash) puis reflasher
*/
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <esp_random.h>
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

#define RELAIS_ACTIF_HAUT 1   // mettre 0 si le module relais colle a l'etat BAS (verifier le module)

// ---------- Etalonnage capteur sol (a mesurer sur le terrain) ----------
int ADC_SEC = 3200;        // capteur dans l'air
int ADC_EAU = 1400;        // capteur plonge dans l'eau
const int ADC_MARGE = 300; // hors [EAU - marge, SEC + marge] : capteur debranche ou HS

// ---------- Reglages (modifiables via app / site) ----------
int seuilStart = 30;       // % : l'arrosage demarre en dessous
int seuilStop  = 60;       // % : l'arrosage s'arrete au dessus
const int ECART_MIN = 5;   // % : ecart minimal entre les deux seuils
int seuilN = 20, seuilP = 10, seuilK = 80;   // mg/kg, a etalonner par culture
const unsigned long POMPE_MAX_MS   = 10UL * 60UL * 1000UL;  // securite : 10 min de marche maxi
const unsigned long POMPE_REPOS_MS = 30UL * 60UL * 1000UL;  // puis 30 min de verrouillage
const unsigned long ECRAN_ID_MS    = 60UL * 1000UL;         // affichage des identifiants au demarrage

struct Mesures { float sol, temp, hum, pres; int n, p, k; bool pompe; };
Mesures m = {0, 0, 0, 0, 0, 0, 0, false};

Preferences prefs;
Adafruit_BME280 bme;
TFT_eSPI tft;
WebServer server(80);

String ssid, motDePasse, jeton;
bool alerteEngrais = false;
bool alertePlante  = false;     // mise a jour par l'IA (ESP-CAM)
bool npkOk = false, bmeOk = false, capteurSolOk = true;   // sol : fixe par la 1re mesure
bool defautPompe = false, ecranId = true;
unsigned long pompeDepuis = 0, defautDepuis = 0, dernierCycle = 0, dernierBip = 0;

// ---------- Lecture des capteurs ----------
float lireSol() {
  long s = 0;
  for (int i = 0; i < 10; i++) { s += analogRead(PIN_SOL); delay(5); }
  int v = s / 10;
  capteurSolOk = v > ADC_EAU - ADC_MARGE && v < ADC_SEC + ADC_MARGE;
  if (!capteurSolOk) return NAN;
  float pct = (float)(ADC_SEC - v) * 100.0 / (ADC_SEC - ADC_EAU);
  return constrain(pct, 0, 100);
}

uint16_t crcModbus(const uint8_t* d, int n) {     // CRC Modbus RTU (poly 0xA001, init 0xFFFF)
  uint16_t crc = 0xFFFF;
  for (int i = 0; i < n; i++) {
    crc ^= d[i];
    for (int b = 0; b < 8; b++) crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1;
  }
  return crc;
}

bool lireNPK() {
  // Trame Modbus courante pour capteur NPK 3 en 1 (verifier la fiche technique)
  uint8_t req[8] = {0x01, 0x03, 0x00, 0x1E, 0x00, 0x03, 0, 0};
  uint16_t c = crcModbus(req, 6);
  req[6] = c & 0xFF;  req[7] = c >> 8;        // CRC poids faible en premier
  uint8_t rep[11];
  while (Serial1.available()) Serial1.read();
  digitalWrite(PIN_RS485_DE, HIGH);
  Serial1.write(req, 8);
  Serial1.flush();
  digitalWrite(PIN_RS485_DE, LOW);
  int lus = 0;                                // delai total de 300 ms, meme si la ligne est bruitee
  unsigned long t0 = millis();
  while (lus < 11 && millis() - t0 < 300) {
    if (Serial1.available()) rep[lus++] = Serial1.read(); else delay(1);
  }
  if (lus != 11) return false;
  if (rep[0] != 0x01 || rep[1] != 0x03 || rep[2] != 6) return false;   // esclave, fonction, 6 octets
  if (crcModbus(rep, 9) != (rep[9] | (rep[10] << 8))) return false;        // trame corrompue
  m.n = (rep[3] << 8) | rep[4];
  m.p = (rep[5] << 8) | rep[6];
  m.k = (rep[7] << 8) | rep[8];
  return true;
}

// ---------- Logique ----------
void ecrireRelais(bool marche) {
  bool niveau = RELAIS_ACTIF_HAUT ? marche : !marche;
  digitalWrite(PIN_RELAIS, niveau ? HIGH : LOW);
}

void gererPompe() {
  unsigned long t = millis();
  if (defautPompe && t - defautDepuis >= POMPE_REPOS_MS) defautPompe = false;  // nouvel essai
  if (!m.pompe && capteurSolOk && !defautPompe && m.sol <= seuilStart) {
    m.pompe = true;
    pompeDepuis = t;
  } else if (m.pompe && (!capteurSolOk || m.sol >= seuilStop)) {
    m.pompe = false;
  } else if (m.pompe && t - pompeDepuis > POMPE_MAX_MS) {
    m.pompe = false;          // le sol ne remonte pas : capteur hors sol, fuite ou cuve vide
    defautPompe = true;
    defautDepuis = t;
  }
  ecrireRelais(m.pompe);
}

void gererAlertes() {
  alerteEngrais = npkOk && (m.n < seuilN || m.p < seuilP || m.k < seuilK);
  bool alerte = alerteEngrais || alertePlante || defautPompe || !capteurSolOk;
  digitalWrite(PIN_LED, (alerte && ((millis() / 500) % 2)) ? HIGH : LOW);
  if (alerte && millis() - dernierBip > 10000) {   // un bip toutes les 10 s
    tone(PIN_BUZZER, 2000, 250);
    dernierBip = millis();
  }
}

// ---------- Ecran ----------
String txt(float v, int d) { return isnan(v) ? String("--") : String(v, d); }

void ligne(int y, String t, uint16_t c = TFT_WHITE) {
  tft.setTextColor(c, TFT_BLACK);
  tft.setTextPadding(460);
  tft.drawString(t, 10, y, 4);
}

void afficherIdentifiants() {
  tft.fillScreen(TFT_BLACK);
  ligne(5,   "Smart Agri92 - identifiants", TFT_GREEN);
  ligne(50,  "Wi-Fi : " + ssid);
  ligne(85,  "Mot de passe : " + motDePasse);
  ligne(130, "Jeton API :");
  ligne(165, jeton.substring(0, 16));
  ligne(200, jeton.substring(16));
  ligne(260, "A noter : affiche 60 s", TFT_YELLOW);
}

void afficher() {
  ligne(5,   "Sol : " + txt(m.sol, 0) + " %");
  ligne(40,  "Temp : " + txt(m.temp, 1) + " C   Air : " + txt(m.hum, 0) + " %");
  ligne(75,  "Pression : " + txt(m.pres, 0) + " hPa");
  if (npkOk) ligne(110, "N " + String(m.n) + "  P " + String(m.p) + "  K " + String(m.k) + " mg/kg");
  else ligne(110, "NPK : pas de reponse du capteur", TFT_YELLOW);
  if (defautPompe) ligne(145, "Pompe : DEFAUT (arret securite)", TFT_RED);
  else ligne(145, m.pompe ? "Pompe : MARCHE" : "Pompe : arret", m.pompe ? TFT_GREEN : TFT_WHITE);
  ligne(190, alerteEngrais ? "ALERTE : sol pauvre en engrais" : "Engrais : OK",
        alerteEngrais ? TFT_RED : TFT_GREEN);
  ligne(225, alertePlante ? "ALERTE : plante malade" : "Plantes : OK",
        alertePlante ? TFT_RED : TFT_GREEN);
  ligne(260, capteurSolOk ? "Capteur sol : OK" : "ALERTE : capteur sol debranche",
        capteurSolOk ? TFT_GREEN : TFT_RED);
}

// ---------- Identifiants du kit ----------
String genererSecret(int n, const char* alphabet) {
  int a = strlen(alphabet), lim = 256 - (256 % a);   // rejet : pas de biais de modulo
  String s;
  while ((int)s.length() < n) {
    uint8_t b = esp_random() & 0xFF;   // aleatoire materiel (radio Wi-Fi demarree avant l'appel)
    if (b < lim) s += alphabet[b % a];
  }
  return s;
}

String lireOuCreer(const char* cle, int n, const char* alphabet) {
  String s = prefs.getString(cle, "");
  if ((int)s.length() != n) { s = genererSecret(n, alphabet); prefs.putString(cle, s); }
  return s;
}

// ---------- Serveur local ----------
String num(float v, int d) { return isnan(v) ? String("null") : String(v, d); }
String bol(bool v) { return v ? "true" : "false"; }

String json() {
  String s = "{";
  s += "\"sol\":" + num(m.sol, 1) + ",\"temp\":" + num(m.temp, 1);
  s += ",\"hum\":" + num(m.hum, 1) + ",\"pres\":" + num(m.pres, 1);
  if (npkOk) s += ",\"n\":" + String(m.n) + ",\"p\":" + String(m.p) + ",\"k\":" + String(m.k);
  else       s += ",\"n\":null,\"p\":null,\"k\":null";
  s += ",\"pompe\":" + bol(m.pompe) + ",\"defautPompe\":" + bol(defautPompe);
  s += ",\"alerteEngrais\":" + bol(alerteEngrais) + ",\"alertePlante\":" + bol(alertePlante);
  s += ",\"capteurSolOk\":" + bol(capteurSolOk) + ",\"bmeOk\":" + bol(bmeOk) + ",\"npkOk\":" + bol(npkOk);
  s += ",\"seuilStart\":" + String(seuilStart) + ",\"seuilStop\":" + String(seuilStop) + "}";
  return s;
}

const char PAGE[] PROGMEM =
  "<meta name=viewport content='width=device-width'><h2>Smart Agri92</h2>"
  "<pre id=d>...</pre><script>setInterval(()=>fetch('/data').then(r=>r.text())"
  ".then(t=>d.textContent=t),3000)</script>";

void repondre(int code, const String& corps) {
  server.sendHeader("Cache-Control", "no-store");
  server.sendHeader("X-Content-Type-Options", "nosniff");
  server.send(code, "application/json", corps);
}

bool jetonValide() {                      // comparaison en temps constant
  String t = server.header("X-Agri-Token");
  if (t.length() != jeton.length()) return false;
  uint8_t d = 0;
  for (unsigned i = 0; i < t.length(); i++) d |= t[i] ^ jeton[i];
  return d == 0;
}

bool accesCommande() {                    // POST + jeton obligatoires pour modifier l'etat
  if (server.method() != HTTP_POST) { repondre(405, "{\"erreur\":\"POST requis\"}"); return false; }
  if (!jetonValide()) { repondre(401, "{\"erreur\":\"jeton invalide\"}"); return false; }
  return true;
}

bool lireEntier(const String& s, int& v) {    // 1 a 3 chiffres, rien d'autre
  if (s.length() == 0 || s.length() > 3) return false;
  for (unsigned i = 0; i < s.length(); i++) if (!isDigit(s[i])) return false;
  v = s.toInt();
  return true;
}

void routes() {
  const char* entetes[] = {"X-Agri-Token"};
  server.collectHeaders(entetes, 1);
  server.on("/", []() {
    server.sendHeader("Cache-Control", "no-store");
    server.send_P(200, "text/html", PAGE);
  });
  server.on("/data", []() { repondre(200, json()); });
  server.on("/seuils", []() {             // POST /seuils?start=30&stop=60
    if (!accesCommande()) return;
    int start = seuilStart, stop = seuilStop;
    if ((server.hasArg("start") && !lireEntier(server.arg("start"), start)) ||
        (server.hasArg("stop")  && !lireEntier(server.arg("stop"),  stop)) ||
        stop > 100 || stop - start < ECART_MIN) {
      repondre(400, "{\"erreur\":\"seuils invalides : 0 <= start, start + 5 <= stop <= 100\"}");
      return;
    }
    if (start != seuilStart) { seuilStart = start; prefs.putInt("start", start); }  // ecriture
    if (stop  != seuilStop)  { seuilStop  = stop;  prefs.putInt("stop",  stop);  }  // si changement
    repondre(200, json());
  });
  server.on("/plante", []() {             // appele par l'IA : POST /plante?etat=1
    if (!accesCommande()) return;
    String e = server.arg("etat");
    if (e != "0" && e != "1") { repondre(400, "{\"erreur\":\"etat doit valoir 0 ou 1\"}"); return; }
    alertePlante = e == "1";
    repondre(200, json());
  });
  server.begin();
}

// ---------- Programme ----------
void setup() {
  pinMode(PIN_RELAIS, OUTPUT);   ecrireRelais(false);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_RS485_DE, OUTPUT); digitalWrite(PIN_RS485_DE, LOW);
  analogSetAttenuation(ADC_11db);

  Serial1.begin(4800, SERIAL_8N1, PIN_RX_NPK, PIN_TX_NPK);

  Wire.begin();
  bmeOk = bme.begin(0x76) || bme.begin(0x77);   // absent : mesures a null / "--"

  tft.init();
  tft.setRotation(1);            // paysage 480x320
  tft.fillScreen(TFT_BLACK);

  prefs.begin("agri92", false);
  int a = prefs.getInt("start", seuilStart), b = prefs.getInt("stop", seuilStop);
  if (a >= 0 && b <= 100 && b - a >= ECART_MIN) { seuilStart = a; seuilStop = b; }  // v1 : non verifies

  WiFi.mode(WIFI_AP);            // demarre la radio : esp_random() devient vraiment aleatoire
  String mac = WiFi.softAPmacAddress();
  ssid       = "SmartAgri92-" + mac.substring(12, 14) + mac.substring(15, 17);
  motDePasse = lireOuCreer("wifi", 12, "abcdefghjkmnpqrstuvwxyz23456789");
  jeton      = lireOuCreer("jeton", 32, "0123456789abcdef");
  WiFi.softAP(ssid.c_str(), motDePasse.c_str(), 1, 0, 4);   // WPA2, 4 clients maxi
  routes();
  afficherIdentifiants();

  enableLoopWDT();               // blocage du programme -> redemarrage, pompe coupee
}

void loop() {
  server.handleClient();
  if (millis() - dernierCycle >= 2000) {
    dernierCycle = millis();
    m.sol  = lireSol();
    m.temp = bmeOk ? bme.readTemperature() : NAN;
    m.hum  = bmeOk ? bme.readHumidity() : NAN;
    m.pres = bmeOk ? bme.readPressure() / 100.0 : NAN;
    npkOk  = lireNPK();
    gererPompe();
    if (ecranId && millis() > ECRAN_ID_MS) { ecranId = false; tft.fillScreen(TFT_BLACK); }
    if (!ecranId) afficher();
  }
  gererAlertes();
}
