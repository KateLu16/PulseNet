#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "logo.h"

// =====================================================
// DEVICE
// =====================================================

#define DEVICE_NAME "PULSENET-001"

// =====================================================
// TFT - 160x128 LANDSCAPE
// =====================================================

#define TFT_CS    5
#define TFT_DC    2
#define TFT_RST   4

Adafruit_ST7735 tft(TFT_CS, TFT_DC, TFT_RST);

// =====================================================
// KEYPAD 4x4
// =====================================================

#define ROW1 13
#define ROW2 12
#define ROW3 14
#define ROW4 27

#define COL1 26
#define COL2 25
#define COL3 33
#define COL4 32

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
// LOGO          -> idle: HCMUTE logo, waiting for a session
// LOBBY         -> session pushed: enter ID (open-ended)
// REGISTERING   -> waiting for REGISTER_ACK
// JOINED        -> in, waiting for the teacher to start
// WAIT_QUESTION -> quiz running, waiting for a question
// QUESTION      -> question on screen, A-D to answer
// ANSWER_SENT   -> choice highlighted, waiting for ACK
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

// Timeouts for missing ACKs.

unsigned long registerSentAt = 0;
unsigned long answerSentAt = 0;

volatile bool gatewayConnected = false;

// =====================================================
// PENDING BLE EVENTS
// =====================================================

volatile bool pendingQuestion = false;
volatile bool pendingAck = false;
volatile bool pendingQuizInfo = false;
volatile bool pendingQuizEnd = false;

String ackType = "";
String ackStatus = "";
String ackReason = "";
bool ackCorrect = false;

String newQuizTitle = "";
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

    int end = packet.indexOf("\"", start);

    if (end <= start)
    {
        return "";
    }

    return packet.substring(start, end);
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

// =====================================================
// LAYOUT
// =====================================================

// Quiz clock: top-right corner (x 118..160, y 4..16).

#define CLOCK_X 118
#define CLOCK_Y 4
#define CLOCK_W 42
#define CLOCK_H 12

// Option row Y positions on the question screen.

const int optionY[4] = {68, 82, 96, 110};

// =====================================================
// FORWARD DECLARATIONS
// =====================================================

void showResultScreen();
void drawQuizClock(bool force = false);
void drawGatewayFooter();
void displayLogoIdle();
void drawSignalIcon();
void displayLobbyEntry();
void displayStudentID();
void displayJoined();
void displayQuizStarting();
void displayMessage(
    const char* title,
    uint16_t titleColor,
    const String& line1,
    const String& line2
);
void displayWaitQuestion();
void drawQuestionScreen();
void highlightOption(char choice);

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

        if (state == STATE_LOGO)
        {
            drawSignalIcon();
        }

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
            ackStatus = jsonGetString(value, "status");
            ackReason = jsonGetString(value, "reason");
            ackCorrect =
                jsonGetString(value, "correct") == "true";

            pendingAck = true;
        }
    }
};

// =====================================================
// QUESTION CALLBACK
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
// TEXT WRAP HELPER
// =====================================================

void drawWrappedText(
    const String& text,
    int x,
    int y,
    int maxY,
    int maxCharsPerLine
)
{
    String remaining = text;

    while (remaining.length() > 0 && y < maxY)
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

        tft.setCursor(x, y);
        tft.println(line);

        remaining = remaining.substring(lineLength);

        remaining.trim();

        y += 10;
    }
}

// =====================================================
// QUIZ CLOCK (top-right corner, every screen)
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

    int remaining = clockRemainingSec();

    char buf[8];

    snprintf(
        buf,
        sizeof(buf),
        "%02d:%02d",
        remaining / 60,
        remaining % 60
    );

    tft.fillRect(
        CLOCK_X,
        CLOCK_Y,
        CLOCK_W,
        CLOCK_H,
        ST77XX_BLACK
    );

    tft.setTextSize(1);

    tft.setTextColor(
        remaining <= 10 ? ST77XX_RED : ST77XX_YELLOW
    );

    tft.setCursor(CLOCK_X + 4, CLOCK_Y + 1);
    tft.print(buf);

    if (remaining <= 0 && !quizEnded)
    {
        showResultScreen();
    }
}

