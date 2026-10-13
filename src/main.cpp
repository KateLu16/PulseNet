#include <Arduino.h>
#include <SPI.h>
#include <esp_mac.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "logo.h"

// =====================================================
// DEVICE
//
// All boards run identical code, but the backend requires
// a UNIQUE device_code per device, and the advertised BLE
// name doubles as that code. The name is therefore derived
// from the BT MAC suffix at boot (e.g. PULSENET-B0B2), so
// flashing the same binary to every board still yields a
// distinct identity per device.
// =====================================================

#define DEVICE_NAME_PREFIX "PULSENET"

char deviceName[16] = DEVICE_NAME_PREFIX;

// =====================================================
// TFT - 160x128 LANDSCAPE
// =====================================================

#define TFT_CS    5
#define TFT_DC    2
#define TFT_RST   4

Adafruit_ST7735 tft(TFT_CS, TFT_DC, TFT_RST);

// =====================================================
// UI THEME (mockup: Giao dien quiz TFT PulseNet HCMUTE)
//
// Dark background #0A0A14, blue header #1565D8 with a
// thin cyan divider, dark navy panels #101830, cyan
// accents #4FC3F7 for selection, gold #F5C518 for the
// countdown ring, green/red for success/error.
// =====================================================

#define COL8(r, g, b) \
    ((uint16_t)((((r) & 0xF8) << 8) | (((g) & 0xFC) << 3) | ((b) >> 3)))

const uint16_t COL_BG       = COL8(10, 10, 20);
const uint16_t COL_PANEL    = COL8(16, 24, 48);
const uint16_t COL_PANEL_LT = COL8(22, 50, 74);
const uint16_t COL_HEADER   = COL8(21, 101, 216);
const uint16_t COL_BLUE     = COL8(33, 150, 243);
const uint16_t COL_CYAN     = COL8(79, 195, 247);
const uint16_t COL_GREEN    = COL8(34, 197, 94);
const uint16_t COL_RED      = COL8(229, 57, 53);
const uint16_t COL_GOLD     = COL8(245, 197, 24);
const uint16_t COL_YELLOW   = COL8(255, 215, 0);
const uint16_t COL_GRAY     = COL8(154, 160, 166);
const uint16_t COL_DIM      = COL8(100, 108, 130);
const uint16_t COL_TRACK    = COL8(42, 47, 58);
const uint16_t COL_PINK     = COL8(240, 98, 146);
const uint16_t COL_WHITE    = 0xFFFF;
const uint16_t COL_BLACK    = 0x0000;

#define HDR_H 16

// =====================================================
// QUESTION VIEW (scrollable)
//
// The question screen is one scrollable "document":
//   header 0..16   -> "Q n/total" + clock (+ link icon)
//   viewport 18..110 -> wrapped question text + options
//   footer 112..127 -> key hints, answer chip, OFFLINE,
//                      more-content-above/below arrows
// =====================================================

#define QVIEW_Y0   18
#define QVIEW_Y1   110
#define QVIEW_H    (QVIEW_Y1 - QVIEW_Y0 + 1)
#define QFOOT_Y    112

// Keypad scroll step: ~2 text rows (10px each) per press.
#define SCROLL_STEP_PX 20

// Classic 5x7 GFX font at size 1: every char is 6px wide.
// Line capacity is derived from this metric, never from a
// fixed character count.
#define CHAR_W        6
#define Q_TEXT_X      5
#define Q_TEXT_MAX_PX 150      // 160 - 2*5 margin
#define O_TEXT_X      24
#define O_TEXT_MAX_PX 130      // 24..154, right of the badge

// Document rows (wrapped lines). 400-char questions +
// 4x160-char options wrap to ~57 rows; the budget below has
// headroom, and an overflow marker row is shown if exceeded
// (content is never dropped silently).
#define MAX_DOC_ROWS 66

// Fragmented QUESTION transfer (see gateway send_ack.py):
// QBEGIN announces the total byte count, following writes are
// raw payload appended until the count is reached.
#define FRAG_BUF_SIZE   2048
#define FRAG_TIMEOUT_MS 6000

// =====================================================
// KEYPAD 4x4
// =====================================================

#define ROW1 26
#define ROW2 25
#define ROW3 33
#define ROW4 32

#define COL1 13
#define COL2 12
#define COL3 14
#define COL4 27

const uint8_t rowPins[4] = {
    ROW1, ROW2, ROW3, ROW4
};

const uint8_t colPins[4] = {
    COL1, COL2, COL3, COL4
};

const char keyMap[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}
};

// =====================================================
// STATE MACHINE (Kahoot-style)
// =====================================================
//
// LOGO          -> idle: dark screen, waiting for a session
// LOBBY         -> session pushed: enter ID (open-ended)
// REGISTERING   -> waiting for REGISTER_ACK (spinner)
// JOINED        -> in: joined screen, then quiz info
// WAIT_QUESTION -> answer confirmed / waiting for next
// QUESTION      -> question on screen, A-D to answer
// ANSWER_SENT   -> answer highlighted, waiting for ACK
// RESULT        -> quiz over, showing score

enum DeviceState {
    STATE_LOGO,
    STATE_LOBBY,
    STATE_REGISTERING,
    STATE_JOINED,
    STATE_WAIT_QUESTION,
    STATE_QUESTION,
    STATE_ANSWER_SENT,
    STATE_RESULT
};

volatile DeviceState state = STATE_LOGO;

// Sub-modes of STATE_WAIT_QUESTION.

enum WaitMode {
    WAIT_CONFIRMED,   // "Answer sent!" + your answer
    WAIT_NEXT,        // hourglass, next question
    WAIT_DONE         // all questions answered
};

volatile WaitMode waitMode = WAIT_NEXT;

// Sub-modes of STATE_JOINED.

enum JoinedPhase {
    JOINED_HELLO,     // green check "JOINED!" (2s)
    JOINED_INFO       // quiz information list
};

volatile JoinedPhase joinedPhase = JOINED_INFO;

// =====================================================
// DATA
// =====================================================

String studentID = "";

const size_t MAX_ID_LENGTH = 12;

// Session info from QUIZ_INFO.

String quizTitle = "";
int quizTotal = 0;
int quizTimeLimitSec = 0;
int quizExpected = 0;
String idPrefix = "";
int idLength = 0;

// Current question.

String currentQuestionID = "";
int currentQuestionNumber = 0;
int questionTotal = 0;
String qText = "";
String qA = "";
String qB = "";
String qC = "";
String qD = "";

// Scrollable question document (built from qText/qA..qD).

enum DocRowKind : uint8_t {
    ROW_QTEXT,      // question text line          (10px)
    ROW_GAP,        // vertical spacing            (8px)
    ROW_OPT_HEAD,   // option first line: badge+text (15px)
    ROW_OPT_CONT,   // option continuation line    (10px)
    ROW_MARK        // visible overflow marker     (10px)
};

struct DocRow {
    uint8_t kind;
    uint8_t opt;    // 0..3 for option rows, 255 otherwise
    String text;
};

DocRow docRows[MAX_DOC_ROWS];
int docRowCount = 0;
bool docOverflow = false;
int docHeightPx = 0;
int scrollPx = 0;
int maxScrollPx = 0;
bool questionDocReady = false;

// Fragmented QUESTION transfer state (BLE callback side).

volatile bool questionReceiving = false;
volatile bool pendingQBegin = false;
bool showingReceiving = false;
volatile unsigned long fragStartedAt = 0;
int fragExpectedBytes = 0;
String fragBuf = "";

// Whole-quiz countdown.

unsigned long quizDeadline = 0;
bool quizDeadlineSet = false;
bool quizRunning = false;
bool quizEnded = false;
unsigned long lastClockPaint = 0;

// Lobby entry window (open until the teacher starts).

bool entryOpen = false;

// Score tracking (correct answers come from ANSWER_ACK).

int answeredCount = 0;
int correctCount = 0;

// Count each question at most once: a late ACK (after the
// 5s timeout put us back on the question screen), a
// re-answer, or a duplicate ACK for the same question must
// not inflate the counters.

String lastCountedQuestionID = "";
bool lastCountedCorrect = false;

// quiz_id of the session loaded from QUIZ_INFO. A running
// QUIZ_INFO with a DIFFERENT quiz_id starts a fresh session
// (score + countdown reset) even if the old one was never
// properly finished on screen.

int activeQuizID = 0;

// Timeouts for missing ACKs.

unsigned long registerSentAt = 0;
unsigned long answerSentAt = 0;

// Answer sequencing + retry.
//
// Every answering attempt gets a rising `sequence` number.
// Automatic retries of the same attempt (ACK lost over BLE)
// REUSE the number, so the backend can tell a retry apart
// from a later re-answer:
//
//   same sequence   -> duplicate delivery, keep stored answer
//   higher sequence -> newer attempt, overwrites the old one
//   lower sequence  -> stale delayed packet, ignored
//
// The counter never resets, so it also orders attempts across
// questions for the whole session.

uint32_t answerSeq = 0;
uint8_t answerAttempts = 0;
const uint8_t MAX_ANSWER_ATTEMPTS = 3;

// UI bookkeeping.

char lastAnswerChoice = '-';
unsigned long waitConfirmedAt = 0;
unsigned long joinedShownAt = 0;
bool idCursorOn = true;
volatile bool bleLinkLost = false;

volatile bool gatewayConnected = false;

// =====================================================
// PENDING BLE EVENTS
// =====================================================

volatile bool pendingQuestion = false;
volatile bool pendingAck = false;
volatile bool pendingQuizInfo = false;
volatile bool pendingQuizEnd = false;
volatile bool pendingBleLost = false;

String ackType = "";
String ackQuestionID = "";
String ackStatus = "";
String ackReason = "";
bool ackCorrect = false;

