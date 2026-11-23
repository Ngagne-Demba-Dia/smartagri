/*
  ============================================================
  SMART AGRI92 - V7 : DASHBOARD AGRO-METEO PROFESSIONNEL
  ESP32-S3 Feather + TFT ILI9488 480x320 (paysage)
  SEN0500 + humidite du sol analogique + NPK RS485 Modbus
  LED alerte + LED OK + buzzer + relais pompe

  Corrections de cette version :
  - L'ecran n'est plus efface et redessine en entier toutes les
    2 secondes (c'etait ce qui donnait l'impression d'un
    redemarrage). Seules les cartes dont la valeur change sont
    redessinees.
  - Le graphique ne prend un point que toutes les 30 secondes.
  - NPK : shield RS485 en mode MANU, direction pilotee par D12.

  Cablage shield DFRobot RS485 (mode MANU, valide par test) :
    Commutateur AUTO/MANU -> MANU
    Commutateur ON/OFF     -> ON
    Broche 2 du shield     -> D12 (GPIO12)
    Broche 0 / RXD         -> A0 (GPIO18) via diviseur 1k / 2k
    Broche 1 / TXD         -> A1 (GPIO17)
    5V -> USB, GND -> GND

  Bibliotheques :
    - GFX Library for Arduino (Arduino_GFX_Library)
    - DFRobot_EnvironmentalSensor
    - ModbusMaster
  ============================================================
*/

#include <Arduino_GFX_Library.h>
#include <Wire.h>
#include <DFRobot_EnvironmentalSensor.h>
#include <ModbusMaster.h>
#include <math.h>
#include <string.h>

// -------------------- BROCHES --------------------
#define I2C_SDA       3
#define I2C_SCL       4
#define SOIL_PIN      8
#define LED_PIN       13
#define LED_OK_PIN    15
#define BUZZER_PIN    14
#define RELAY_PIN     11
#define NPK_RX_PIN    18
#define NPK_TX_PIN    17
#define NPK_DE_RE     12   // D12 -> broche 2 du shield (mode MANU)

#define SEN0500_ADDR  0x22
#define BUZZER_ON     LOW
#define BUZZER_OFF    HIGH

// -------------------- ECRAN TFT --------------------
Arduino_DataBus *bus = new Arduino_ESP32SPI(10, 9, 36, 35, 37);
Arduino_GFX *gfx = new Arduino_ILI9488_18bit(bus, 6, 1, false);

// -------------------- CAPTEURS --------------------
DFRobot_EnvironmentalSensor environnement(SEN0500_ADDR, &Wire);

HardwareSerial NpkSerial(1);
ModbusMaster npk;

bool capteurOK = false;
bool npkOK = false;
bool solSec = false;

float temperature = NAN;
float humiditeAir = NAN;
float pression = NAN;
float indiceUV = NAN;
float lumiere = NAN;

int humiditeSol = 0;
int valeurN = 0;
int valeurP = 0;
int valeurK = 0;

// -------------------- CALIBRATION DU SOL --------------------
int SOIL_DRY = 3000;
int SOIL_WET = 1300;

const int SEUIL_SOL_SEC = 30;

// -------------------- SEUILS NPK --------------------
const int N_FAIBLE = 20;
const int N_BON = 40;

const int P_FAIBLE = 10;
const int P_BON = 20;

const int K_FAIBLE = 100;
const int K_BON = 200;

enum EtatEngrais {
  ENGRAIS_INCONNU,
  ENGRAIS_PAUVRE,
  ENGRAIS_CORRECT,
  ENGRAIS_RICHE
};

EtatEngrais etatEngrais = ENGRAIS_INCONNU;

// -------------------- TEMPORISATIONS --------------------
const unsigned long INTERVALLE_LECTURE = 2000;
const unsigned long INTERVALLE_LECTURE_NPK = 4000;
const unsigned long INTERVALLE_NPK_ERREUR = 10000;
const unsigned long INTERVALLE_RECONNEXION = 3000;
const unsigned long INTERVALLE_HISTORIQUE = 30000;
const unsigned long CLIGNOTEMENT_LED = 300;