// =====================================================
// GATEWAY FOOTER
// =====================================================

void drawGatewayFooter()
{
    tft.fillRect(0, 118, 160, 10, ST77XX_BLACK);

    tft.setTextSize(1);

    tft.setTextColor(
        gatewayConnected ? ST77XX_GREEN : ST77XX_RED
    );

    tft.setCursor(5, 119);

    tft.print("Gateway: ");

    tft.println(gatewayConnected ? "OK" : "...");
}

// =====================================================
// SCREEN: LOGO IDLE (waiting for a session)
// =====================================================

// Signal icon, top-left corner: a broadcast dot with
// sound-wave arcs. Black while the gateway is linked;
// gray with a red diagonal slash while it is not.

void drawBroadcastArcs(
    int cx,
    int cy,
    int r,
    uint16_t color
)
{
    for (int side = -1; side <= 1; side += 2)
    {
        int px = 0;
        int py = 0;

        for (int a = -50; a <= 50; a += 5)
        {
            float rad = a * 3.14159f / 180.0f;

            int x = cx + side *
                (int)(r * cos(rad) + 0.5f);

            int y = cy -
                (int)(r * sin(rad) + 0.5f);

            if (a > -50)
            {
                tft.drawLine(px, py, x, y, color);
            }

            px = x;
            py = y;
        }
    }
}

void drawSignalIcon()
{
    // White patch behind the icon.
    tft.fillRect(2, 2, 30, 22, ST77XX_WHITE);

    int cx = 17;
    int cy = 13;

    uint16_t color =
        gatewayConnected
            ? ST77XX_BLACK
            : 0xB596;  // light gray

    tft.fillCircle(cx, cy, 3, color);

    drawBroadcastArcs(cx, cy, 8, color);
    drawBroadcastArcs(cx, cy, 7, color);
    drawBroadcastArcs(cx, cy, 12, color);
    drawBroadcastArcs(cx, cy, 11, color);

    if (!gatewayConnected)
    {
        // Red slash, bottom-left to top-right.
        tft.drawLine(5, 21, 29, 5, ST77XX_RED);
        tft.drawLine(6, 21, 30, 5, ST77XX_RED);
    }
}

void displayLogoIdle()
{
    // White background + purple HCMUTE logo.
    tft.drawRGBBitmap(
        0,
        0,
        LOGO_HCMUTE,
        LOGO_WIDTH,
        LOGO_HEIGHT
    );

    drawSignalIcon();

    // "Waiting for teacher..." centered near the bottom.
    tft.fillRect(0, 110, 160, 14, ST77XX_WHITE);

    tft.setTextColor(ST77XX_BLACK);
    tft.setTextSize(1);

    const char* msg = "Waiting for teacher...";

    int16_t x =
        (160 - (int)strlen(msg) * 6) / 2;

    tft.setCursor(x, 115);
    tft.print(msg);

    lastClockPaint = 0;
}

// =====================================================
// SCREEN: LOBBY ENTRY (open-ended ID entry)
// =====================================================

void displayLobbyEntry()
{
    tft.fillScreen(ST77XX_BLACK);

    // Quiz title (up to 2 lines).
    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(1);

    if (quizTitle.length() > 0)
    {
        drawWrappedText(quizTitle, 5, 4, 26, 19);
    }

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(5, 30);
    tft.println("Enter Student ID:");

    tft.fillRect(0, 42, 160, 20, ST77XX_BLACK);
    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 44);
    tft.println(studentID);

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    tft.setCursor(5, 70);
    tft.print("* Clear   # Confirm");

    if (quizTimeLimitSec > 0)
    {
        char buf[8];
        snprintf(buf, sizeof(buf), "%02d:%02d",
                 quizTimeLimitSec / 60,
                 quizTimeLimitSec % 60);

        tft.setCursor(5, 88);
        tft.print("Quiz time: ");
        tft.print(buf);
    }

    if (quizTotal > 0)
    {
        tft.setCursor(5, 100);
        tft.print("Questions: ");
        tft.print(quizTotal);
    }

    drawGatewayFooter();
}