String newQuizTitle = "";
int newQuizID = 0;
int newQuizTotal = 0;
int newQuizTimeLimit = 0;
bool newQuizRunning = false;
bool newQuizLobby = false;
int newQuizExpected = 0;
String newQuizPrefix = "";
int newQuizIdLength = 0;

// =====================================================
// BLE UUID
// =====================================================

#define PULSENET_SERVICE_UUID \
    "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"

#define REGISTRATION_CHAR_UUID \
    "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

#define QUESTION_CHAR_UUID \
    "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

#define ANSWER_CHAR_UUID \
    "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"

#define ACK_CHAR_UUID \
    "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"

// =====================================================
// BLE OBJECTS
// =====================================================

BLEServer* bleServer = nullptr;

BLECharacteristic* registrationCharacteristic = nullptr;
BLECharacteristic* questionCharacteristic = nullptr;
BLECharacteristic* answerCharacteristic = nullptr;
BLECharacteristic* ackCharacteristic = nullptr;

volatile bool deviceConnected = false;

// =====================================================
// JSON FIELD HELPERS
// =====================================================

String jsonGetString(
    const String& packet,
    const char* key
)
{
    String pattern = "\"" + String(key) + "\":\"";

    int start = packet.indexOf(pattern);

    if (start < 0)
    {
        return "";
    }

    start += pattern.length();

    // The value may contain escaped quotes (\"), so skip
    // backslash-escaped characters while searching for the
    // real closing quote.
    int end = start;
    int n = (int)packet.length();

    while (end < n)
    {
        char c = packet.charAt(end);

        if (c == '\\' && end + 1 < n)
        {
            end += 2;
            continue;
        }

        if (c == '"')
        {
            break;
        }

        end++;
    }

    if (end <= start || end > n)
    {
        return "";
    }

    // Decode the escapes json.dumps can produce in question
    // text: \" \\ \n \t \r. \uXXXX is NOT decoded — the
    // gateway transliterates non-ASCII to plain ASCII before
    // sending (the classic GFX font has no Vietnamese
    // glyphs).
    String out = "";

    out.reserve(end - start);

    for (int i = start; i < end; i++)
    {
        char c = packet.charAt(i);

        if (c == '\\' && i + 1 < end)
        {
            char e = packet.charAt(i + 1);

            if (e == 'n')
            {
                out += '\n';
            }
            else if (e == 't')
            {
                out += '\t';
            }
            else if (e == 'r')
            {
                out += '\r';
            }
            else
            {
                out += e;
            }

            i++;
        }
        else
        {
            out += c;
        }
    }

    return out;
}

long jsonGetInt(
    const String& packet,
    const char* key
)
{
    String pattern = "\"" + String(key) + "\":";

    int start = packet.indexOf(pattern);

    if (start < 0)
    {
        return 0;
    }

    start += pattern.length();

    int end = start;

    while (end < (int)packet.length())
    {
        char c = packet.charAt(end);

        if (c < '0' || c > '9')
        {
            break;
        }

        end++;
    }

    if (end == start)
    {
        return 0;
    }

    return packet.substring(start, end).toInt();
}

// JSON booleans are serialized UNQUOTED:
//
//     "correct":true
//
// jsonGetString cannot read them (it requires an opening
// quote after the colon), so match the raw pattern instead.
bool jsonGetBool(
    const String& packet,
    const char* key
)
{
    String pattern =
        "\"" + String(key) + "\":true";

    return packet.indexOf(pattern) >= 0;
}

// =====================================================
// FORWARD DECLARATIONS
// =====================================================

void drawSplashScreen();
void drawIdleWaitScreen();
void drawLobbyEntry();
void updateIdBox(bool cursorOn);
void drawConnectingScreen();
void drawJoinedScreen();
void drawQuizInfoScreen();
void runStartCountdown();
void drawQuestionScreen();
void buildQuestionDoc();
void renderQuestionContent();
void renderQuestionFooter();
void drawReceivingScreen();
void applyQuestionPacket(const String& packet);
void drawSendingAnswerScreen();
void drawAnswerConfirmedScreen();
void drawNextQuestionScreen();
void drawWaitDoneScreen();
void drawTimeUpScreen();
void drawConnectionLostScreen();
void drawResultScreen();
void showResultScreen();
void displayMessage(
    const char* title,
    uint16_t titleColor,
    const String& line1,
    const String& line2
);
void drawQuizClock(bool force);
void redrawWaitScreen();
bool allQuestionsAnswered();

// =====================================================
// BLE SERVER CALLBACK
// =====================================================

class ServerCallbacks : public BLEServerCallbacks
{
    void onConnect(BLEServer* server) override
    {
        deviceConnected = true;

        Serial.println("BLE GATEWAY CONNECTED");
    }

    void onDisconnect(BLEServer* server) override
    {
        deviceConnected = false;
        gatewayConnected = false;
        bleLinkLost = true;

        // Screen updates happen in loop() so the TFT is
        // never touched from the BLE task.
        pendingBleLost = true;

        Serial.println("BLE GATEWAY DISCONNECTED");

        delay(100);

        BLEDevice::startAdvertising();

        Serial.println("BLE advertising restarted.");
    }
};

// =====================================================
// ACK / QUIZ_INFO / QUIZ_END CALLBACK
// =====================================================

class ACKCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic* characteristic) override
    {
        String value = characteristic->getValue().c_str();

        Serial.println();
        Serial.println("========== BLE RX ==========");
        Serial.println(value);
        Serial.println("============================");

        String type = jsonGetString(value, "type");

        if (type == "QUIZ_INFO")
        {
            newQuizID = jsonGetInt(value, "quiz_id");
            newQuizTitle = jsonGetString(value, "title");
            newQuizTotal = jsonGetInt(value, "total");
            newQuizTimeLimit = jsonGetInt(value, "time_limit");
            newQuizExpected = jsonGetInt(value, "expected");
            newQuizPrefix = jsonGetString(value, "prefix");
            newQuizIdLength = jsonGetInt(value, "id_length");

            String st = jsonGetString(value, "status");
            newQuizRunning = (st == "running");
            newQuizLobby = (st == "lobby");

            pendingQuizInfo = true;
        }
        else if (type == "QUIZ_END")
        {
            pendingQuizEnd = true;
        }
        else
        {
            ackType = type;
            ackQuestionID =
                jsonGetString(value, "question_id");
            ackStatus = jsonGetString(value, "status");
            ackReason = jsonGetString(value, "reason");
            ackCorrect =
                jsonGetBool(value, "correct");

            pendingAck = true;
        }
    }
};

// =====================================================
// QUESTION PACKET PARSER
// (shared by the single-shot and fragmented paths)
// =====================================================

void applyQuestionPacket(const String& packet)
{
    currentQuestionID =
        jsonGetString(packet, "question_id");

    long number = jsonGetInt(packet, "number");
    long total = jsonGetInt(packet, "total");

    if (number > 0)
    {
        currentQuestionNumber = (int)number;
    }
    else if (currentQuestionID.length() > 0)
    {
        currentQuestionNumber =
            currentQuestionID.substring(1).toInt();
    }

    if (total > 0)
    {
        questionTotal = (int)total;
    }

    qText = jsonGetString(packet, "question");
    qA = jsonGetString(packet, "A");
    qB = jsonGetString(packet, "B");
    qC = jsonGetString(packet, "C");
    qD = jsonGetString(packet, "D");

    if (currentQuestionID.length() == 0)
    {
        return;
    }

    pendingQuestion = true;
}

// =====================================================
// QUESTION CALLBACK
//
// Long questions arrive fragmented (a single BLE write is
// capped by the negotiated MTU):
//
//   {"type":"QBEGIN","bytes":512,"chunks":3}   -> begin
//   <raw chunk 1> ... <raw chunk N>            -> append
//
// The chunks concatenated equal the full QUESTION JSON; the
// transfer self-completes when the announced byte count is
// reached, and a timeout abandons a stalled transfer (the
// gateway re-pushes the question after a reconnect).
// =====================================================

class QuestionCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic* characteristic) override
    {
        String packet = characteristic->getValue().c_str();

        Serial.println();
        Serial.println("========== QUESTION ==========");
        Serial.println(packet);
        Serial.println("==============================");

        if (questionReceiving)
        {
            if ((int)(fragBuf.length() + packet.length()) >
                FRAG_BUF_SIZE)
            {
                Serial.println(
                    "[QFRAG] Buffer overflow - dropped."
                );

                questionReceiving = false;
                fragBuf = "";

                return;
            }

            fragBuf += packet;

            if ((int)fragBuf.length() >= fragExpectedBytes)
            {
                String whole = fragBuf;

                questionReceiving = false;
                fragBuf = "";

                Serial.println(
                    "[QFRAG] Transfer complete - parsing."
                );

                applyQuestionPacket(whole);
            }

            return;
        }

        if (jsonGetString(packet, "type") == "QBEGIN")
        {
            long bytes = jsonGetInt(packet, "bytes");

            if (bytes <= 0 || bytes > FRAG_BUF_SIZE)
            {
                Serial.println(
                    "[QFRAG] Invalid QBEGIN - ignored."
                );

                return;
            }

            fragBuf = "";
            fragExpectedBytes = (int)bytes;
            fragStartedAt = millis();
            questionReceiving = true;
            pendingQBegin = true;

            Serial.print("[QFRAG] Expecting ");
            Serial.print(bytes);
            Serial.println(" bytes.");

            return;
        }

        applyQuestionPacket(packet);
    }
};

// =====================================================
// READ KEYPAD
// =====================================================

char readKeypad()
{
    for (int row = 0; row < 4; row++)
    {
        for (int i = 0; i < 4; i++)
        {
            digitalWrite(rowPins[i], HIGH);
        }

        digitalWrite(rowPins[row], LOW);

        for (int col = 0; col < 4; col++)
        {
            if (digitalRead(colPins[col]) == LOW)
            {
                delay(20);

                if (digitalRead(colPins[col]) != LOW)
                {
                    continue;
                }

                while (digitalRead(colPins[col]) == LOW)
                {
                    delay(1);
                }

                return keyMap[row][col];
            }
        }
    }

    return '\0';
}

