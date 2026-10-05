#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

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

// Logical display size after rotation:
// WIDTH  = 160
// HEIGHT = 128

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
    ROW1,
    ROW2,
    ROW3,
    ROW4
};

const uint8_t colPins[4] = {
    COL1,
    COL2,
    COL3,
    COL4
};

const char keyMap[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}
};

// =====================================================
// STUDENT ID
// =====================================================

String studentID = "";

const size_t MAX_ID_LENGTH = 10;

// =====================================================
// CURRENT QUESTION
// =====================================================

// Question ID received from Raspberry Pi.
// Example: Q01, Q02, Q03...

String currentQuestionID = "";

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
// BLE SERVER CALLBACK
// =====================================================

class ServerCallbacks : public BLEServerCallbacks
{
    void onConnect(BLEServer* server) override
    {
        deviceConnected = true;

        Serial.println();
        Serial.println("================================");
        Serial.println("BLE GATEWAY CONNECTED");
        Serial.println("================================");
    }

    void onDisconnect(BLEServer* server) override
    {
        deviceConnected = false;

        Serial.println();
        Serial.println("================================");
        Serial.println("BLE GATEWAY DISCONNECTED");
        Serial.println("================================");

        delay(100);

        BLEDevice::startAdvertising();

        Serial.println("BLE advertising restarted.");
    }
};

// =====================================================
// ACK CALLBACK
// Raspberry Pi -> ESP32
// =====================================================

class ACKCallbacks : public BLECharacteristicCallbacks
{
    void onWrite(BLECharacteristic* characteristic) override
    {
        String value = characteristic->getValue().c_str();

        Serial.println();
        Serial.println("========== BLE RX ==========");
        Serial.print("ACK: ");
        Serial.println(value);
        Serial.println("============================");

        // -------------------------------------------------
        // 160x128 LANDSCAPE UI
        // -------------------------------------------------

        tft.fillScreen(ST77XX_BLACK);

        tft.setTextColor(ST77XX_GREEN);
        tft.setTextSize(2);
        tft.setCursor(25, 10);
        tft.println("REGISTERED");

        tft.setTextColor(ST77XX_WHITE);
        tft.setTextSize(1);
        tft.setCursor(10, 45);
        tft.println("Student ID:");

        tft.setTextColor(ST77XX_YELLOW);
        tft.setTextSize(2);
        tft.setCursor(10, 60);
        tft.println(studentID);

        tft.setTextColor(ST77XX_CYAN);
        tft.setTextSize(1);
        tft.setCursor(68, 105);
        tft.println("READY");
    }
};