void displayStudentID()
{
    tft.fillRect(0, 42, 160, 20, ST77XX_BLACK);

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 44);
    tft.println(studentID);

    Serial.print("Student ID: ");
    Serial.println(studentID);
}

// =====================================================
// SCREEN: JOINED / STARTING
// =====================================================

void displayJoined()
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setCursor(30, 14);
    tft.println("JOINED!");

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    tft.setCursor(10, 44);
    tft.print("ID: ");

    tft.setTextColor(ST77XX_YELLOW);
    tft.println(studentID);

    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(10, 70);
    tft.println("Waiting for the teacher");
    tft.setCursor(10, 82);
    tft.println("to start the quiz...");

    drawGatewayFooter();
}

void displayQuizStarting()
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(2);
    tft.setCursor(25, 14);
    tft.println("GET READY!");

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    tft.setCursor(10, 50);
    tft.println("The quiz is starting...");

    tft.setCursor(10, 70);
    tft.println("ID: ");

    tft.setTextColor(ST77XX_YELLOW);
    tft.println(studentID);

    drawGatewayFooter();
}

// =====================================================
// SCREEN: SIMPLE MESSAGE
// =====================================================

void displayMessage(
    const char* title,
    uint16_t titleColor,
    const String& line1,
    const String& line2
)
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(titleColor);
    tft.setTextSize(2);

    int16_t x = (160 - (int)strlen(title) * 12) / 2;

    if (x < 0)
    {
        x = 5;
    }

    tft.setCursor(x, 14);
    tft.println(title);

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    if (line1.length() > 0)
    {
        drawWrappedText(line1, 10, 50, 84, 24);
    }

    if (line2.length() > 0)
    {
        drawWrappedText(line2, 10, 86, 114, 24);
    }

    drawGatewayFooter();
}

// =====================================================
// SCREEN: WAIT FOR NEXT QUESTION
// =====================================================

void displayWaitQuestion()
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setCursor(45, 16);
    tft.println("READY");

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    tft.setCursor(10, 42);
    tft.print("ID: ");

    tft.setTextColor(ST77XX_YELLOW);
    tft.println(studentID);

    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(10, 58);
    tft.print("Answered: ");
    tft.println(answeredCount);

    tft.setCursor(10, 74);

    if (questionTotal > 0 &&
        answeredCount >= questionTotal)
    {
        tft.println("All questions answered.");
        tft.setCursor(10, 88);
        tft.println("Waiting for the quiz to end...");
    }
    else
    {
        tft.println("Waiting for next question...");
    }

    drawGatewayFooter();
}

// =====================================================
// SCREEN: QUESTION
// =====================================================

void drawQuestionScreen()
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(1);
    tft.setCursor(5, 5);
    tft.print("Question ");

    tft.setTextColor(ST77XX_YELLOW);

    if (questionTotal > 0)
    {
        tft.print(currentQuestionNumber);
        tft.print("/");
        tft.print(questionTotal);
    }
    else
    {
        tft.print(currentQuestionID);
    }

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    drawWrappedText(qText, 5, 20, 64, 26);

    const String options[4] = {qA, qB, qC, qD};

    for (int i = 0; i < 4; i++)
    {
        tft.setTextColor(ST77XX_WHITE);
        tft.setCursor(5, optionY[i]);
        tft.print((char)('A' + i));
        tft.print(". ");
        tft.println(options[i]);
    }

    lastClockPaint = 0;
}