// =====================================================
// TEXT HELPERS
// =====================================================

void printCentered(
    const char* text,
    int y,
    uint8_t size,
    uint16_t color
)
{
    tft.setTextSize(size);
    tft.setTextColor(color);

    int w = strlen(text) * 6 * size;

    int x = (160 - w) / 2;

    if (x < 0)
    {
        x = 0;
    }

    tft.setCursor(x, y);
    tft.print(text);
}

// Big title: size 2 when it fits, size 1 otherwise.
void drawTitleAuto(
    const char* text,
    int y,
    uint16_t color
)
{
    uint8_t size =
        ((int)strlen(text) * 12 <= 152) ? 2 : 1;

    printCentered(text, y, size, color);
}

void drawWrappedCentered(
    const String& text,
    int y,
    int maxCharsPerLine,
    uint16_t color,
    int maxLines = 3
)
{
    String remaining = text;

    int lines = 0;

    while (remaining.length() > 0 && lines < maxLines)
    {
        int lineLength = maxCharsPerLine;

        if ((int)remaining.length() < lineLength)
        {
            lineLength = remaining.length();
        }

        if (lineLength < (int)remaining.length())
        {
            int spacePos =
                remaining.lastIndexOf(' ', lineLength);

            if (spacePos > 0)
            {
                lineLength = spacePos;
            }
        }

        String line =
            remaining.substring(0, lineLength);

        line.trim();

        printCentered(line.c_str(), y, 1, color);

        remaining = remaining.substring(lineLength);

        remaining.trim();

        y += 11;

        lines++;
    }
}

// =====================================================
// ICON HELPERS
// =====================================================

// Arc segment used by rings and spinners. Angles in
// degrees, 0 = right, growing clockwise on screen.
void drawRingArc(
    int cx,
    int cy,
    int r,
    int startDeg,
    int spanDeg,
    uint16_t color
)
{
    int px = 0;
    int py = 0;

    for (int a = startDeg; a <= startDeg + spanDeg; a += 5)
    {
        float rad = a * 3.14159f / 180.0f;

        int x = cx + (int)(r * cos(rad) + 0.5f);
        int y = cy + (int)(r * sin(rad) + 0.5f);

        if (a > startDeg)
        {
            tft.drawLine(px, py, x, y, color);
        }

        px = x;
        py = y;
    }
}

// One wave stroke of the signal icon, drawn on both sides
// of the center: an arc bulging outward and spanning about
// +/-50 degrees around the horizontal. Multiple stroke
// passes fatten the line like the reference icon.
void drawWaveArcPair(
    int cx,
    int cy,
    int r,
    int stroke,
    uint16_t color
)
{
    for (int side = -1; side <= 1; side += 2)
    {
        for (int s = 0; s < stroke; s++)
        {
            int rr = r - s;

            int px = 0;
            int py = 0;

            for (int a = -50; a <= 50; a += 5)
            {
                float rad = a * 3.14159f / 180.0f;

                int x = cx + side *
                    (int)(rr * cos(rad) + 0.5f);

                int y = cy -
                    (int)(rr * sin(rad) + 0.5f);

                if (a > -50)
                {
                    tft.drawLine(px, py, x, y, color);
                }

                px = x;
                py = y;
            }
        }
    }
}

// Signal-wave status icon: a center dot with two nested
// waves on each side. off = true adds the diagonal slash
// (bottom-left up to top-right) that marks a lost link.
void drawSignalWaves(
    int cx,
    int cy,
    int outerR,
    uint16_t color,
    bool off
)
{
    int innerR = (2 * outerR + 1) / 3;
    int dotR = (outerR + 1) / 3;
    int stroke = outerR >= 10 ? 2 : 1;

    tft.fillCircle(cx, cy, dotR, color);

    drawWaveArcPair(cx, cy, innerR, stroke, color);
    drawWaveArcPair(cx, cy, outerR, stroke, color);

    if (off)
    {
        int v = (outerR * 77 + 50) / 100;

        tft.drawLine(
            cx - outerR, cy + v,
            cx + outerR, cy - v,
            color
        );

        if (stroke > 1)
        {
            tft.drawLine(
                cx - outerR, cy + v + 1,
                cx + outerR, cy - v + 1,
                color
            );
        }
    }
}

// One frame of the loading spinner. The track circles
// fully cover the previous frame's arc.
void drawSpinnerFrame(
    int cx,
    int cy,
    int r,
    int angleDeg
)
{
    tft.drawCircle(cx, cy, r, COL_TRACK);
    tft.drawCircle(cx, cy, r - 1, COL_TRACK);

    drawRingArc(cx, cy, r, angleDeg, 90, COL_BLUE);
    drawRingArc(cx, cy, r - 1, angleDeg, 90, COL_BLUE);
}

void drawCheckCircle(
    int cx,
    int cy,
    int r,
    uint16_t color
)
{
    tft.fillCircle(cx, cy, r, color);

    for (int i = 0; i < 3; i++)
    {
        tft.drawLine(
            cx - r / 2 - 1 + i, cy + 1,
            cx - 3 + i, cy + r / 2,
            COL_WHITE
        );

        tft.drawLine(
            cx - 3 + i, cy + r / 2,
            cx + r / 2 + 1 + i, cy - r / 2,
            COL_WHITE
        );
    }
}

void drawExclaimCircle(
    int cx,
    int cy,
    int r,
    uint16_t color
)
{
    tft.fillCircle(cx, cy, r, color);

    tft.fillRect(cx - 2, cy - r + 4, 4, r - 5, COL_WHITE);
    tft.fillRect(cx - 2, cy + 3, 4, 4, COL_WHITE);
}

void drawClockSmallIcon(int cx, int cy, uint16_t color)
{
    tft.drawCircle(cx, cy, 4, color);

    tft.drawLine(cx, cy, cx, cy - 3, color);
    tft.drawLine(cx, cy, cx + 2, cy + 1, color);
}

void drawClockBig(int cx, int cy, int r, uint16_t color)
{
    tft.drawCircle(cx, cy, r, color);
    tft.drawCircle(cx, cy, r - 1, color);

    tft.drawLine(cx, cy, cx, cy - r + 4, color);
    tft.drawLine(cx, cy, cx, cy - r + 5, color);
    tft.drawLine(cx, cy, cx + r - 5, cy + 2, color);
    tft.drawLine(cx, cy, cx + r - 6, cy + 2, color);
}

void drawWifiLost(int cx, int cy)
{
    drawSignalWaves(cx, cy, 13, COL_WHITE, true);
}

void drawHourglass(int cx, int cy)
{
    tft.drawTriangle(
        cx - 11, cy - 13, cx + 11, cy - 13, cx, cy - 1,
        COL_BLUE
    );

    tft.drawTriangle(
        cx - 11, cy + 13, cx + 11, cy + 13, cx, cy + 1,
        COL_BLUE
    );

    tft.fillTriangle(
        cx - 4, cy - 11, cx + 4, cy - 11, cx, cy - 4,
        COL_GOLD
    );

    tft.fillTriangle(
        cx - 6, cy + 11, cx + 6, cy + 11, cx, cy + 5,
        COL_GOLD
    );
}

void drawPaperPlane(int cx, int cy)
{
    tft.fillCircle(cx, cy, 16, COL_PANEL);

    tft.fillTriangle(
        cx - 8, cy + 8, cx + 9, cy - 9, cx + 9, cy - 3,
        COL_WHITE
    );

    tft.fillTriangle(
        cx - 8, cy + 8, cx + 9, cy - 3, cx - 1, cy + 1,
        COL_CYAN
    );
}

void drawTrophy(int cx, int cy)
{
    tft.fillCircle(cx, cy, 17, COL_GOLD);

    // Trophy silhouette in dark on the gold circle.

    tft.fillRoundRect(cx - 8, cy - 11, 16, 10, 2, COL_BG);

    tft.drawCircle(cx - 11, cy - 6, 3, COL_BG);
    tft.drawCircle(cx + 11, cy - 6, 3, COL_BG);

    tft.fillRect(cx - 1, cy - 1, 3, 6, COL_BG);
    tft.fillRect(cx - 6, cy + 5, 13, 3, COL_BG);

    // Confetti.

    tft.fillCircle(cx - 26, cy - 14, 1, COL_CYAN);
    tft.fillCircle(cx + 24, cy - 10, 1, COL_PINK);
    tft.fillCircle(cx - 30, cy + 8, 1, COL_GREEN);
    tft.fillCircle(cx + 28, cy + 10, 1, COL_YELLOW);
    tft.fillCircle(cx - 20, cy + 16, 1, COL_RED);
    tft.fillCircle(cx + 20, cy - 18, 1, COL_CYAN);
    tft.fillCircle(cx, cy - 22, 1, COL_PINK);
    tft.fillCircle(cx - 14, cy - 20, 1, COL_YELLOW);
}

void drawTeacherIcon(int cx, int cy)
{
    // Board.

    tft.drawRoundRect(cx - 24, cy - 14, 48, 32, 4, COL_GOLD);
    tft.drawRoundRect(cx - 23, cy - 13, 46, 30, 3, COL_GOLD);

    // Person.

    tft.fillCircle(cx, cy - 3, 5, COL_WHITE);

    tft.fillRoundRect(cx - 9, cy + 4, 18, 11, 4, COL_WHITE);
}

void drawDocIcon(int x, int y, uint16_t color)
{
    tft.drawRect(x, y, 10, 12, color);

    for (int i = 0; i < 3; i++)
    {
        tft.drawFastHLine(x + 2, y + 3 + i * 3, 6, color);
    }
}

