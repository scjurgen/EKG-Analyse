#include <SAMDTimerInterrupt.h>
#include <SD.h>
#include <RTCZero.h>

RTCZero rtc;
// trace ekg will output data on the serial interface
// otherwise the data will be written to SD card only and the serial interface
// will just report some statistics stuff
#define TRACE_EKG 0
#define CHUNKMAXWRITE 128 // limit files to 1MB
int chunksWritten = 0;

#if TRACE_EGK == 1
#define CHUNKSIZE 256
#else
#define CHUNKSIZE 4096
#endif

uint16_t values[2][CHUNKSIZE]; // double buffer

// The chip select pin. For the MKRZero it is SDCARD_SS_PIN
const int SD_CHIP_SELECT = SDCARD_SS_PIN;

bool SDCardReady = false;

// pins of the leads off detection ECG module connected to the Arduino
#define LO_PLUS_PIN 1
#define LO_MINUS_PIN 2

/*
 * Warning signals:
 *
 */

// led pin for warning signals
#define LED_WARNING_PIN 11

SAMDTimer ITimer(TIMER_TC3);

void dateTime(uint16_t *date, uint16_t *time)
{
    *date = FAT_DATE(rtc.getYear(), rtc.getMonth(), rtc.getDay());
    *time = FAT_TIME(rtc.getHours(), rtc.getMinutes(), rtc.getSeconds());
}

void openSDCard()
{
    SDCardReady = SD.begin(SD_CHIP_SELECT);
    if (SDCardReady)
    {
        Serial.println("SD card is ready\n");
    }
    else
    {
        Serial.println("No SD card?\n");
    }
    delay(1000);
}

extern void measure();

int filecnt = 0;

void createCountFile()
{
    char number[32];
    SD.remove("COUNT.TXT");
    File dataFile = SD.open("COUNT.TXT", FILE_WRITE);
    sprintf(number, "%d", filecnt);
    if (dataFile)
    {
        dataFile.write(number, strlen(number));
        dataFile.close();
        Serial.print("Count file written: ");
        Serial.println(filecnt);
    }
    else
    {
        Serial.println("ERROR: Count file not written: ");
        SDCardReady = false;
    }
}

void readFileCount()
{
    File dataFile = SD.open("COUNT.TXT", FILE_READ);
    if (dataFile)
    {
        char number[32];
        dataFile.read(number, sizeof(number) - 1);
        dataFile.close();
        filecnt = atoi(number);
        filecnt++;
    }
    createCountFile();
    char logFile[32];
    sprintf(logFile, "EKG_%04d.BIN", filecnt);
    SD.remove(logFile);
    chunksWritten = 0;
}

void setup()
{
    Serial.begin(115200);
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(LO_PLUS_PIN, INPUT);  // Setup for leads off detection LO +
    pinMode(LO_MINUS_PIN, INPUT); // Setup for leads off detection LO -
    pinMode(LED_WARNING_PIN, OUTPUT);
    rtc.begin();
    for (int i = 0; i < 4; ++i)
    {
        digitalWrite(LED_WARNING_PIN, 1);
        delay(100);
        digitalWrite(LED_WARNING_PIN, 0);
        delay(900);
    }
    Serial.println("SD card check\n");
    SdFile::dateTimeCallback(dateTime);
    openSDCard();
    readFileCount();
    if (ITimer.attachInterruptInterval(2 * 1000, measure)) // 2000 ysecs = 500Hz
    {
        Serial.print(F("Starting ITimer OK, millis() = "));
        Serial.println(millis());
    }
    else
        Serial.println(F("Can't set ITimer. Select another freq. or timer"));
}

volatile int  currentWritePos = 0;
volatile int  currentBuffer   = 0;
volatile bool bufferReady     = false;
volatile int  bufferWrittenTo = 0;

bool    noData  = true;
int16_t cntData = 0;

void measure()
{
    if ((digitalRead(LO_PLUS_PIN) == 1) || (digitalRead(LO_MINUS_PIN) == 1))
    {
        noData = true;
        digitalWrite(LED_WARNING_PIN, cntData < 10);
        cntData++;
        if (cntData >= 20)
            cntData = 0;
        return;
    }
    noData = false;

    uint16_t value = analogRead(A6);

    values[currentBuffer][currentWritePos] = (uint16_t) value;
    currentWritePos++;
    digitalWrite(LED_WARNING_PIN, value > 650);

    if (currentWritePos >= CHUNKSIZE)
    {
        bufferWrittenTo = currentBuffer;
        currentBuffer   = 1 - currentBuffer;
        currentWritePos = 0;
        bufferReady     = true;
    }
}

unsigned long nextShow = 0;

void loop()
{
    if (noData)
    {
        digitalWrite(LED_BUILTIN, 1);
        delay(10);
        digitalWrite(LED_BUILTIN, 0);
        delay(50);
    }
    if (!SDCardReady)
    {
        digitalWrite(LED_WARNING_PIN, 1);
        delay(250);
        digitalWrite(LED_WARNING_PIN, 0);
        delay(50);
    }
    else
    {
        // digitalWrite(LED_WARNING_PIN, 0);
    }
    if (millis() >= nextShow)
    {
#if !TRACE_EKG
        Serial.print("B:");
        Serial.print(currentBuffer);
        Serial.print(" Pos:");
        Serial.print(currentWritePos);
        Serial.print(" SD:");
        Serial.print(SDCardReady);
        Serial.println(" #");
        nextShow = millis() + 1000;
#endif
        digitalWrite(LED_BUILTIN, 1);
        delay(50);
        digitalWrite(LED_BUILTIN, 0);
    }
    if (bufferReady)
    {
        bufferReady = false;
        if (SDCardReady)
        {
            digitalWrite(LED_BUILTIN, 1);

            int  bufferIndex = bufferWrittenTo;
            char logFile[32];
            sprintf(logFile, "EKG_%04d.BIN", filecnt);
#if TRACE_EKG == 0
            Serial.print("chunk count: ");
            Serial.print(chunksWritten);
            Serial.print(" Writing new set: ");
            Serial.println(logFile);
#else
            for (int n = 0; n < CHUNKSIZE; n++)
            {
                Serial.println(values[bufferIndex][n]);
            }
#endif
            File dataFile = SD.open(logFile, FILE_WRITE);
            if (dataFile)
            {
                dataFile.write((uint8_t *) &values[bufferIndex][0], CHUNKSIZE * sizeof(uint16_t));
                dataFile.close();
            }
            else
            {
                SDCardReady = false;
            }
            chunksWritten++;
            if (chunksWritten >= CHUNKMAXWRITE)
            {
                filecnt++;
                createCountFile();
                chunksWritten = 0;
            }
            digitalWrite(LED_BUILTIN, 0);
            delay(100);
        }
        else
        {
            Serial.println("SD card not working\n");
            SDCardReady = false;
            for (int i = 0; i < 15; ++i)
            {
                digitalWrite(LED_WARNING_PIN, 1);
                delay(50);
                digitalWrite(LED_WARNING_PIN, 0);
                delay(100);
            }
            openSDCard();
        }
    }
}