void highlightOption(char choice)
{
    int index = choice - 'A';

    if (index < 0 || index > 3)
    {
        return;
    }

    const String options[4] = {qA, qB, qC, qD};

    tft.fillRect(
        0,
        optionY[index] - 2,
        160,
        14,
        ST77XX_BLUE
    );

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(5, optionY[index]);

    tft.print((char)('A' + index));
    tft.print(". ");
    tft.println(options[index]);

    tft.fillRect(0, 124, 160, 4, ST77XX_BLACK);

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(1);
    tft.setCursor(5, 124);
    tft.print("Sending...");
}

// =====================================================
// SCREEN: RESULT
// =====================================================

void showResultScreen()
{
    quizEnded = true;
    entryOpen = false;
    state = STATE_RESULT;

    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(2);
    tft.setCursor(22, 12);
    tft.println("QUIZ ENDED");

    int total = questionTotal > 0 ? questionTotal : quizTotal;

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);

    tft.setCursor(10, 45);
    tft.print("Correct: ");

    tft.setTextColor(ST77XX_GREEN);
    tft.print(correctCount);

    tft.setTextColor(ST77XX_WHITE);
    tft.print(" / ");
    tft.print(total);

    float score =
        total > 0
            ? (float)correctCount * 10.0f / (float)total
            : 0.0f;

    tft.setTextColor(ST77XX_WHITE);
    tft.setCursor(10, 65);
    tft.print("Score: ");

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 80);

    char buf[12];

    snprintf(buf, sizeof(buf), "%.1f/10", score);

    tft.println(buf);

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(10, 108);
    tft.println("See the teacher's screen.");

    Serial.print("RESULT: correct=");
    Serial.print(correctCount);
    Serial.print("/");
    Serial.print(total);
    Serial.print(" score=");
    Serial.println(buf);
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
            ST77XX_RED,
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
        "\"device_name\":\"" DEVICE_NAME "\","
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
        "\"}";

    Serial.print("TX: ");
    Serial.println(packet);

    answerCharacteristic->setValue(packet.c_str());
    answerCharacteristic->notify();

    answerSentAt = millis();

    return true;
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
        // Already joined? Keep the joined screen.
        if (state == STATE_JOINED ||
            state == STATE_REGISTERING)
        {
            return;
        }

        studentID = "";
        entryOpen = true;

        state = STATE_LOBBY;

        displayLobbyEntry();

        return;
    }

    // -------------------------------------------------
    // RUNNING: the teacher started the quiz
    // -------------------------------------------------

    if (newQuizRunning)
    {
        bool alreadyRunning = quizRunning;

        quizRunning = true;
        quizEnded = false;

        if (!alreadyRunning)
        {
            answeredCount = 0;
            correctCount = 0;
        }

        if (!quizDeadlineSet || !alreadyRunning)
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

        if (state == STATE_LOGO ||
            state == STATE_LOBBY ||
            state == STATE_JOINED ||
            state == STATE_RESULT)
        {
            state = STATE_WAIT_QUESTION;

            displayQuizStarting();
        }

        return;
    }

    // -------------------------------------------------
    // DRAFT: no active session (or lobby cancelled)
    // -------------------------------------------------

    quizRunning = false;
    quizDeadlineSet = false;
    quizEnded = false;
    entryOpen = false;
    answeredCount = 0;
    correctCount = 0;
    questionTotal = 0;

    studentID = "";

    state = STATE_LOGO;

    displayLogoIdle();
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

        if (state == STATE_LOGO)
        {
            // White idle screen: just repaint the signal icon.
            drawSignalIcon();
        }
        else if (state == STATE_LOBBY)
        {
            displayLobbyEntry();
        }
        else if (state == STATE_JOINED)
        {
            displayJoined();
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

            displayJoined();
        }
        else
        {
            String reason =
                ackReason.length() > 0
                    ? ackReason
                    : "UNKNOWN";

            displayMessage(
                "REJECTED",
                ST77XX_RED,
                "Registration failed:",
                reason
            );

            delay(2000);

            // Let the student try again (entry stays open
            // until the teacher starts the quiz).
            if (state == STATE_REGISTERING)
            {
                state = STATE_LOBBY;

                displayLobbyEntry();
            }
        }

        return;
    }

    // ----- ANSWER_ACK -----

    if (ackType == "ANSWER_ACK")
    {
        if (state != STATE_ANSWER_SENT)
        {
            return;
        }

        if (ackStatus == "ACCEPTED")
        {
            answeredCount++;

            if (ackCorrect)
            {
                correctCount++;
            }

            state = STATE_WAIT_QUESTION;

            if (questionTotal > 0 &&
                answeredCount >= questionTotal)
            {
                displayWaitQuestion();
            }
            else
            {
                displayMessage(
                    "SENT",
                    ST77XX_CYAN,
                    "Answer recorded.",
                    "Loading next question..."
                );
            }
        }
        else
        {
            String reason =
                ackReason.length() > 0
                    ? ackReason
                    : "INVALID";

            displayMessage(
                "REJECTED",
                ST77XX_RED,
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

    BLEDevice::init(DEVICE_NAME);

    String macAddress =
        BLEDevice::getAddress().toString().c_str();

    Serial.print("Device Name : ");
    Serial.println(DEVICE_NAME);

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

    displayLogoIdle();

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

    if (pendingQuestion)
    {
        pendingQuestion = false;

        if (quizEnded)
        {
            quizEnded = false;
        }

        Serial.print("New question: ");
        Serial.println(currentQuestionID);

        drawQuestionScreen();
        drawQuizClock(true);

        state = STATE_QUESTION;
    }

    if (pendingAck)
    {
        pendingAck = false;

        handleAck();
    }

    // -------------------------------------------------
    // 2. Clocks
    // -------------------------------------------------

    if (!quizEnded && quizDeadlineSet && state != STATE_RESULT)
    {
        drawQuizClock(false);
    }

    // -------------------------------------------------
    // 3. Timeouts
    // -------------------------------------------------

    if (state == STATE_REGISTERING &&
        millis() - registerSentAt > 6000)
    {
        displayMessage(
            "NO REPLY",
            ST77XX_RED,
            "Gateway did not reply.",
            ""
        );

        delay(1500);

        // Entry stays open; let the student retry.
        state = STATE_LOBBY;
        displayLobbyEntry();
    }

    if (state == STATE_ANSWER_SENT &&
        millis() - answerSentAt > 5000)
    {
        drawQuestionScreen();
        drawQuizClock(true);

        state = STATE_QUESTION;
    }

    // -------------------------------------------------
    // 4. Keypad (state-aware)
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

                    displayStudentID();
                }
            }
            else if (key == '*')
            {
                studentID = "";

                displayStudentID();
            }
            else if (key == '#')
            {
                if (studentID.length() == 0)
                {
                    displayMessage(
                        "NO ID",
                        ST77XX_RED,
                        "Enter your student ID first.",
                        ""
                    );

                    delay(1200);

                    displayLobbyEntry();
                }
                else if (
                    idPrefix.length() > 0 &&
                    !studentID.startsWith(idPrefix)
                )
                {
                    displayMessage(
                        "WRONG ID",
                        ST77XX_RED,
                        "ID must start with:",
                        idPrefix
                    );

                    delay(1500);

                    displayLobbyEntry();
                }
                else if (
                    idLength > 0 &&
                    (int)studentID.length() != idLength
                )
                {
                    displayMessage(
                        "WRONG ID",
                        ST77XX_RED,
                        "ID must be exactly",
                        String(idLength) + " digits"
                    );

                    delay(1500);

                    displayLobbyEntry();
                }
                else if (sendRegistration())
                {
                    state = STATE_REGISTERING;

                    displayMessage(
                        "JOINING",
                        ST77XX_CYAN,
                        "Registering ID: " + studentID,
                        ""
                    );
                }
            }
        }

        // ----- Question: answer -----

        else if (state == STATE_QUESTION)
        {
            if (key >= 'A' && key <= 'D')
            {
                highlightOption(key);

                if (sendAnswer(key))
                {
                    state = STATE_ANSWER_SENT;
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