void drawMiniClockIcon(int x, int y, uint16_t color)
{
    tft.drawCircle(x + 5, y + 5, 5, color);

    tft.drawLine(x + 5, y + 5, x + 5, y + 1, color);
    tft.drawLine(x + 5, y + 5, x + 8, y + 6, color);
}

void drawPeopleIcon(int x, int y, uint16_t color)
{
    tft.fillCircle(x + 3, y + 3, 3, color);
    tft.fillCircle(x + 11, y + 4, 2, COL_DIM);

    tft.fillRoundRect(x - 1, y + 7, 9, 6, 3, color);
    tft.fillRoundRect(x + 8, y + 7, 7, 6, 3, COL_DIM);
}

// =====================================================
// SHARED CHROME
// =====================================================

// Blue app bar with white title and a BLE status icon.
void drawAppHeader(const char* title)
{
    tft.fillRect(0, 0, 160, HDR_H, COL_HEADER);
    tft.drawFastHLine(0, HDR_H, 160, COL_CYAN);

    tft.setTextSize(1);
    tft.setTextColor(COL_WHITE);
    tft.setCursor(5, 4);
    tft.print(title);

    // Plain waves while linked, slashed waves while down.
    // cy = 10 keeps the whole glyph inside the 16px header.
    drawSignalWaves(
        147, 10, 7, COL_WHITE, !gatewayConnected
    );
}

// Dark header of the question screen: "Q n/total" left,
// clock icon + remaining time right (painted by
// drawQuizClock).
void drawQuestionHeader()
{
    tft.fillRect(0, 0, 160, HDR_H, COL_PANEL);
    tft.drawFastHLine(0, HDR_H, 160, COL_CYAN);

    char buf[24];

    if (questionTotal > 0)
    {
        snprintf(
            buf, sizeof(buf), "Q %d/%d",
            currentQuestionNumber, questionTotal
        );
    }
    else
    {
        snprintf(
            buf, sizeof(buf), "Q %s",
            currentQuestionID.c_str()
        );
    }

    tft.setTextSize(1);
    tft.setTextColor(COL_WHITE);
    tft.setCursor(5, 4);
    tft.print(buf);

    // Link status where space permits: the slashed icon only
    // appears while the gateway link is DOWN (the question
    // number and clock already crowd this 16px bar).
    if (!gatewayConnected)
    {
        drawSignalWaves(108, 9, 6, COL_RED, true);
    }
}

void drawButton(
    int x,
    int y,
    int w,
    int h,
    uint16_t color,
    const char* label
)
{
    tft.fillRoundRect(x, y, w, h, 5, COL_PANEL);

    tft.drawRoundRect(x, y, w, h, 5, color);
    tft.drawRoundRect(x + 1, y + 1, w - 2, h - 2, 4, color);

    printCentered(label, y + (h - 8) / 2, 1, color);
}

// =====================================================
// QUIZ CLOCK (question screen header)
// =====================================================

int clockRemainingSec()
{
    if (!quizDeadlineSet)
    {
        return -1;
    }

    long remainingMs =
        (long)quizDeadline - (long)millis();

    return remainingMs > 0 ? (int)(remainingMs / 1000) : 0;
}

void drawQuizClock(bool force)
{
    if (!quizDeadlineSet)
    {
        return;
    }

    unsigned long now = millis();

    if (!force && now - lastClockPaint < 250)
    {
        return;
    }

    lastClockPaint = now;

    // The clock only lives on the question screen; expiry
    // itself is checked in loop() on every state.
    if (state != STATE_QUESTION && !force)
    {
        return;
    }

    int remaining = clockRemainingSec();

    char buf[8];

    snprintf(
        buf,
        sizeof(buf),
        "%02d:%02d",
        remaining / 60,
        remaining % 60
    );

    tft.fillRect(116, 0, 44, HDR_H, COL_PANEL);

    drawClockSmallIcon(122, 8, COL_GRAY);

    tft.setTextSize(1);

    tft.setTextColor(
        remaining <= 10 ? COL_RED : COL_YELLOW
    );

    tft.setCursor(128, 4);
    tft.print(buf);
}

// =====================================================
// SCREEN 1: SPLASH (boot only)
// =====================================================

void drawSplashScreen()
{
    // Full-screen HCMUTE logo (white background, purple
    // stroke) with a bottom strip reserved for text.
    tft.drawRGBBitmap(
        0,
        0,
        LOGO_HCMUTE,
        LOGO_WIDTH,
        LOGO_HEIGHT
    );

    tft.fillRect(0, 96, 160, 32, ST77XX_WHITE);

    // Loading bar: gray track + blue fill.
    tft.fillRoundRect(30, 104, 100, 8, 4, COL_TRACK);

    for (int p = 0; p <= 100; p += 4)
    {
        int w = 96 * p / 100;

        if (w < 4)
        {
            w = 4;
        }

        tft.fillRoundRect(32, 106, w, 4, 2, COL_HEADER);

        delay(22);
    }

    printCentered(
        "Waiting for teacher...",
        118,
        1,
        ST77XX_BLACK
    );

    delay(800);
}

// =====================================================
// SCREEN 15: IDLE - WAITING FOR TEACHER
// =====================================================

void drawIdleWaitScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawTeacherIcon(80, 40);

    drawTitleAuto("Waiting for teacher...", 68, COL_WHITE);

    drawWrappedCentered(
        "The quiz has not been started yet.",
        88,
        26,
        COL_GRAY,
        2
    );

    lastClockPaint = 0;
}

// =====================================================
// SCREEN 2: ENTER STUDENT ID
// =====================================================

void drawLobbyEntry()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("Enter Student ID");

    // ID box: yellow border, dark panel.
    tft.fillRoundRect(10, 24, 140, 30, 5, COL_BG);
    tft.drawRoundRect(10, 24, 140, 30, 5, COL_YELLOW);

    tft.fillRoundRect(12, 26, 136, 26, 4, COL_PANEL);

    // Legend panel.
    tft.fillRoundRect(10, 62, 140, 46, 5, COL_PANEL);

    const char* keys[3] = {"0-9", "*", "#"};
    const char* actions[3] =
        {"Input number", "Clear", "Confirm"};

    for (int i = 0; i < 3; i++)
    {
        int y = 70 + i * 12;

        tft.setTextSize(1);
        tft.setTextColor(COL_CYAN);
        tft.setCursor(24, y);
        tft.print(keys[i]);

        tft.setTextColor(COL_WHITE);
        tft.setCursor(54, y);
        tft.print(actions[i]);
    }

    idCursorOn = true;

    updateIdBox(true);
}

void updateIdBox(bool cursorOn)
{
    tft.fillRoundRect(14, 28, 132, 22, 4, COL_PANEL);

    int len = studentID.length();

    int size = len <= 9 ? 2 : 1;

    int charW = 6 * size;

    int textW = len * charW + (cursorOn ? charW : 0);

    int x = 16 + (128 - textW) / 2;

    if (x < 16)
    {
        x = 16;
    }

    tft.setTextSize(size);
    tft.setTextColor(COL_YELLOW);
    tft.setCursor(x, size == 2 ? 31 : 35);
    tft.print(studentID);

    if (cursorOn)
    {
        tft.print("_");
    }
}

// =====================================================
// SCREEN 3: CONNECTING (spinner animated in loop)
// =====================================================

void drawConnectingScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawSpinnerFrame(80, 46, 14, 0);

    drawTitleAuto("Joining...", 70, COL_WHITE);

    drawWrappedCentered(
        "Sending your information to the server.",
        94,
        24,
        COL_GRAY,
        2
    );
}

// =====================================================
// SCREEN 4: JOINED
// =====================================================

void drawJoinedScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawCheckCircle(80, 34, 16, COL_GREEN);

    printCentered("JOINED!", 58, 2, COL_GREEN);

    String idLine = "ID: " + studentID;

    printCentered(idLine.c_str(), 80, 1, COL_WHITE);

    tft.fillRoundRect(15, 94, 130, 26, 5, COL_PANEL);

    printCentered("Ready for quiz", 99, 1, COL_WHITE);
    printCentered("Please wait...", 109, 1, COL_GRAY);
}

// =====================================================
// SCREEN 5: QUIZ INFORMATION
// =====================================================

void drawQuizInfoScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    printCentered("Quiz Information", 22, 1, COL_GOLD);

    if (quizTitle.length() > 0)
    {
        drawWrappedCentered(quizTitle, 34, 26, COL_CYAN, 2);
    }

    tft.fillRoundRect(12, 54, 136, 42, 5, COL_PANEL);

    int y = 60;

    char buf[24];

    if (quizTotal > 0)
    {
        snprintf(buf, sizeof(buf), "%d questions", quizTotal);

        drawDocIcon(24, y, COL_CYAN);

        tft.setTextSize(1);
        tft.setTextColor(COL_WHITE);
        tft.setCursor(42, y + 2);
        tft.print(buf);

        y += 12;
    }

    if (quizTimeLimitSec > 0)
    {
        snprintf(
            buf, sizeof(buf), "%d minutes",
            quizTimeLimitSec / 60 > 0
                ? quizTimeLimitSec / 60
                : quizTimeLimitSec
        );

        drawMiniClockIcon(24, y, COL_CYAN);

        tft.setTextSize(1);
        tft.setTextColor(COL_WHITE);
        tft.setCursor(42, y + 2);
        tft.print(buf);

        y += 12;
    }

    drawPeopleIcon(24, y, COL_CYAN);

    tft.setTextSize(1);
    tft.setTextColor(COL_WHITE);
    tft.setCursor(42, y + 2);
    tft.print("Please get ready!");

    drawButton(
        25, 102, 110, 18, COL_CYAN, "Waiting to start..."
    );
}

// =====================================================
// SCREEN 6: COUNTDOWN (quiz starting)
// =====================================================