unsigned long derniereLecture = 0;
unsigned long derniereLectureNPK = 0;
unsigned long derniereTentativeCapteur = 0;
unsigned long dernierClignotement = 0;
unsigned long derniereHistorique = 0;

bool etatLED = false;

// -------------------- COULEURS RGB565 --------------------
#define C_BG       0x0009
#define C_PANEL    0x0862
#define C_PANEL2   0x10A3
#define C_BORDER   0x2945
#define C_WHITE    0xFFFF
#define C_GRAY     0xBDF7
#define C_MUTED    0x7BEF
#define C_GREEN    0x07E0
#define C_GREEN2   0x3FE0
#define C_TEMP     0xFD20
#define C_HUM      0x04FF
#define C_PRESS    0xFFE0
#define C_UV       0xB81F
#define C_LIGHT    0xFDE0
#define C_SOIL     0x47E8
#define C_ORANGE   0xFC00
#define C_RED      0xF800
#define C_RED_DARK 0x6000
#define C_PURPLE   0xA81F

// -------------------- DIMENSIONS ECRAN --------------------
const int SCREEN_W = 480;
const int SCREEN_H = 320;

const int HEADER_H = 43;

const int TOP_Y = 51;
const int TOP_H = 70;
const int TOP_W = 112;

const int TOP_X[4] = {
  8, 126, 244, 362
};

const int MID_Y = 129;
const int MID_H = 96;

const int NPK_X = 8;
const int NPK_W = 300;

const int LIGHT_X = 316;
const int LIGHT_W = 156;

const int BOT_Y = 233;
const int BOT_H = 77;

const int SOIL_X = 8;
const int SOIL_W = 140;

const int GRAPH_X = 156;
const int GRAPH_W = 192;

const int STATUS_X = 356;
const int STATUS_W = 116;

// -------------------- HISTORIQUE GRAPHIQUE --------------------
const uint8_t HIST_SIZE = 24;

float histTemp[HIST_SIZE];
float histHum[HIST_SIZE];
float histPress[HIST_SIZE];
float histSoil[HIST_SIZE];

uint8_t histIndex = 0;
uint8_t histCount = 0;

bool grapheModifie = true;

// -------------------- DERNIERES VALEURS AFFICHEES --------------------
// Servent a ne redessiner que ce qui a change
char affTemp[18] = "";
char affHum[18] = "";
char affPress[18] = "";
char affUV[18] = "";
int  affLux = -9999;
int  affSol = -9999;
bool affSolSec = false;
int  affN = -1;
int  affP = -1;
int  affK = -1;
bool affNpkOK = false;
EtatEngrais affEtat = ENGRAIS_INCONNU;
bool affEntete = false;
bool affKitSolSec = false;
bool affKitCapteur = false;
bool affKitNpk = false;

// -------------------- FONCTIONS GENERALES --------------------
float borner(float v, float mini, float maxi) {
  if (v < mini) return mini;
  if (v > maxi) return maxi;
  return v;
}

// -------------------- COMMANDE POMPE --------------------
void relaisOn() {
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
}

void relaisOff() {
  pinMode(RELAY_PIN, INPUT);
}

// -------------------- DESSIN DES CARTES --------------------
void dessinerCarte(
  int x,
  int y,
  int w,
  int h,
  uint16_t accent
) {
  gfx->fillRoundRect(x, y, w, h, 9, C_PANEL);
  gfx->drawRoundRect(x, y, w, h, 9, C_BORDER);
  gfx->fillRoundRect(x, y + 5, 3, h - 10, 2, accent);
}

// -------------------- TEXTE CENTRE --------------------
void texteCentre(
  const char *txt,
  int cx,
  int y,
  uint16_t couleur,
  uint8_t taille
) {
  gfx->setTextSize(taille);
  gfx->setTextColor(couleur);

  int largeur = strlen(txt) * 6 * taille;

  gfx->setCursor(cx - largeur / 2, y);
  gfx->print(txt);
}