// =====================================================
// QUESTION CALLBACK
// Raspberry Pi -> ESP32
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

        // -------------------------------------------------
        // Extract question_id
        // -------------------------------------------------

        int idStart = packet.indexOf("\"question_id\":\"");

        if (idStart >= 0)
        {
            idStart += strlen("\"question_id\":\"");

            int idEnd = packet.indexOf("\"", idStart);

            if (idEnd > idStart)
            {
                currentQuestionID = packet.substring(
                    idStart,
                    idEnd
                );

                Serial.print("Current Question ID: ");
                Serial.println(currentQuestionID);
            }
        }

        // -------------------------------------------------
        // Extract question text
        // -------------------------------------------------

        String questionText = "";

        int questionStart =
            packet.indexOf("\"question\":\"");

        if (questionStart >= 0)
        {
            questionStart += strlen("\"question\":\"");

            int questionEnd =
                packet.indexOf("\"", questionStart);

            if (questionEnd > questionStart)
            {
                questionText =
                    packet.substring(
                        questionStart,
                        questionEnd
                    );
            }
        }

        // -------------------------------------------------
        // Extract options
        // -------------------------------------------------

        String optionA = "";
        String optionB = "";
        String optionC = "";
        String optionD = "";

        int posA = packet.indexOf("\"A\":\"");

        if (posA >= 0)
        {
            posA += strlen("\"A\":\"");

            int endA = packet.indexOf("\"", posA);

            if (endA > posA)
                optionA = packet.substring(posA, endA);
        }

        int posB = packet.indexOf("\"B\":\"");

        if (posB >= 0)
        {
            posB += strlen("\"B\":\"");

            int endB = packet.indexOf("\"", posB);

            if (endB > posB)
                optionB = packet.substring(posB, endB);
        }

        int posC = packet.indexOf("\"C\":\"");

        if (posC >= 0)
        {
            posC += strlen("\"C\":\"");

            int endC = packet.indexOf("\"", posC);

            if (endC > posC)
                optionC = packet.substring(posC, endC);
        }

        int posD = packet.indexOf("\"D\":\"");

        if (posD >= 0)
        {
            posD += strlen("\"D\":\"");

            int endD = packet.indexOf("\"", posD);

            if (endD > posD)
                optionD = packet.substring(posD, endD);
        }

        // -------------------------------------------------
        // Serial debug
        // -------------------------------------------------

        Serial.println("------ PARSED QUESTION ------");

        Serial.print("Question ID: ");
        Serial.println(currentQuestionID);

        Serial.print("Question: ");
        Serial.println(questionText);

        Serial.print("A: ");
        Serial.println(optionA);

        Serial.print("B: ");
        Serial.println(optionB);

        Serial.print("C: ");
        Serial.println(optionC);

        Serial.print("D: ");
        Serial.println(optionD);

        Serial.println("-----------------------------");

        // -------------------------------------------------
        // DISPLAY
        // 160 x 128 LANDSCAPE
        // -------------------------------------------------

        tft.fillScreen(ST77XX_BLACK);

        // -------------------------------------------------
        // Header
        // -------------------------------------------------

        tft.setTextColor(ST77XX_CYAN);
        tft.setTextSize(1);

        tft.setCursor(5, 5);
        tft.print("QUESTION ");

        tft.setTextColor(ST77XX_YELLOW);
        tft.print(currentQuestionID);

        // -------------------------------------------------
        // Question text
        // -------------------------------------------------

        tft.setTextColor(ST77XX_WHITE);
        tft.setTextSize(1);

        int x = 5;
        int y = 20;

        const int maxCharsPerLine = 26;

        String remaining = questionText;

        while (remaining.length() > 0 && y < 65)
        {
            int lineLength = maxCharsPerLine;

            if (remaining.length() < lineLength)
            {
                lineLength = remaining.length();
            }

            // -------------------------------------------------
            // Don't split a word if possible.
            // -------------------------------------------------

            if (lineLength < remaining.length())
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

            remaining =
                remaining.substring(lineLength);

            remaining.trim();

            y += 10;
        }

        // -------------------------------------------------
        // Options
        // -------------------------------------------------

        tft.setTextColor(ST77XX_GREEN);

        tft.setCursor(5, 70);
        tft.print("A. ");
        tft.println(optionA);

        tft.setCursor(5, 84);
        tft.print("B. ");
        tft.println(optionB);

        tft.setCursor(5, 98);
        tft.print("C. ");
        tft.println(optionC);

        tft.setCursor(5, 112);
        tft.print("D. ");
        tft.println(optionD);
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
            digitalWrite(
                rowPins[i],
                HIGH
            );
        }

        digitalWrite(
            rowPins[row],
            LOW
        );

        for (int col = 0; col < 4; col++)
        {
            if (digitalRead(colPins[col]) == LOW)
            {
                delay(20);

                // Confirm the key is still pressed.
                if (digitalRead(colPins[col]) != LOW)
                {
                    continue;
                }

                // Wait until release so one press = one key event.
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
// DISPLAY STUDENT ID
// =====================================================

void displayStudentID()
{
    // 160x128 landscape
    // Clear full-width student ID area.
    tft.fillRect(
        0,
        42,
        160,
        38,
        ST77XX_BLACK
    );

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(10, 45);
    tft.println("Student ID:");

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 58);
    tft.println(studentID);

    Serial.print("Student ID: ");
    Serial.println(studentID);
}

// =====================================================
// DISPLAY READY
// =====================================================

void displayReady()
{
    tft.fillScreen(ST77XX_BLACK);

    // -------------------------------------------------
    // Header
    // -------------------------------------------------

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setCursor(45, 8);
    tft.println("PulseNet");

    // -------------------------------------------------
    // Student ID
    // -------------------------------------------------

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(10, 35);
    tft.println("Enter Student ID:");

    displayStudentID();

    // -------------------------------------------------
    // Key instructions
    // -------------------------------------------------

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(1);

    tft.setCursor(10, 95);
    tft.println("* = Clear");

    tft.setCursor(10, 110);
    tft.println("# = Confirm");
}

// =====================================================
// DISPLAY REGISTRATION STATUS
// =====================================================

void displayRegistrationStatus(
    const char* status
)
{
    tft.fillScreen(ST77XX_BLACK);

    // -------------------------------------------------
    // Header
    // -------------------------------------------------

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(2);
    tft.setCursor(35, 12);
    tft.println("REGISTER");

    // -------------------------------------------------
    // Student ID
    // -------------------------------------------------

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(10, 45);
    tft.println("Student ID:");

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(10, 60);
    tft.println(studentID);

    // -------------------------------------------------
    // Status
    // -------------------------------------------------

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(1);
    tft.setCursor(10, 100);
    tft.println(status);
}

// =====================================================
// SEND REGISTRATION
// ESP32 -> Raspberry Pi
// =====================================================

bool sendRegistration()
{
    Serial.println();
    Serial.println("========== REGISTRATION ==========");
    Serial.print("BLE connected: ");
    Serial.println(
        deviceConnected ? "YES" : "NO"
    );

    if (!deviceConnected)
    {
        Serial.println(
            "ERROR: Raspberry Pi is not connected."
        );

        Serial.println(
            "Registration cannot be sent."
        );

        displayRegistrationStatus(
            "BLE NOT CONNECTED"
        );

        return false;
    }

    if (registrationCharacteristic == nullptr)
    {
        Serial.println(
            "ERROR: Registration characteristic is NULL."
        );

        displayRegistrationStatus(
            "BLE ERROR"
        );

        return false;
    }

    String macAddress =
        BLEDevice::getAddress()
            .toString()
            .c_str();

    String packet =
        "{\"type\":\"REGISTER\","
        "\"student_id\":\"" +
        studentID +
        "\","
        "\"device_name\":\"" DEVICE_NAME "\","
        "\"device_mac\":\"" +
        macAddress +
        "\"}";

    Serial.println(
        "Sending registration packet:"
    );

    Serial.println(packet);

    registrationCharacteristic->setValue(
        packet.c_str()
    );

    registrationCharacteristic->notify();

    Serial.println(
        "Registration notify sent."
    );

    Serial.println(
        "=================================="
    );

    displayRegistrationStatus(
        "SENT TO GATEWAY"
    );

    return true;
}

// =====================================================
// SEND ANSWER
// ESP32 -> Raspberry Pi
// =====================================================

bool sendAnswer(char answer)
{
    if (!deviceConnected)
    {
        Serial.println(
            "ERROR: BLE gateway not connected."
        );

        return false;
    }

    if (answerCharacteristic == nullptr)
    {
        Serial.println(
            "ERROR: Answer characteristic is NULL."
        );

        return false;
    }

    // -------------------------------------------------
    // Make sure a question has been received
    // -------------------------------------------------

    if (currentQuestionID.length() == 0)
    {
        Serial.println(
            "ERROR: No current question."
        );

        Serial.println(
            "Cannot send answer."
        );

        return false;
    }

    // -------------------------------------------------
    // Build ANSWER packet
    // -------------------------------------------------

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

    Serial.println();
    Serial.println("========== BLE TX ==========");
    Serial.println("Answer packet:");
    Serial.println(packet);
    Serial.println("============================");

    answerCharacteristic->setValue(
        packet.c_str()
    );

    answerCharacteristic->notify();

    return true;
}

// =====================================================
// INITIALIZE BLE
// =====================================================

void setupBLE()
{
    Serial.println();
    Serial.println("Starting BLE...");

    BLEDevice::init(
        DEVICE_NAME
    );

    String macAddress =
        BLEDevice::getAddress()
            .toString()
            .c_str();

    Serial.print("Device Name : ");
    Serial.println(DEVICE_NAME);

    Serial.print("BLE MAC     : ");
    Serial.println(macAddress);

    bleServer =
        BLEDevice::createServer();

    bleServer->setCallbacks(
        new ServerCallbacks()
    );

    BLEService* service =
        bleServer->createService(
            PULSENET_SERVICE_UUID
        );

    // -------------------------------------------------
    // ESP32 -> Pi
    // Registration
    // -------------------------------------------------

    registrationCharacteristic =
        service->createCharacteristic(
            REGISTRATION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    registrationCharacteristic->addDescriptor(
        new BLE2902()
    );

    // -------------------------------------------------
    // Pi -> ESP32
    // Question
    // -------------------------------------------------

    questionCharacteristic =
        service->createCharacteristic(
            QUESTION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    questionCharacteristic->setCallbacks(
        new QuestionCallbacks()
    );

    // -------------------------------------------------
    // ESP32 -> Pi
    // Answer
    // -------------------------------------------------

    answerCharacteristic =
        service->createCharacteristic(
            ANSWER_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    answerCharacteristic->addDescriptor(
        new BLE2902()
    );

    // -------------------------------------------------
    // Pi -> ESP32
    // ACK
    // -------------------------------------------------

    ackCharacteristic =
        service->createCharacteristic(
            ACK_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    ackCharacteristic->setCallbacks(
        new ACKCallbacks()
    );

    // -------------------------------------------------
    // Start BLE service
    // -------------------------------------------------

    service->start();

    BLEAdvertising* advertising =
        BLEDevice::getAdvertising();

    advertising->addServiceUUID(
        PULSENET_SERVICE_UUID
    );

    advertising->setScanResponse(
        true
    );

    advertising->setMinPreferred(
        0x06
    );

    advertising->setMinPreferred(
        0x12
    );

    BLEDevice::startAdvertising();

    Serial.println(
        "BLE initialized."
    );

    Serial.println(
        "Advertising started."
    );

    Serial.println();
}

// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    delay(1000);

    Serial.println();
    Serial.println(
        "================================"
    );

    Serial.println(
        "PulseNet Student Device"
    );

    Serial.println(
        "ESP32 + ST7735S 160x128 + Keypad + BLE"
    );

    Serial.println(
        "================================"
    );

    // -------------------------------------------------
    // TFT
    // -------------------------------------------------

    Serial.println(
        "Starting ST7735S 160x128 landscape..."
    );

    /*
     * The physical ST7735 display is 128x160.
     *
     * Rotation 1 changes the logical orientation to:
     *
     * WIDTH  = 160
     * HEIGHT = 128
     */

    tft.initR(
        INITR_BLACKTAB
    );

    tft.setRotation(1);

    tft.fillScreen(
        ST77XX_BLACK
    );

    Serial.print("TFT width  : ");
    Serial.println(tft.width());

    Serial.print("TFT height : ");
    Serial.println(tft.height());

    Serial.println(
        "TFT initialized in landscape mode"
    );

    // -------------------------------------------------
    // Keypad
    // -------------------------------------------------

    for (int i = 0; i < 4; i++)
    {
        pinMode(
            rowPins[i],
            OUTPUT
        );

        digitalWrite(
            rowPins[i],
            HIGH
        );
    }

    for (int i = 0; i < 4; i++)
    {
        pinMode(
            colPins[i],
            INPUT_PULLUP
        );
    }

    Serial.println(
        "Keypad initialized"
    );

    // -------------------------------------------------
    // BLE
    // -------------------------------------------------

    setupBLE();

    // -------------------------------------------------
    // Start screen
    // -------------------------------------------------

    displayReady();

    Serial.println(
        "System ready."
    );

    Serial.println(
        "Enter Student ID..."
    );
}

// =====================================================
// LOOP
// =====================================================

void loop()
{
    char key = readKeypad();

    if (key != '\0')
    {
        Serial.print(
            "Key pressed: "
        );

        Serial.println(key);

        // -------------------------------------------------
        // NUMBER
        // -------------------------------------------------

        if (
            key >= '0' &&
            key <= '9'
        )
        {
            if (
                studentID.length()
                < MAX_ID_LENGTH
            )
            {
                studentID += key;

                displayStudentID();
            }
            else
            {
                Serial.println(
                    "Student ID: maximum length reached."
                );
            }
        }

        // -------------------------------------------------
        // CLEAR
        // -------------------------------------------------

        else if (key == '*')
        {
            studentID = "";

            displayStudentID();

            Serial.println(
                "Student ID cleared"
            );
        }

        // -------------------------------------------------
        // CONFIRM + SEND REGISTER
        // -------------------------------------------------

        else if (key == '#')
        {
            if (
                studentID.length() == 0
            )
            {
                Serial.println(
                    "Student ID is empty. Nothing to send."
                );

                displayRegistrationStatus(
                    "ENTER STUDENT ID"
                );

                delay(1000);

                displayReady();
            }
            else
            {
                Serial.println(
                    "=========================="
                );

                Serial.print(
                    "Student ID confirmed: "
                );

                Serial.println(
                    studentID
                );

                Serial.println(
                    "=========================="
                );

                sendRegistration();
            }
        }

        // -------------------------------------------------
        // ANSWER
        // -------------------------------------------------

        else if (
            key >= 'A' &&
            key <= 'D'
        )
        {
            Serial.print(
                "Answer selected: "
            );

            Serial.println(key);

            // -------------------------------------------------
            // 160x128 LANDSCAPE ANSWER SCREEN
            // -------------------------------------------------

            tft.fillScreen(
                ST77XX_BLACK
            );

            tft.setTextColor(
                ST77XX_WHITE
            );

            tft.setTextSize(1);

            tft.setCursor(
                45,
                15
            );

            tft.println(
                "ANSWER SELECTED"
            );

            tft.setTextColor(
                ST77XX_YELLOW
            );

            tft.setTextSize(4);

            tft.setCursor(
                68,
                45
            );

            tft.println(key);

            // -------------------------------------------------
            // Send answer together with currentQuestionID.
            // BLE logic unchanged.
            // -------------------------------------------------

            sendAnswer(key);

            delay(1000);

            displayReady();
        }
    }

    delay(10);
}