void drawCountdownFrame(int secondsLeft)
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    printCentered("Quiz will start in", 22, 1, COL_WHITE);

    // Progress ring: the gold arc grows as time passes.
    tft.drawCircle(80, 62, 22, COL_TRACK);
    tft.drawCircle(80, 62, 21, COL_TRACK);

    int span = (6 - secondsLeft) * 72;

    if (span > 0)
    {
        drawRingArc(80, 62, 22, -90, span, COL_GOLD);
        drawRingArc(80, 62, 21, -90, span, COL_GOLD);
    }

    tft.setTextSize(3);
    tft.setTextColor(COL_WHITE);
    tft.setCursor(71, 50);
    tft.print(secondsLeft);

    printCentered("Get ready!", 98, 1, COL_GOLD);
}

void runStartCountdown()
{
    for (int s = 5; s >= 1; s--)
    {
        drawCountdownFrame(s);

        unsigned long t0 = millis();

        // Cut the countdown short if a question or a
        // session update already arrived.
        while (millis() - t0 < 1000)
        {
            if (pendingQuestion ||
                pendingQuizInfo ||
                pendingQuizEnd)
            {
                return;
            }

            delay(20);
        }
    }
}

// =====================================================
// SCREEN 7: QUESTION (scrollable document)
// =====================================================

int docRowHeight(uint8_t kind)
{
    switch (kind)
    {
        case ROW_OPT_HEAD: return 15;
        case ROW_GAP:      return 8;
        default:           return 10;
    }
}

void appendDocRow(uint8_t kind, uint8_t opt, const String& text)
{
    if (docRowCount >= MAX_DOC_ROWS)
    {
        docOverflow = true;
        return;
    }

    DocRow& row = docRows[docRowCount++];

    row.kind = kind;
    row.opt = opt;
    row.text = text;
}

// Word-wrap `text` into document rows at most maxPx wide.
// Breaks at spaces, honors hard '\n' from the teacher's
// input, and splits any word longer than a full line (never
// loops forever). opt == 255 wraps question text; otherwise
// the first wrapped line becomes the option's badge row.
void appendWrapped(const String& text, int maxPx, uint8_t opt)
{
    int maxChars = maxPx / CHAR_W;

    if (maxChars < 1)
    {
        maxChars = 1;
    }

    int i = 0;
    int n = (int)text.length();
    bool first = true;

    while (i < n)
    {
        int end = i;
        int hardBreak = -1;

        while (end < n && (end - i) < maxChars)
        {
            char c = text.charAt(end);

            if (c == '\n')
            {
                hardBreak = end;
                break;
            }

            end++;
        }

        String line;
        int next;

        if (hardBreak >= 0)
        {
            line = text.substring(i, hardBreak);
            next = hardBreak + 1;
        }
        else if (end >= n)
        {
            line = text.substring(i, n);
            next = n;
        }
        else
        {
            int sp = text.lastIndexOf(' ', end - 1);

            if (sp >= i)
            {
                line = text.substring(i, sp);
                next = sp + 1;
            }
            else if (text.charAt(end) == ' ')
            {
                line = text.substring(i, end);
                next = end + 1;
            }
            else
            {
                // Inside a word longer than one line: split it.
                line = text.substring(i, end);
                next = end;
            }
        }

        while (line.length() > 0 && line.charAt(0) == ' ')
        {
            line.remove(0, 1);
        }

        if (line.length() > 0)
        {
            if (opt == 255)
            {
                appendDocRow(ROW_QTEXT, 255, line);
            }
            else
            {
                appendDocRow(
                    first ? ROW_OPT_HEAD : ROW_OPT_CONT,
                    opt,
                    line
                );
            }

            first = false;
        }

        i = next;
    }
}

// Turn the current qText/qA..qD into scrollable rows. All
// received text is preserved — nothing is truncated to fit
// the screen; extra content is reached by scrolling.
void buildQuestionDoc()
{
    docRowCount = 0;
    docOverflow = false;
    scrollPx = 0;

    if (qText.length() == 0 &&
        qA.length() == 0 &&
        qB.length() == 0 &&
        qC.length() == 0 &&
        qD.length() == 0)
    {
        questionDocReady = false;
        docHeightPx = 0;
        maxScrollPx = 0;
        return;
    }

    appendWrapped(qText, Q_TEXT_MAX_PX, 255);

    appendDocRow(ROW_GAP, 255, "");

    const String options[4] = {qA, qB, qC, qD};

    for (int i = 0; i < 4; i++)
    {
        appendWrapped(options[i], O_TEXT_MAX_PX, i);

        if (i < 3)
        {
            appendDocRow(ROW_GAP, 255, "");
        }
    }

    if (docOverflow)
    {
        // Make room for the visible "cut" marker by dropping
        // the last wrapped line (the marker says content was
        // longer than the buffer — never a silent cut).
        if (docRowCount >= MAX_DOC_ROWS)
        {
            docRowCount = MAX_DOC_ROWS - 1;
        }

        appendDocRow(ROW_MARK, 255, "!");
    }

    docHeightPx = 0;

    for (int r = 0; r < docRowCount; r++)
    {
        docHeightPx += docRowHeight(docRows[r].kind);
    }

    maxScrollPx = docHeightPx - QVIEW_H;

    if (maxScrollPx < 0)
    {
        maxScrollPx = 0;
    }

    questionDocReady = true;
}

void drawOptionBadge(int x, int y, int opt, bool selected)
{
    if (selected)
    {
        tft.fillRoundRect(x, y, 13, 13, 3, COL_CYAN);
        tft.setTextColor(COL_BG);
    }
    else
    {
        tft.fillRoundRect(x, y, 13, 13, 3, COL_HEADER);
        tft.setTextColor(COL_WHITE);
    }

    tft.setTextSize(1);
    tft.setCursor(x + 3, y + 3);
    tft.print((char)('A' + opt));
}

bool isOptionLastRow(int r)
{
    return r + 1 >= docRowCount ||
           docRows[r + 1].opt != docRows[r].opt;
}

// Draw the visible slice of the document. Rows are only
// drawn when they fit FULLY inside the viewport (GFX text
// cannot be clipped to a box), so a partially visible row at
// either edge waits for the next scroll step.
void renderQuestionContent()
{
    tft.fillRect(0, QVIEW_Y0, 160, QVIEW_H, COL_BG);

    int y = QVIEW_Y0 - scrollPx;

    for (int r = 0; r < docRowCount; r++)
    {
        DocRow& row = docRows[r];

        int h = docRowHeight(row.kind);
        int top = y;
        int bottom = y + h;

        y += h;

        if (top < QVIEW_Y0 || bottom > QVIEW_Y1 + 1)
        {
            continue;
        }

        bool selected =
            row.opt < 4 &&
            lastAnswerChoice == (char)('A' + row.opt);

        if (row.kind == ROW_QTEXT)
        {
            tft.setTextSize(1);
            tft.setTextColor(COL_WHITE);
            tft.setCursor(Q_TEXT_X, top);
            tft.print(row.text);
        }
        else if (row.kind == ROW_MARK)
        {
            tft.setTextSize(1);
            tft.setTextColor(COL_RED);
            tft.setCursor(Q_TEXT_X, top);
            tft.print(">>");
        }
        else if (row.kind == ROW_OPT_HEAD ||
                 row.kind == ROW_OPT_CONT)
        {
            if (selected)
            {
                tft.fillRect(
                    3, top, 154, h, COL_PANEL_LT
                );
            }

            if (row.kind == ROW_OPT_HEAD)
            {
                drawOptionBadge(6, top + 1, row.opt, selected);

                tft.setTextSize(1);
                tft.setTextColor(
                    selected ? COL_CYAN : COL_WHITE
                );
                tft.setCursor(O_TEXT_X, top + 4);
                tft.print(row.text);
            }
            else
            {
                tft.setTextSize(1);
                tft.setTextColor(
                    selected ? COL_CYAN : COL_WHITE
                );
                tft.setCursor(O_TEXT_X, top);
                tft.print(row.text);
            }

            if (selected)
            {
                // Bracket the whole option block with cyan
                // rails so the selection stays visible across
                // every scroll position.
                tft.drawFastVLine(2, top, h, COL_CYAN);
                tft.drawFastVLine(157, top, h, COL_CYAN);

                if (row.kind == ROW_OPT_HEAD)
                {
                    tft.drawFastHLine(
                        2, top, 156, COL_CYAN
                    );
                }

                if (isOptionLastRow(r))
                {
                    tft.drawFastHLine(
                        2, bottom - 1, 156, COL_CYAN
                    );
                }
            }
        }
    }
}

// Footer: key hints, the chosen answer, an OFFLINE flag when
// the gateway link is down, and up/down arrows whenever more
// content sits above/below the viewport.
void renderQuestionFooter()
{
    tft.fillRect(0, QFOOT_Y, 160, 128 - QFOOT_Y, COL_BG);
    tft.drawFastHLine(0, QFOOT_Y, 160, COL_PANEL_LT);

    tft.setTextSize(1);

    if (gatewayConnected)
    {
        tft.setTextColor(COL_DIM);
        tft.setCursor(5, 116);
        tft.print("2:up 8:down");

        if (lastAnswerChoice >= 'A' &&
            lastAnswerChoice <= 'D')
        {
            tft.setTextColor(COL_YELLOW);
            tft.setCursor(104, 116);
            tft.print("Ans:");
            tft.print(lastAnswerChoice);
        }
    }
    else
    {
        tft.setTextColor(COL_RED);
        tft.setCursor(5, 116);
        tft.print("OFFLINE");
    }

    if (maxScrollPx > 0)
    {
        if (scrollPx > 0)
        {
            tft.fillTriangle(
                148, 117, 154, 117, 151, 113, COL_CYAN
            );
        }

        if (scrollPx < maxScrollPx)
        {
            tft.fillTriangle(
                148, 120, 154, 120, 151, 124, COL_CYAN
            );
        }
    }
}