// -------------------- ENTETE --------------------
void dessinerEntete() {

  gfx->fillRect(0, 0, SCREEN_W, HEADER_H, 0x0128);

  gfx->drawFastHLine(
    0,
    HEADER_H - 1,
    SCREEN_W,
    C_GREEN
  );

  gfx->fillCircle(19, 20, 7, C_GREEN);
  gfx->fillCircle(19, 20, 3, C_WHITE);

  gfx->setTextColor(C_WHITE);
  gfx->setTextSize(2);
  gfx->setCursor(34, 8);
  gfx->print("SMART ");

  gfx->setTextColor(C_GREEN2);
  gfx->print("AGRI92");

  gfx->setTextSize(1);
  gfx->setTextColor(C_GRAY);
  gfx->setCursor(34, 29);
  gfx->print("AGRICULTURE INTELLIGENTE");

  gfx->fillRoundRect(
    344, 9, 126, 25, 12, C_PANEL2
  );

  gfx->fillCircle(
    357, 21, 4,
    capteurOK ? C_GREEN : C_ORANGE
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(367, 17);

  gfx->print(
    capteurOK ? "STATION EN LIGNE" : "CAPTEUR ABSENT"
  );
}

// -------------------- CARTES METEO --------------------
void dessinerCarteMeteo(
  int x,
  const char *titre,
  const char *valeur,
  const char *unite,
  uint16_t accent
) {

  dessinerCarte(
    x, TOP_Y, TOP_W, TOP_H, accent
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_GRAY);
  gfx->setCursor(x + 10, TOP_Y + 10);
  gfx->print(titre);

  gfx->setTextSize(2);
  gfx->setTextColor(accent);
  gfx->setCursor(x + 10, TOP_Y + 31);
  gfx->print(valeur);

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(x + 10, TOP_Y + 54);
  gfx->print(unite);
}

// -------------------- BADGE DE STATUT NPK (reutilisable) --------------------
void dessinerBadgeNPK(bool surbrillance) {

  uint16_t etatCouleur = C_MUTED;
  uint16_t fondBadge = C_PANEL2;
  const char *etatTxt = "Analyse en attente";

  if (npkOK) {

    if (etatEngrais == ENGRAIS_PAUVRE) {
      etatTxt = "SOL PAUVRE";
      if (surbrillance) {
        fondBadge = C_RED;
        etatCouleur = C_WHITE;
      } else {
        fondBadge = C_RED_DARK;
        etatCouleur = C_RED;
      }
    }
    else if (etatEngrais == ENGRAIS_RICHE) {
      etatCouleur = C_GREEN;
      etatTxt = "SOL RICHE";
    }
    else {
      etatCouleur = C_GREEN2;
      etatTxt = "SOL EQUILIBRE";
    }
  }
  else {
    etatCouleur = C_ORANGE;
    etatTxt = "NPK ABSENT";
  }

  gfx->fillRoundRect(
    NPK_X + 205,
    MID_Y + 5,
    84,
    17,
    7,
    fondBadge
  );

  texteCentre(
    etatTxt,
    NPK_X + 247,
    MID_Y + 9,
    etatCouleur,
    1
  );
}

// -------------------- ZONE NPK --------------------
void dessinerZoneNPK() {

  dessinerCarte(
    NPK_X, MID_Y, NPK_W, MID_H, C_GREEN
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(NPK_X + 12, MID_Y + 9);
  gfx->print("ANALYSE NPK DU SOL");

  const int colX[3] = {
    NPK_X + 53,
    NPK_X + 151,
    NPK_X + 249
  };

  const char *labels[3] = {
    "AZOTE (N)",
    "PHOSPHORE (P)",
    "POTASSIUM (K)"
  };

  const uint16_t colors[3] = {
    C_GREEN,
    C_ORANGE,
    C_PURPLE
  };

  const int vals[3] = {
    valeurN,
    valeurP,
    valeurK
  };

  for (int i = 0; i < 3; i++) {

    if (i > 0) {
      gfx->drawFastVLine(
        NPK_X + 101 + (i - 1) * 98,
        MID_Y + 30,
        54,
        C_BORDER
      );
    }

    gfx->fillCircle(
      colX[i],
      MID_Y + 39,
      12,
      colors[i]
    );

    texteCentre(
      i == 0 ? "N" : (i == 1 ? "P" : "K"),
      colX[i],
      MID_Y + 32,
      C_WHITE,
      1
    );

    gfx->setTextSize(1);
    gfx->setTextColor(C_GRAY);

    int labelW = strlen(labels[i]) * 6;

    gfx->setCursor(
      colX[i] - labelW / 2,
      MID_Y + 56
    );

    gfx->print(labels[i]);

    char b[16];

    snprintf(
      b,
      sizeof(b),
      "%d mg/kg",
      vals[i]
    );

    texteCentre(
      b,
      colX[i],
      MID_Y + 72,
      C_WHITE,
      1
    );
  }

  dessinerBadgeNPK(false);
}

// -------------------- CARTE LUMIERE --------------------
void dessinerCarteLumiere() {

  dessinerCarte(
    LIGHT_X,
    MID_Y,
    LIGHT_W,
    MID_H,
    C_LIGHT
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_GRAY);
  gfx->setCursor(LIGHT_X + 12, MID_Y + 12);
  gfx->print("LUMIERE");

  gfx->setTextSize(2);
  gfx->setTextColor(C_LIGHT);
  gfx->setCursor(LIGHT_X + 12, MID_Y + 34);

  if (isnan(lumiere)) {
    gfx->print("--");
  } else {
    gfx->print((int)lumiere);
  }

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(LIGHT_X + 83, MID_Y + 41);
  gfx->print("lux");

  int largeur = 0;

  if (!isnan(lumiere)) {
    largeur = (int)(
      borner(lumiere, 0, 2000) / 2000.0 * 128
    );
  }

  gfx->drawRoundRect(
    LIGHT_X + 12,
    MID_Y + 72,
    130,
    10,
    4,
    C_BORDER
  );

  if (largeur > 0) {
    gfx->fillRoundRect(
      LIGHT_X + 13,
      MID_Y + 73,
      largeur,
      8,
      3,
      C_LIGHT
    );
  }
}

// -------------------- CARTE HUMIDITE DU SOL --------------------
void dessinerCarteSol() {

  dessinerCarte(
    SOIL_X,
    BOT_Y,
    SOIL_W,
    BOT_H,
    C_SOIL
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_GRAY);
  gfx->setCursor(SOIL_X + 10, BOT_Y + 10);
  gfx->print("HUMIDITE SOL");

  gfx->setTextSize(3);
  gfx->setTextColor(solSec ? C_RED : C_SOIL);

  gfx->setCursor(SOIL_X + 12, BOT_Y + 29);
  gfx->print(humiditeSol);

  gfx->setTextSize(1);
  gfx->print("%");

  gfx->drawRoundRect(
    SOIL_X + 10,
    BOT_Y + 62,
    119,
    8,
    4,
    C_BORDER
  );

  int w = (int)(
    borner(humiditeSol, 0, 100) * 1.15
  );

  if (w > 0) {
    gfx->fillRoundRect(
      SOIL_X + 11,
      BOT_Y + 63,
      w,
      6,
      3,
      solSec ? C_RED : C_GREEN
    );
  }
}

// -------------------- HISTORIQUE --------------------
void ajouterHistorique() {

  histTemp[histIndex] =
    isnan(temperature) ? 0 : temperature;

  histHum[histIndex] =
    isnan(humiditeAir) ? 0 : humiditeAir;

  histPress[histIndex] =
    isnan(pression) ? 0 : pression;

  histSoil[histIndex] = humiditeSol;

  histIndex = (histIndex + 1) % HIST_SIZE;

  if (histCount < HIST_SIZE) {
    histCount++;
  }

  grapheModifie = true;
}

// -------------------- COORDONNEES GRAPHIQUE --------------------
int yGraph(
  float v,
  float minV,
  float maxV,
  int y,
  int h
) {

  float n = (
    borner(v, minV, maxV) - minV
  ) / (maxV - minV);

  return y + h - (int)(n * h);
}

// -------------------- TRACER COURBE --------------------
void tracerCourbe(
  float data[],
  uint16_t couleur,
  int gx,
  int gy,
  int gw,
  int gh,
  float minV,
  float maxV
) {

  if (histCount < 2) return;

  int debut = (
    histIndex + HIST_SIZE - histCount
  ) % HIST_SIZE;

  int ancienX = -1;
  int ancienY = -1;

  for (int i = 0; i < histCount; i++) {

    int idx = (debut + i) % HIST_SIZE;

    int x = gx +
      i * (gw - 1) / (histCount - 1);

    int y = yGraph(
      data[idx],
      minV,
      maxV,
      gy,
      gh
    );

    if (ancienX >= 0) {
      gfx->drawLine(
        ancienX,
        ancienY,
        x,
        y,
        couleur
      );
    }

    ancienX = x;
    ancienY = y;
  }
}

// -------------------- GRAPHIQUE --------------------
void dessinerGraphique() {

  dessinerCarte(
    GRAPH_X,
    BOT_Y,
    GRAPH_W,
    BOT_H,
    C_HUM
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(GRAPH_X + 9, BOT_Y + 8);
  gfx->print("TENDANCE DES MESURES");

  const int gx = GRAPH_X + 10;
  const int gy = BOT_Y + 27;
  const int gw = GRAPH_W - 20;
  const int gh = 39;

  for (int i = 0; i < 3; i++) {

    int yy = gy + i * gh / 2;

    gfx->drawFastHLine(
      gx,
      yy,
      gw,
      C_BORDER
    );
  }

  tracerCourbe(
    histTemp,
    C_TEMP,
    gx, gy, gw, gh,
    0, 50
  );

  tracerCourbe(
    histHum,
    C_HUM,
    gx, gy, gw, gh,
    0, 100
  );

  tracerCourbe(
    histPress,
    C_PRESS,
    gx, gy, gw, gh,
    950, 1050
  );

  tracerCourbe(
    histSoil,
    C_GREEN,
    gx, gy, gw, gh,
    0, 100
  );
}

// -------------------- ETAT DU KIT / ALERTE SOL SEC --------------------
void dessinerEtatKit(bool surbrillance) {

  if (solSec) {

    uint16_t fond = surbrillance ? C_RED : C_RED_DARK;

    gfx->fillRoundRect(
      STATUS_X, BOT_Y, STATUS_W, BOT_H, 9, fond
    );
    gfx->drawRoundRect(
      STATUS_X, BOT_Y, STATUS_W, BOT_H, 9, C_RED
    );

    texteCentre(
      "SOL",
      STATUS_X + STATUS_W / 2,
      BOT_Y + 16,
      C_WHITE,
      2
    );
    texteCentre(
      "SEC !",
      STATUS_X + STATUS_W / 2,
      BOT_Y + 38,
      C_WHITE,
      2
    );

    gfx->setTextSize(1);
    gfx->setTextColor(C_WHITE);
    gfx->setCursor(STATUS_X + 10, BOT_Y + 63);
    gfx->print("Pompe activee");

    return;
  }

  dessinerCarte(
    STATUS_X,
    BOT_Y,
    STATUS_W,
    BOT_H,
    C_GREEN
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_WHITE);
  gfx->setCursor(STATUS_X + 9, BOT_Y + 9);
  gfx->print("ETAT DU KIT");

  bool systemeOK =
    capteurOK && npkOK && !solSec;

  gfx->setTextSize(1);

  gfx->setTextColor(
    systemeOK ? C_GREEN : C_ORANGE
  );

  gfx->setCursor(STATUS_X + 10, BOT_Y + 31);

  gfx->print(
    systemeOK ? "FONCTIONNEL" : "A VERIFIER"
  );

  gfx->setTextColor(C_GRAY);
  gfx->setCursor(STATUS_X + 10, BOT_Y + 51);

  gfx->print(
    capteurOK ? "SEN0500 OK" : "SEN0500 --"
  );

  gfx->setCursor(STATUS_X + 10, BOT_Y + 63);

  gfx->print(
    npkOK ? "NPK OK" : "NPK --"
  );
}

// -------------------- REDESSIN RAPIDE DES ALERTES (clignotement) --------------------
void clignoterAlertes() {

  if (solSec) {
    dessinerEtatKit(etatLED);
  }

  if (npkOK && etatEngrais == ENGRAIS_PAUVRE) {
    dessinerBadgeNPK(etatLED);
  }
}

// -------------------- PIED DE PAGE --------------------
void dessinerPiedPage() {

  gfx->fillRect(
    0, 313, SCREEN_W, 7, 0x0128
  );

  gfx->drawFastHLine(
    8, 313, SCREEN_W - 16, C_BORDER
  );

  gfx->setTextSize(1);
  gfx->setTextColor(C_GRAY);
  gfx->setCursor(10, 315);

  gfx->print(
    "SMART AGRI92 | Surveillance agro-meteorologique"
  );
}

// -------------------- FORMATAGE D'UNE VALEUR --------------------
void formaterValeur(
  char *buf,
  size_t taille,
  float v,
  const char *format
) {
  if (isnan(v)) {
    snprintf(buf, taille, "--");
  } else {
    snprintf(buf, taille, format, v);
  }
}

// -------------------- MISE A JOUR DE L'AFFICHAGE --------------------
// tout = true  : efface l'ecran et dessine tout (au demarrage seulement)
// tout = false : ne redessine que les cartes dont la valeur a change
void mettreAJourAffichage(bool tout) {

  char b[18];

  if (tout) {
    gfx->fillScreen(C_BG);
    dessinerPiedPage();
  }

  // ---- En-tete ----
  if (tout || capteurOK != affEntete) {
    dessinerEntete();
    affEntete = capteurOK;
  }

  // ---- Cartes meteo ----
  formaterValeur(b, sizeof(b), temperature, "%.1f");
  if (tout || strcmp(b, affTemp) != 0) {
    dessinerCarteMeteo(
      TOP_X[0], "TEMPERATURE", b, "deg C", C_TEMP
    );
    strcpy(affTemp, b);
  }

  formaterValeur(b, sizeof(b), humiditeAir, "%.0f");
  if (tout || strcmp(b, affHum) != 0) {
    dessinerCarteMeteo(
      TOP_X[1], "HUMIDITE AIR", b, "%", C_HUM
    );
    strcpy(affHum, b);
  }

  formaterValeur(b, sizeof(b), pression, "%.0f");
  if (tout || strcmp(b, affPress) != 0) {
    dessinerCarteMeteo(
      TOP_X[2], "PRESSION", b, "hPa", C_PRESS
    );
    strcpy(affPress, b);
  }

  formaterValeur(b, sizeof(b), indiceUV, "%.1f");
  if (tout || strcmp(b, affUV) != 0) {
    dessinerCarteMeteo(
      TOP_X[3], "INDICE UV", b, "UV", C_UV
    );
    strcpy(affUV, b);
  }

  // ---- Zone NPK ----
  if (
    tout ||
    valeurN != affN ||
    valeurP != affP ||
    valeurK != affK ||
    npkOK != affNpkOK ||
    etatEngrais != affEtat
  ) {
    dessinerZoneNPK();
    affN = valeurN;
    affP = valeurP;
    affK = valeurK;
    affNpkOK = npkOK;
    affEtat = etatEngrais;
  }

  // ---- Lumiere (tolerance de 10 lux pour eviter le scintillement) ----
  int lux = isnan(lumiere) ? -1 : (int)lumiere;
  if (
    tout ||
    abs(lux - affLux) > 10 ||
    ((lux < 0) != (affLux < 0))
  ) {
    dessinerCarteLumiere();
    affLux = lux;
  }

  // ---- Humidite du sol (tolerance de 2 % contre le bruit de mesure) ----
  if (
    tout ||
    abs(humiditeSol - affSol) >= 2 ||
    solSec != affSolSec
  ) {
    dessinerCarteSol();
    affSol = humiditeSol;
    affSolSec = solSec;
  }

  // ---- Graphique (change toutes les 30 s) ----
  if (tout || grapheModifie) {
    dessinerGraphique();
    grapheModifie = false;
  }

  // ---- Etat du kit ----
  if (
    tout ||
    solSec != affKitSolSec ||
    capteurOK != affKitCapteur ||
    npkOK != affKitNpk
  ) {
    dessinerEtatKit(etatLED);
    affKitSolSec = solSec;
    affKitCapteur = capteurOK;
    affKitNpk = npkOK;
  }
}

// -------------------- INITIALISATION SEN0500 --------------------
bool initSEN0500() {
  return environnement.begin() == 0;
}

// -------------------- LECTURE HUMIDITE SOL --------------------
int lireHumiditeSol() {

  int brut = analogRead(SOIL_PIN);

  if (SOIL_DRY == SOIL_WET) {
    return 0;
  }

  int valeur = map(
    brut,
    SOIL_DRY,
    SOIL_WET,
    0,
    100
  );

  return constrain(valeur, 0, 100);
}

// -------------------- DIRECTION RS485 (mode MANU) --------------------
void npkPreTransmission() {
  digitalWrite(NPK_DE_RE, HIGH);
  delay(2);
}

void npkPostTransmission() {
  delay(2);
  digitalWrite(NPK_DE_RE, LOW);
}

// -------------------- LECTURE NPK --------------------
bool lireNPK() {

  uint8_t resultat =
    npk.readHoldingRegisters(0x1E, 3);

  if (resultat != npk.ku8MBSuccess) {
    Serial.printf(
      "NPK : erreur Modbus 0x%02X\n",
      resultat
    );
    return false;
  }

  valeurN = npk.getResponseBuffer(0);
  valeurP = npk.getResponseBuffer(1);
  valeurK = npk.getResponseBuffer(2);

  return true;
}

// -------------------- CLASSIFICATION ENGRAIS --------------------
EtatEngrais classerEngrais(
  int n,
  int p,
  int k
) {

  if (
    n < N_FAIBLE ||
    p < P_FAIBLE ||
    k < K_FAIBLE
  ) {
    return ENGRAIS_PAUVRE;
  }

  if (
    n >= N_BON &&
    p >= P_BON &&
    k >= K_BON
  ) {
    return ENGRAIS_RICHE;
  }

  return ENGRAIS_CORRECT;
}

// -------------------- LECTURE ENVIRONNEMENT --------------------
void lireCapteursEnvironnement() {

  if (!capteurOK) return;

  temperature =
    environnement.getTemperature(TEMP_C);

  humiditeAir =
    environnement.getHumidity();

  pression =
    environnement.getAtmospherePressure(HPA);

  indiceUV =
    environnement.getUltravioletIntensity();

  lumiere =
    environnement.getLuminousIntensity();

  if (!isfinite(temperature)) {
    temperature = NAN;
  }

  if (!isfinite(humiditeAir)) {
    humiditeAir = NAN;
  }

  if (!isfinite(pression)) {
    pression = NAN;
  }

  if (!isfinite(indiceUV)) {
    indiceUV = NAN;
  }

  if (!isfinite(lumiere)) {
    lumiere = NAN;
  }
}

// -------------------- GESTION ALERTES --------------------
void gererAlerteSonoreEtVisuelle() {

  if (solSec) {

    digitalWrite(LED_OK_PIN, LOW);

    relaisOn();

    if (
      millis() - dernierClignotement >=
      CLIGNOTEMENT_LED
    ) {

      dernierClignotement = millis();

      etatLED = !etatLED;

      digitalWrite(
        LED_PIN,
        etatLED ? HIGH : LOW
      );

      digitalWrite(
        BUZZER_PIN,
        etatLED ? BUZZER_ON : BUZZER_OFF
      );

      clignoterAlertes();
    }
  }

  else {

    digitalWrite(LED_PIN, LOW);
    digitalWrite(BUZZER_PIN, BUZZER_OFF);

    relaisOff();

    digitalWrite(LED_OK_PIN, HIGH);

    etatLED = false;
  }

  if (
    !solSec &&
    npkOK &&
    etatEngrais == ENGRAIS_PAUVRE &&
    millis() - dernierClignotement >= CLIGNOTEMENT_LED
  ) {
    dernierClignotement = millis();
    etatLED = !etatLED;
    dessinerBadgeNPK(etatLED);
  }
}

// -------------------- SETUP --------------------
void setup() {

  Serial.begin(115200);

  delay(800);

  pinMode(SOIL_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(LED_OK_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(LED_OK_PIN, HIGH);
  digitalWrite(BUZZER_PIN, BUZZER_OFF);

  relaisOff();

  analogReadResolution(12);

  Wire.begin(
    I2C_SDA,
    I2C_SCL
  );

  if (!gfx->begin()) {

    Serial.println(
      "ERREUR : initialisation TFT impossible."
    );
  }

  else {

    gfx->setRotation(1);

    gfx->fillScreen(C_BG);

    gfx->setTextColor(C_WHITE);
    gfx->setTextSize(2);
    gfx->setCursor(30, 130);
    gfx->print("SMART AGRI92");

    gfx->setTextSize(1);
    gfx->setCursor(30, 160);
    gfx->print("Demarrage de la station...");
  }

  capteurOK = initSEN0500();

  // NPK : direction RS485 pilotee par D12 (shield en mode MANU)
  pinMode(NPK_DE_RE, OUTPUT);
  digitalWrite(NPK_DE_RE, LOW);   // reception par defaut

  NpkSerial.begin(
    9600,
    SERIAL_8N1,
    NPK_RX_PIN,
    NPK_TX_PIN
  );

  npk.begin(
    0x01,
    NpkSerial
  );

  npk.preTransmission(npkPreTransmission);
  npk.postTransmission(npkPostTransmission);

  humiditeSol = lireHumiditeSol();

  solSec = (
    humiditeSol < SEUIL_SOL_SEC
  );

  Serial.println(
    "SMART AGRI92 V7 - demarrage termine"
  );

  Serial.printf(
    "SEN0500 : %s\n",
    capteurOK ? "OK" : "ABSENT"
  );

  Serial.println(
    "NPK : premiere lecture en attente"
  );

  lireCapteursEnvironnement();

  npkOK = lireNPK();

  if (npkOK) {
    etatEngrais = classerEngrais(
      valeurN,
      valeurP,
      valeurK
    );
  }

  ajouterHistorique();
  derniereHistorique = millis();

  gererAlerteSonoreEtVisuelle();

  // Premier dessin complet (le seul qui efface l'ecran)
  mettreAJourAffichage(true);
}

// -------------------- LOOP --------------------
void loop() {

  unsigned long maintenant = millis();

  // ---- Reconnexion du SEN0500 ----
  if (
    !capteurOK &&
    maintenant - derniereTentativeCapteur >=
    INTERVALLE_RECONNEXION
  ) {

    derniereTentativeCapteur = maintenant;

    capteurOK = initSEN0500();

    if (capteurOK) {

      lireCapteursEnvironnement();

      Serial.println(
        "SEN0500 reconnecte."
      );
    }
  }

  // ---- Lecture des capteurs (toutes les 2 s) ----
  if (
    maintenant - derniereLecture >=
    INTERVALLE_LECTURE
  ) {

    derniereLecture = maintenant;

    humiditeSol = lireHumiditeSol();

    solSec = (
      humiditeSol < SEUIL_SOL_SEC
    );

    lireCapteursEnvironnement();

    Serial.printf(
      "T=%.1f C | Air=%.1f %% | P=%.1f hPa | UV=%.1f | Lumiere=%.0f lux | Sol=%d %%\n",
      temperature,
      humiditeAir,
      pression,
      indiceUV,
      lumiere,
      humiditeSol
    );
  }

  // ---- Point du graphique (toutes les 30 s) ----
  if (
    maintenant - derniereHistorique >=
    INTERVALLE_HISTORIQUE
  ) {

    derniereHistorique = maintenant;

    ajouterHistorique();
  }

  // ---- Lecture NPK ----
  unsigned long intervalleNPK =
    npkOK
    ? INTERVALLE_LECTURE_NPK
    : INTERVALLE_NPK_ERREUR;

  if (
    maintenant - derniereLectureNPK >=
    intervalleNPK
  ) {

    derniereLectureNPK = maintenant;

    npkOK = lireNPK();

    if (npkOK) {

      etatEngrais = classerEngrais(
        valeurN,
        valeurP,
        valeurK
      );

      Serial.printf(
        "NPK : N=%d P=%d K=%d mg/kg\n",
        valeurN,
        valeurP,
        valeurK
      );
    }

    else {

      Serial.println(
        "Erreur de communication avec le capteur NPK."
      );
    }
  }

  gererAlerteSonoreEtVisuelle();

  // Ne redessine que ce qui a change
  mettreAJourAffichage(false);
}