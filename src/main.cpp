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
// TFT
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

const uint8_t rowPins[4] = {ROW1, ROW2, ROW3, ROW4};
const uint8_t colPins[4] = {COL1, COL2, COL3, COL4};

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

        tft.fillScreen(ST77XX_BLACK);

        tft.setTextColor(ST77XX_GREEN);
        tft.setTextSize(2);
        tft.setCursor(20, 10);
        tft.println("REGISTERED");

        tft.setTextColor(ST77XX_WHITE);
        tft.setTextSize(1);
        tft.setCursor(5, 45);
        tft.println("Student ID:");

        tft.setTextColor(ST77XX_YELLOW);
        tft.setTextSize(2);
        tft.setCursor(5, 60);
        tft.println(studentID);

        tft.setTextColor(ST77XX_CYAN);
        tft.setTextSize(1);
        tft.setCursor(35, 100);
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
        String question = characteristic->getValue().c_str();

        Serial.println();
        Serial.println("========== QUESTION ==========");
        Serial.println(question);
        Serial.println("==============================");

        tft.fillScreen(ST77XX_BLACK);

        tft.setTextColor(ST77XX_CYAN);
        tft.setTextSize(1);
        tft.setCursor(5, 5);
        tft.println("QUESTION");

        tft.setTextColor(ST77XX_WHITE);
        tft.setTextSize(1);
        tft.setCursor(5, 25);
        tft.println(question);
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
            digitalWrite(rowPins[i], HIGH);

        digitalWrite(rowPins[row], LOW);

        for (int col = 0; col < 4; col++)
        {
            if (digitalRead(colPins[col]) == LOW)
            {
                delay(20);

                // Confirm the key is still pressed.
                if (digitalRead(colPins[col]) != LOW)
                    continue;

                // Wait until release so one press = one key event.
                while (digitalRead(colPins[col]) == LOW)
                    delay(1);

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
    tft.fillRect(0, 42, 128, 38, ST77XX_BLACK);

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(5, 45);
    tft.println("Student ID:");

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(5, 58);
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

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(2);
    tft.setCursor(15, 10);
    tft.println("PulseNet");

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(5, 35);
    tft.println("Enter Student ID:");

    displayStudentID();

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(1);

    tft.setCursor(5, 95);
    tft.println("* = Clear");

    tft.setCursor(5, 110);
    tft.println("# = Confirm");
}

// =====================================================
// DISPLAY SENDING
// =====================================================

void displayRegistrationStatus(const char* status)
{
    tft.fillScreen(ST77XX_BLACK);

    tft.setTextColor(ST77XX_CYAN);
    tft.setTextSize(2);
    tft.setCursor(8, 15);
    tft.println("REGISTER");

    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(1);
    tft.setCursor(5, 50);
    tft.println("Student ID:");

    tft.setTextColor(ST77XX_YELLOW);
    tft.setTextSize(2);
    tft.setCursor(5, 65);
    tft.println(studentID);

    tft.setTextColor(ST77XX_GREEN);
    tft.setTextSize(1);
    tft.setCursor(5, 100);
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
    Serial.println(deviceConnected ? "YES" : "NO");

    if (!deviceConnected)
    {
        Serial.println("ERROR: Raspberry Pi is not connected.");
        Serial.println("Registration cannot be sent.");

        displayRegistrationStatus("BLE NOT CONNECTED");
        return false;
    }

    if (registrationCharacteristic == nullptr)
    {
        Serial.println("ERROR: Registration characteristic is NULL.");
        displayRegistrationStatus("BLE ERROR");
        return false;
    }

    String macAddress = BLEDevice::getAddress().toString().c_str();

    String packet =
        "{\"type\":\"REGISTER\","
        "\"student_id\":\"" + studentID + "\","
        "\"device_name\":\"" DEVICE_NAME "\","
        "\"device_mac\":\"" + macAddress + "\"}";

    Serial.println("Sending registration packet:");
    Serial.println(packet);

    registrationCharacteristic->setValue(packet.c_str());
    registrationCharacteristic->notify();

    Serial.println("Registration notify sent.");
    Serial.println("==================================");

    displayRegistrationStatus("SENT TO GATEWAY");

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
        Serial.println("ERROR: BLE gateway not connected.");
        return false;
    }

    if (answerCharacteristic == nullptr)
    {
        Serial.println("ERROR: Answer characteristic is NULL.");
        return false;
    }

    String packet =
        "{\"type\":\"ANSWER\","
        "\"student_id\":\"" + studentID + "\","
        "\"answer\":\"" + String(answer) + "\"}";

    Serial.println();
    Serial.println("========== BLE TX ==========");
    Serial.println("Answer packet:");
    Serial.println(packet);
    Serial.println("============================");

    answerCharacteristic->setValue(packet.c_str());
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

    BLEDevice::init(DEVICE_NAME);

    String macAddress = BLEDevice::getAddress().toString().c_str();

    Serial.print("Device Name : ");
    Serial.println(DEVICE_NAME);

    Serial.print("BLE MAC     : ");
    Serial.println(macAddress);

    bleServer = BLEDevice::createServer();
    bleServer->setCallbacks(new ServerCallbacks());

    BLEService* service =
        bleServer->createService(PULSENET_SERVICE_UUID);

    // ESP32 -> Pi
    registrationCharacteristic =
        service->createCharacteristic(
            REGISTRATION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    registrationCharacteristic->addDescriptor(new BLE2902());

    // Pi -> ESP32
    questionCharacteristic =
        service->createCharacteristic(
            QUESTION_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    questionCharacteristic->setCallbacks(new QuestionCallbacks());

    // ESP32 -> Pi
    answerCharacteristic =
        service->createCharacteristic(
            ANSWER_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_NOTIFY
        );

    answerCharacteristic->addDescriptor(new BLE2902());

    // Pi -> ESP32
    ackCharacteristic =
        service->createCharacteristic(
            ACK_CHAR_UUID,
            BLECharacteristic::PROPERTY_READ |
            BLECharacteristic::PROPERTY_WRITE
        );

    ackCharacteristic->setCallbacks(new ACKCallbacks());

    service->start();

    BLEAdvertising* advertising = BLEDevice::getAdvertising();

    advertising->addServiceUUID(PULSENET_SERVICE_UUID);
    advertising->setScanResponse(true);
    advertising->setMinPreferred(0x06);
    advertising->setMinPreferred(0x12);

    BLEDevice::startAdvertising();

    Serial.println("BLE initialized.");
    Serial.println("Advertising started.");
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
    Serial.println("================================");
    Serial.println("PulseNet Student Device");
    Serial.println("ESP32 + ST7735S + Keypad + BLE");
    Serial.println("================================");

    // TFT
    Serial.println("Starting ST7735S 128x128...");

    tft.initR(INITR_144GREENTAB);
    tft.setRotation(0);
    tft.fillScreen(ST77XX_BLACK);

    Serial.println("TFT initialized");

    // Keypad
    for (int i = 0; i < 4; i++)
    {
        pinMode(rowPins[i], OUTPUT);
        digitalWrite(rowPins[i], HIGH);
    }

    for (int i = 0; i < 4; i++)
        pinMode(colPins[i], INPUT_PULLUP);

    Serial.println("Keypad initialized");

    // BLE
    setupBLE();

    // Start screen
    displayReady();

    Serial.println("System ready.");
    Serial.println("Enter Student ID...");
}

// =====================================================
// LOOP
// =====================================================

void loop()
{
    char key = readKeypad();

    if (key != '\0')
    {
        Serial.print("Key pressed: ");
        Serial.println(key);

        // NUMBER
        if (key >= '0' && key <= '9')
        {
            if (studentID.length() < MAX_ID_LENGTH)
            {
                studentID += key;
                displayStudentID();
            }
            else
            {
                Serial.println("Student ID: maximum length reached.");
            }
        }

        // CLEAR
        else if (key == '*')
        {
            studentID = "";
            displayStudentID();
            Serial.println("Student ID cleared");
        }

        // CONFIRM + SEND REGISTER
        else if (key == '#')
        {
            if (studentID.length() == 0)
            {
                Serial.println("Student ID is empty. Nothing to send.");
                displayRegistrationStatus("ENTER STUDENT ID");
                delay(1000);
                displayReady();
            }
            else
            {
                Serial.println("==========================");
                Serial.print("Student ID confirmed: ");
                Serial.println(studentID);
                Serial.println("==========================");

                sendRegistration();
            }
        }

        // ANSWER
        else if (key >= 'A' && key <= 'D')
        {
            Serial.print("Answer selected: ");
            Serial.println(key);

            tft.fillScreen(ST77XX_BLACK);

            tft.setTextColor(ST77XX_WHITE);
            tft.setTextSize(1);
            tft.setCursor(10, 15);
            tft.println("ANSWER SELECTED");

            tft.setTextColor(ST77XX_YELLOW);
            tft.setTextSize(4);
            tft.setCursor(50, 45);
            tft.println(key);

            sendAnswer(key);

            delay(1000);
            displayReady();
        }
    }

    delay(10);
}