void drawQuestionScreen()
{
    if (!questionDocReady)
    {
        // Question not fully received yet.
        drawReceivingScreen();

        lastClockPaint = 0;

        return;
    }

    tft.fillScreen(COL_BG);

    drawQuestionHeader();

    renderQuestionContent();

    renderQuestionFooter();

    lastClockPaint = 0;
}

// =====================================================
// SCREEN 7b: RECEIVING QUESTION (fragmented transfer)
// =====================================================

void drawReceivingScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawDocIcon(75, 20, COL_CYAN);

    drawSpinnerFrame(80, 46, 14, 0);

    drawTitleAuto("Receiving...", 70, COL_WHITE);

    drawWrappedCentered(
        "Downloading question data.",
        94,
        24,
        COL_GRAY,
        2
    );
}

// =====================================================
// SCREEN 8: SENDING ANSWER (spinner animated in loop)
// =====================================================

void drawSendingAnswerScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawPaperPlane(80, 44);

    drawSpinnerFrame(80, 44, 21, 0);

    printCentered("Sending answer...", 76, 1, COL_CYAN);

    printCentered("Please wait...", 94, 1, COL_GRAY);
}

// =====================================================
// SCREEN 9: ANSWER CONFIRMED
// =====================================================

void drawAnswerConfirmedScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawCheckCircle(80, 30, 13, COL_GREEN);

    printCentered("Answer sent!", 50, 2, COL_GREEN);

    tft.fillRoundRect(20, 70, 120, 28, 5, COL_PANEL);

    tft.setTextSize(1);
    tft.setTextColor(COL_WHITE);
    tft.setCursor(32, 76);

    if (questionTotal > 0)
    {
        tft.print("Q: ");
        tft.print(currentQuestionNumber);
        tft.print("/");
        tft.print(questionTotal);
    }
    else
    {
        tft.print("Q: ");
        tft.print(currentQuestionID);
    }

    tft.setCursor(32, 87);
    tft.print("Your answer: ");

    tft.setTextColor(COL_YELLOW);

    if (lastAnswerChoice >= 'A' && lastAnswerChoice <= 'D')
    {
        tft.print(lastAnswerChoice);
    }
    else
    {
        tft.print("-");
    }

    drawWrappedCentered(
        "Waiting for next question...",
        104,
        26,
        COL_GRAY,
        2
    );
}

// =====================================================
// SCREEN 10: NEXT QUESTION
// =====================================================

void drawNextQuestionScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawHourglass(80, 40);

    drawTitleAuto("Next question...", 72, COL_WHITE);

    printCentered("Please wait...", 92, 1, COL_GRAY);
}

// WAIT_DONE variant: everything answered, quiz not ended.
void drawWaitDoneScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawCheckCircle(80, 32, 14, COL_GREEN);

    printCentered("All done!", 54, 2, COL_GREEN);

    drawWrappedCentered(
        "All questions answered.",
        80,
        26,
        COL_WHITE,
        1
    );

    drawWrappedCentered(
        "Waiting for the quiz to end...",
        100,
        26,
        COL_GRAY,
        2
    );
}

void redrawWaitScreen()
{
    if (waitMode == WAIT_CONFIRMED)
    {
        drawAnswerConfirmedScreen();
    }
    else if (waitMode == WAIT_DONE)
    {
        drawWaitDoneScreen();
    }
    else
    {
        drawNextQuestionScreen();
    }
}

// =====================================================
// SCREEN 11: QUIZ FINISHED (result)
// =====================================================

void drawResultScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawTrophy(80, 36);

    printCentered("Quiz Finished!", 58, 1, COL_WHITE);

    int total = questionTotal > 0 ? questionTotal : quizTotal;

    float score =
        total > 0
            ? (float)correctCount * 10.0f / (float)total
            : 0.0f;

    tft.fillRoundRect(18, 68, 124, 38, 5, COL_PANEL);

    tft.setTextSize(1);

    tft.setTextColor(COL_WHITE);
    tft.setCursor(28, 74);
    tft.print("Correct: ");

    tft.setTextColor(COL_GREEN);
    tft.print(correctCount);

    tft.setTextColor(COL_WHITE);
    tft.print(" / ");
    tft.print(total);

    tft.setCursor(28, 88);
    tft.print("Score:");

    char buf[12];

    snprintf(buf, sizeof(buf), "%.1f/10", score);

    tft.setTextSize(2);
    tft.setTextColor(COL_YELLOW);
    tft.setCursor(66, 86);
    tft.print(buf);

    printCentered("Thank you!", 112, 1, COL_GRAY);
}

void showResultScreen()
{
    quizEnded = true;
    entryOpen = false;
    state = STATE_RESULT;

    drawResultScreen();

    int total = questionTotal > 0 ? questionTotal : quizTotal;

    float score =
        total > 0
            ? (float)correctCount * 10.0f / (float)total
            : 0.0f;

    char buf[12];

    snprintf(buf, sizeof(buf), "%.1f/10", score);

    Serial.print("RESULT: correct=");
    Serial.print(correctCount);
    Serial.print("/");
    Serial.print(total);
    Serial.print(" score=");
    Serial.println(buf);
}

// =====================================================
// SCREEN 12: CONNECTION LOST
// =====================================================

void drawConnectionLostScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawWifiLost(80, 38);

    drawTitleAuto("Connection Lost", 64, COL_RED);

    drawWrappedCentered(
        "Please stay in range of the classroom.",
        86,
        26,
        COL_GRAY,
        2
    );
}

// =====================================================
// SCREENS 13/14 + GENERIC MESSAGE
// (13: Invalid ID — red "!" circle, title, body)
// (14: Time's up! — red clock + button)
// =====================================================

void displayMessage(
    const char* title,
    uint16_t titleColor,
    const String& line1,
    const String& line2
)
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawExclaimCircle(80, 36, 16, titleColor);

    drawTitleAuto(title, 58, titleColor);

    if (line1.length() > 0)
    {
        drawWrappedCentered(line1, 82, 24, COL_WHITE, 3);
    }

    if (line2.length() > 0)
    {
        // Single trailing line; clamp so it cannot overflow
        // the 160px width.
        String l2 = line2;

        if ((int)l2.length() > 26)
        {
            l2 = l2.substring(0, 26);
        }

        printCentered(
            l2.c_str(),
            line1.length() > 0 ? 115 : 86,
            1,
            COL_GRAY
        );
    }
}

void drawTimeUpScreen()
{
    tft.fillScreen(COL_BG);

    drawAppHeader("PulseNet");

    drawClockBig(80, 38, 14, COL_RED);

    drawTitleAuto("Time's up!", 60, COL_RED);

    printCentered("No answer was sent.", 82, 1, COL_CYAN);

    drawButton(
        25, 96, 110, 20, COL_CYAN, "Next question..."
    );
}

// =====================================================
// SEND REGISTRATION
// =====================================================

bool sendRegistration()
{
    if (!deviceConnected)
    {
        displayMessage(
            "BLE ERROR",
            COL_RED,
            "Gateway not connected.",
            ""
        );

        return false;
    }

    String macAddress =
        BLEDevice::getAddress().toString().c_str();

    String packet =
        "{\"type\":\"REGISTER\","
        "\"student_id\":\"" +
        studentID +
        "\","
        "\"device_name\":\"" +
        String(deviceName) +
        "\","
        "\"device_mac\":\"" +
        macAddress +
        "\"}";

    Serial.print("TX: ");
    Serial.println(packet);

    registrationCharacteristic->setValue(packet.c_str());
    registrationCharacteristic->notify();

    registerSentAt = millis();

    return true;
}

// =====================================================
// SEND ANSWER
// =====================================================

bool sendAnswer(char answer)
{
    if (!deviceConnected || currentQuestionID.length() == 0)
    {
        return false;
    }

    // First attempt gets a fresh sequence number; automatic
    // retries reuse the current one (see the timeout handler
    // in loop()).
    if (answerAttempts == 0)
    {
        answerSeq++;
    }

    String packet =
        "{\"type\":\"ANSWER\","
        "\"student_id\":\"" +
        studentID +
        "\","
        "\"question_id\":\"" +
        currentQuestionID +
        "\","
        "\"answer\":\"" +
        String(answer) +
        "\","
        "\"sequence\":" +
        String((unsigned long)answerSeq) +
        "}";

    Serial.print("TX: ");
    Serial.println(packet);

    answerCharacteristic->setValue(packet.c_str());
    answerCharacteristic->notify();

    answerSentAt = millis();
    answerAttempts++;

    return true;
}

// =====================================================
// HELPERS
// =====================================================

bool allQuestionsAnswered()
{
    return questionTotal > 0 &&
           answeredCount >= questionTotal;
}

// =====================================================
// HANDLE QUIZ INFO (session lifecycle)
// =====================================================

void handleQuizInfo()
{
    Serial.print("QUIZ_INFO: ");
    Serial.print(newQuizTitle);
    Serial.print(" status=");
    Serial.print(
        newQuizLobby ? "lobby"
                     : (newQuizRunning ? "running" : "draft")
    );
    Serial.print(" time=");
    Serial.print(newQuizTimeLimit);
    Serial.print(" total=");
    Serial.print(newQuizTotal);
    Serial.print(" expected=");
    Serial.println(newQuizExpected);

    quizTitle = newQuizTitle;
    quizTotal = newQuizTotal;
    quizTimeLimitSec = newQuizTimeLimit;
    quizExpected = newQuizExpected;
    idPrefix = newQuizPrefix;
    idLength = newQuizIdLength;

    if (questionTotal == 0 && quizTotal > 0)
    {
        questionTotal = quizTotal;
    }

    // -------------------------------------------------
    // LOBBY: session pushed, students enter IDs
    // -------------------------------------------------

    if (newQuizLobby)
    {
        if (newQuizID > 0)
        {
            activeQuizID = newQuizID;
        }

        // Already joined? Keep the joined screen.
        if (state == STATE_JOINED ||
            state == STATE_REGISTERING)
        {
            return;
        }

        studentID = "";
        entryOpen = true;

        state = STATE_LOBBY;

        drawLobbyEntry();

        return;
    }

    // -------------------------------------------------
    // RUNNING: the teacher started the quiz
    // -------------------------------------------------

    if (newQuizRunning)
    {
        // A different quiz_id means a FRESH session — even
        // if the previous one was never cleaned up on
        // screen (e.g. teacher finished quiz A and started
        // quiz B right away). Reset score + countdown.
        bool newSession =
            newQuizID > 0 && newQuizID != activeQuizID;

        if (newSession)
        {
            activeQuizID = newQuizID;
            answeredCount = 0;
            correctCount = 0;
            lastCountedQuestionID = "";
            lastCountedCorrect = false;
            quizDeadlineSet = false;
        }

        quizRunning = true;
        quizEnded = false;

        if (!quizDeadlineSet)
        {
            if (quizTimeLimitSec > 0)
            {
                quizDeadline =
                    millis() +
                    (unsigned long)quizTimeLimitSec * 1000UL;

                quizDeadlineSet = true;
            }
        }

        entryOpen = false;

        // Devices that have NOT joined yet (still typing the
        // student ID in the lobby) stay in the lobby: their
        // answers would be rejected until they register.
        // After REGISTER_ACK the gateway pushes the current
        // question and pendingQuestion moves them on.
        if (state == STATE_LOGO ||
            state == STATE_JOINED ||
            state == STATE_RESULT)
        {
            runStartCountdown();

            state = STATE_WAIT_QUESTION;
            waitMode = WAIT_NEXT;

            drawNextQuestionScreen();
        }

        return;
    }

    // -------------------------------------------------
    // DRAFT: no active session (or lobby cancelled).
    //
    // If the result screen is showing, KEEP it — the
    // teacher may still be reviewing scores. The next
    // lobby/running QUIZ_INFO (new quiz_id) starts a
    // fresh session and pulls the device out of it.
    // -------------------------------------------------

    quizRunning = false;
    quizDeadlineSet = false;
    quizEnded = false;
    entryOpen = false;
    answeredCount = 0;
    correctCount = 0;
    lastCountedQuestionID = "";
    lastCountedCorrect = false;
    questionTotal = 0;
    activeQuizID = 0;

    studentID = "";

    if (state == STATE_RESULT)
    {
        return;
    }

    state = STATE_LOGO;

    drawIdleWaitScreen();
}

// =====================================================
// HANDLE ACK
// =====================================================

void handleAck()
{
    Serial.print("ACK type=");
    Serial.print(ackType);
    Serial.print(" status=");
    Serial.println(ackStatus);

    // ----- Gateway greeting -----

    if (ackType == "ACK" && ackStatus == "CONNECTED")
    {
        gatewayConnected = true;
        bleLinkLost = false;

        // Repaint whatever screen the device is on so the
        // header BLE icon turns white.
        if (state == STATE_LOGO)
        {
            drawIdleWaitScreen();
        }
        else if (state == STATE_LOBBY)
        {
            drawLobbyEntry();
        }
        else if (state == STATE_REGISTERING)
        {
            drawConnectingScreen();
        }
        else if (state == STATE_JOINED)
        {
            joinedPhase = JOINED_INFO;

            drawQuizInfoScreen();
        }
        else if (state == STATE_WAIT_QUESTION)
        {
            redrawWaitScreen();
        }
        else if (state == STATE_QUESTION)
        {
            drawQuestionScreen();
            drawQuizClock(true);
        }
        else if (state == STATE_ANSWER_SENT)
        {
            drawSendingAnswerScreen();
        }
        else if (state == STATE_RESULT)
        {
            drawResultScreen();
        }

        return;
    }

    // ----- REGISTER_ACK -----

    if (ackType == "REGISTER_ACK")
    {
        if (state != STATE_REGISTERING)
        {
            return;
        }

        if (ackStatus == "ACCEPTED")
        {
            state = STATE_JOINED;
            joinedPhase = JOINED_HELLO;
            joinedShownAt = millis();

            drawJoinedScreen();
        }
        else
        {
            String reason =
                ackReason.length() > 0
                    ? ackReason
                    : "This student ID is not registered or not allowed.";

            displayMessage(
                "Invalid ID",
                COL_RED,
                reason,
                ""
            );

            delay(2500);

            // Let the student try again (entry stays open
            // until the teacher starts the quiz).
            if (state == STATE_REGISTERING)
            {
                state = STATE_LOBBY;

                drawLobbyEntry();
            }
        }

        return;
    }

    // ----- ANSWER_ACK -----

    if (ackType == "ANSWER_ACK")
    {
        // Any final verdict ends the retry cycle for this
        // answer (a duplicate ACK for the same question is
        // filtered by the counters below).
        answerAttempts = 0;

        if (ackStatus == "ACCEPTED")
        {
            // Count each question at most once. The gateway
            // may re-ACK the same question after a re-answer
            // or a duplicate packet, and an ACK may arrive
            // LATE — after the 5s timeout put us back on
            // the question screen.
            if (ackQuestionID.length() > 0 &&
                ackQuestionID == lastCountedQuestionID)
            {
                if (ackCorrect && !lastCountedCorrect)
                {
                    correctCount++;
                }
                else if (!ackCorrect &&
                         lastCountedCorrect)
                {
                    correctCount--;
                }

                lastCountedCorrect = ackCorrect;
            }
            else
            {
                answeredCount++;

                if (ackCorrect)
                {
                    correctCount++;
                }

                lastCountedQuestionID = ackQuestionID;
                lastCountedCorrect = ackCorrect;
            }

            // Accept the ACK while waiting OR when the same
            // question is still on screen (late ACK). If the
            // next question was already pushed, only the
            // counters above change — nothing to redraw.
            if (state == STATE_ANSWER_SENT ||
                (state == STATE_QUESTION &&
                 ackQuestionID == currentQuestionID))
            {
                state = STATE_WAIT_QUESTION;

                if (allQuestionsAnswered())
                {
                    waitMode = WAIT_DONE;

                    drawWaitDoneScreen();
                }
                else
                {
                    waitMode = WAIT_CONFIRMED;
                    waitConfirmedAt = millis();

                    drawAnswerConfirmedScreen();
                }
            }
        }
        else
        {
            // A rejection only matters while we are still
            // waiting for the ACK of that answer.
            if (state != STATE_ANSWER_SENT)
            {
                return;
            }

            String reason =
                ackReason.length() > 0
                    ? ackReason
                    : "INVALID";

            displayMessage(
                "REJECTED",
                COL_RED,
                "Answer rejected:",
                reason
            );

            delay(2000);

            drawQuestionScreen();
            drawQuizClock(true);

            state = STATE_QUESTION;
        }

        return;
    }
}

// =====================================================
// INITIALIZE BLE
// =====================================================

void setupBLE()
{
    Serial.println();
    Serial.println("Starting BLE...");

    uint8_t btMac[6];

    esp_read_mac(btMac, ESP_MAC_BT);

    snprintf(
        deviceName,
        sizeof(deviceName),
        DEVICE_NAME_PREFIX "-%02X%02X",
        btMac[4],
        btMac[5]
    );

    BLEDevice::init(deviceName);

    String macAddress =
        BLEDevice::getAddress().toString().c_str();

    Serial.print("Device Name : ");
    Serial.println(deviceName);

    Serial.print("BLE MAC     : ");
    Serial.println(macAddress);

    bleServer = BLEDevice::createServer();

    bleServer->setCallbacks(new ServerCallbacks());

    BLEService* service =
        bleServer->createService(
            PULSENET_SERVICE_UUID
        );

    registrationCharacteristic =
        service->createCharacteristic(
            REGISTRATION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    registrationCharacteristic->addDescriptor(
        new BLE2902()
    );

    questionCharacteristic =
        service->createCharacteristic(
            QUESTION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    questionCharacteristic->setCallbacks(
        new QuestionCallbacks()
    );

    answerCharacteristic =
        service->createCharacteristic(
            ANSWER_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    answerCharacteristic->addDescriptor(
        new BLE2902()
    );

    ackCharacteristic =
        service->createCharacteristic(
            ACK_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    ackCharacteristic->setCallbacks(
        new ACKCallbacks()
    );

    service->start();

    BLEAdvertising* advertising =
        BLEDevice::getAdvertising();

    advertising->addServiceUUID(
        PULSENET_SERVICE_UUID
    );

    advertising->setScanResponse(true);

    advertising->setMinPreferred(0x06);
    advertising->setMinPreferred(0x12);

    BLEDevice::startAdvertising();

    Serial.println("BLE initialized. Advertising started.");
}

// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    delay(1000);

    Serial.println();
    Serial.println("PulseNet Student Device");
    Serial.println("ESP32 + ST7735S 160x128 + Keypad + BLE");

    tft.initR(INITR_BLACKTAB);
    tft.setRotation(1);
    tft.fillScreen(ST77XX_BLACK);

    Serial.print("TFT width  : ");
    Serial.println(tft.width());

    Serial.print("TFT height : ");
    Serial.println(tft.height());

    for (int i = 0; i < 4; i++)
    {
        pinMode(rowPins[i], OUTPUT);
        digitalWrite(rowPins[i], HIGH);
    }

    for (int i = 0; i < 4; i++)
    {
        pinMode(colPins[i], INPUT_PULLUP);
    }

    setupBLE();

    // Screen 1 (splash) then screen 15 (idle wait).
    drawSplashScreen();

    state = STATE_LOGO;

    drawIdleWaitScreen();

    Serial.println("System ready. Waiting for a quiz session...");
}

// =====================================================
// LOOP
// =====================================================

void loop()
{
    // -------------------------------------------------
    // 0. Advertising watchdog
    //
    // If the link died without an onDisconnect event
    // (e.g. the gateway host rebooted mid-connection),
    // the stack can sit silent and never advertise
    // again. Restart advertising periodically while no
    // central is connected so the gateway can always
    // find us.
    // -------------------------------------------------

    static unsigned long lastAdvCheck = 0;

    if (!deviceConnected &&
        millis() - lastAdvCheck > 8000)
    {
        lastAdvCheck = millis();

        if (bleServer->getConnectedCount() == 0)
        {
            BLEDevice::startAdvertising();
        }
    }

    // -------------------------------------------------
    // 1. Pending BLE events
    // -------------------------------------------------

    if (pendingBleLost)
    {
        pendingBleLost = false;

        if (state == STATE_LOGO)
        {
            // Idle screen: just refresh the header icon.
            drawIdleWaitScreen();
        }
        else if (state == STATE_QUESTION)
        {
            // Keep the question content on screen; the header
            // icon and the OFFLINE footer flag the lost link.
            drawQuestionHeader();
            drawQuizClock(true);
            renderQuestionFooter();
        }
        else if (
            state != STATE_ANSWER_SENT &&
            state != STATE_RESULT)
        {
            // Keep the final score / sending screen; otherwise
            // show the connection-lost screen.
            drawConnectionLostScreen();
        }
    }

    if (pendingQuizEnd)
    {
        pendingQuizEnd = false;

        Serial.println("QUIZ_END received.");

        if (!quizEnded)
        {
            showResultScreen();
        }
    }

    if (pendingQuizInfo)
    {
        pendingQuizInfo = false;

        handleQuizInfo();
    }

    if (pendingQBegin)
    {
        pendingQBegin = false;

        // A fragmented question is arriving: show the
        // receiving status on the screens where it makes
        // sense (the lobby ID entry keeps its own screen).
        if (state == STATE_QUESTION ||
            state == STATE_WAIT_QUESTION ||
            state == STATE_ANSWER_SENT)
        {
            showingReceiving = true;

            drawReceivingScreen();
        }
    }

    if (pendingQuestion)
    {
        pendingQuestion = false;

        if (quizEnded)
        {
            quizEnded = false;
        }

        Serial.print("New question: ");
        Serial.println(currentQuestionID);

        answerAttempts = 0;
        showingReceiving = false;

        state = STATE_QUESTION;

        buildQuestionDoc();

        drawQuestionScreen();
        drawQuizClock(true);
    }

    if (pendingAck)
    {
        pendingAck = false;

        handleAck();
    }

    // -------------------------------------------------
    // 2. Quiz countdown (expiry checked in every state,
    //    the clock itself paints on the question screen)
    // -------------------------------------------------

    if (!quizEnded && quizDeadlineSet && state != STATE_RESULT)
    {
        if (clockRemainingSec() <= 0)
        {
            bool answeredAll = allQuestionsAnswered();

            if (!answeredAll &&
                (state == STATE_QUESTION ||
                 state == STATE_ANSWER_SENT))
            {
                drawTimeUpScreen();

                delay(2000);
            }

            showResultScreen();
        }
        else if (state == STATE_QUESTION)
        {
            drawQuizClock(false);
        }
    }

    // -------------------------------------------------
    // 3. Screen animations / sub-screens
    // -------------------------------------------------

    static unsigned long lastAnimTick = 0;
    static int spinnerAngle = 0;

    if (millis() - lastAnimTick >= 80)
    {
        lastAnimTick = millis();

        if (state == STATE_REGISTERING)
        {
            spinnerAngle = (spinnerAngle + 25) % 360;

            drawSpinnerFrame(80, 46, 14, spinnerAngle);
        }
        else if (state == STATE_ANSWER_SENT &&
                 !showingReceiving)
        {
            spinnerAngle = (spinnerAngle + 25) % 360;

            drawSpinnerFrame(80, 44, 21, spinnerAngle);
        }
        else if (showingReceiving)
        {
            spinnerAngle = (spinnerAngle + 25) % 360;

            drawSpinnerFrame(80, 46, 14, spinnerAngle);
        }
    }

    static unsigned long lastBlinkTick = 0;

    if (state == STATE_LOBBY &&
        millis() - lastBlinkTick >= 500)
    {
        lastBlinkTick = millis();

        idCursorOn = !idCursorOn;

        updateIdBox(idCursorOn);
    }

    if (state == STATE_JOINED &&
        joinedPhase == JOINED_HELLO &&
        millis() - joinedShownAt > 2000)
    {
        joinedPhase = JOINED_INFO;

        drawQuizInfoScreen();
    }

    if (state == STATE_WAIT_QUESTION &&
        waitMode == WAIT_CONFIRMED &&
        millis() - waitConfirmedAt > 4000)
    {
        if (allQuestionsAnswered())
        {
            waitMode = WAIT_DONE;

            drawWaitDoneScreen();
        }
        else
        {
            waitMode = WAIT_NEXT;

            drawNextQuestionScreen();
        }
    }

    // -------------------------------------------------
    // 4. Timeouts
    // -------------------------------------------------

    // A fragmented question that stalls mid-transfer is
    // abandoned; the gateway re-pushes the whole question
    // after a reconnect (or on its next poll).
    if (questionReceiving &&
        millis() - fragStartedAt > FRAG_TIMEOUT_MS)
    {
        questionReceiving = false;
        fragBuf = "";

        Serial.println(
            "[QFRAG] Timeout - transfer abandoned."
        );

        if (showingReceiving)
        {
            showingReceiving = false;

            if (state == STATE_QUESTION)
            {
                drawQuestionScreen();
                drawQuizClock(true);
            }
        }
    }

    if (state == STATE_REGISTERING &&
        millis() - registerSentAt > 6000)
    {
        if (deviceConnected)
        {
            displayMessage(
                "NO REPLY",
                COL_RED,
                "Gateway did not reply.",
                ""
            );

            delay(1500);
        }
        else
        {
            delay(600);
        }

        // Entry stays open; let the student retry.
        state = STATE_LOBBY;
        drawLobbyEntry();
    }

    if (state == STATE_ANSWER_SENT &&
        millis() - answerSentAt > 5000)
    {
        if (deviceConnected &&
            answerAttempts < MAX_ANSWER_ATTEMPTS &&
            currentQuestionID.length() > 0)
        {
            // ACK lost: resend the SAME answer with the SAME
            // sequence — the backend treats it as a retry and
            // returns the stored answer instead of saving a
            // second one.
            sendAnswer(lastAnswerChoice);

            // Stay in STATE_ANSWER_SENT; the spinner keeps
            // running while the gateway replies.
        }
        else
        {
            // Back to the question screen. If the link is
            // down the content is still shown, with the
            // OFFLINE flag in the footer and header.
            drawQuestionScreen();
            drawQuizClock(true);

            answerAttempts = 0;

            state = STATE_QUESTION;
        }
    }

    // -------------------------------------------------
    // 5. Keypad (state-aware)
    // -------------------------------------------------

    char key = readKeypad();

    if (key != '\0')
    {
        Serial.print("Key pressed: ");
        Serial.println(key);

        // ----- Lobby: enter student ID -----

        if (state == STATE_LOBBY)
        {
            if (key >= '0' && key <= '9')
            {
                if (studentID.length() < MAX_ID_LENGTH)
                {
                    studentID += key;

                    updateIdBox(true);

                    Serial.print("Student ID: ");
                    Serial.println(studentID);
                }
            }
            else if (key == '*')
            {
                studentID = "";

                updateIdBox(true);

                Serial.print("Student ID: ");
                Serial.println(studentID);
            }
            else if (key == '#')
            {
                if (studentID.length() == 0)
                {
                    displayMessage(
                        "NO ID",
                        COL_RED,
                        "Enter your student ID first.",
                        ""
                    );

                    delay(1200);

                    drawLobbyEntry();
                }
                else if (
                    idPrefix.length() > 0 &&
                    !studentID.startsWith(idPrefix)
                )
                {
                    displayMessage(
                        "WRONG ID",
                        COL_RED,
                        "ID must start with:",
                        idPrefix
                    );

                    delay(1500);

                    drawLobbyEntry();
                }
                else if (
                    idLength > 0 &&
                    (int)studentID.length() != idLength
                )
                {
                    displayMessage(
                        "WRONG ID",
                        COL_RED,
                        "ID must be exactly",
                        String(idLength) + " digits"
                    );

                    delay(1500);

                    drawLobbyEntry();
                }
                else if (sendRegistration())
                {
                    state = STATE_REGISTERING;

                    drawConnectingScreen();
                }
            }
        }

        // ----- Question: scroll + answer -----

        else if (state == STATE_QUESTION)
        {
            if (questionReceiving || showingReceiving)
            {
                // A new question is mid-download — keys are
                // ignored until it completes (or times out).
            }
            else if (key == '2' || key == '8')
            {
                // Scroll: clamped at both ends, so pressing
                // '2' at the top and '8' at the bottom just
                // holds the position.
                if (maxScrollPx > 0)
                {
                    int before = scrollPx;

                    if (key == '2')
                    {
                        scrollPx -= SCROLL_STEP_PX;
                    }
                    else
                    {
                        scrollPx += SCROLL_STEP_PX;
                    }

                    if (scrollPx < 0)
                    {
                        scrollPx = 0;
                    }

                    if (scrollPx > maxScrollPx)
                    {
                        scrollPx = maxScrollPx;
                    }

                    if (scrollPx != before)
                    {
                        renderQuestionContent();
                        renderQuestionFooter();
                    }
                }
            }
            else if (key >= 'A' && key <= 'D')
            {
                lastAnswerChoice = key;

                // Selection is part of the document render, so
                // it survives any later scrolling.
                renderQuestionContent();
                renderQuestionFooter();

                if (sendAnswer(key))
                {
                    state = STATE_ANSWER_SENT;

                    drawSendingAnswerScreen();
                }
                else
                {
                    drawQuestionScreen();
                    drawQuizClock(true);
                }
            }
        }
        // Other states: keys ignored.
    }

    delay(10);
}
