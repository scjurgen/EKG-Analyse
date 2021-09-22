
#include <SAMDTimerInterrupt.h>
#include <SD.h>

// The chip select pin.
// For MKRZero it's SDCARD_SS_PIN
// for mem shield, it's 4
const int  SD_CHIP_SELECT = SDCARD_SS_PIN;

// whether or not the SD card initialized:
bool SDAvailable = false;


SAMDTimer ITimer(TIMER_TC3);

void openSDCard()
{
  SDAvailable = SD.begin(SD_CHIP_SELECT);
  if (SDAvailable) {
    Serial.println("SD card is ready\n");
  }
  else
  {
    Serial.println("No SD card?\n");
  }
  delay(1000);
}


extern void measure();
#define CHUNKMAXWRITE 30

int chunksWritten = 0;
int filecnt=0;

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
        SDAvailable = false;
    }
}

void readFileCount()
{
    File dataFile = SD.open("COUNT.TXT", FILE_READ);
    if (dataFile)
    {
        char number[32];
        dataFile.read(number, sizeof(number)-1);
        dataFile.close();
        filecnt = atoi(number);
        filecnt++;
    }
    createCountFile();
    char logFile[32];
    sprintf(logFile, "EKG_%04d.BIN", filecnt);
    SD.remove(logFile);
    chunksWritten=0;
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(2, INPUT); // Setup for leads off detection LO +
  pinMode(1, INPUT); // Setup for leads off detection LO -
  delay(4000);
  Serial.println("SD card check\n");
  openSDCard();
  readFileCount();
  if (ITimer.attachInterruptInterval(4 * 1000, measure))
  {
    Serial.print(F("Starting ITimer OK, millis() = ")); 
    Serial.println(millis());
  }
  else
    Serial.println(F("Can't set ITimer. Select another freq. or timer"));
}

class  FilterBeLp250Hz
{
    public:
        FilterBeLp250Hz()
        {
            v[0]=0.0;
            v[1]=0.0;
            v[2]=0.0;
        }
    private:
        float v[3];
    public:
        float step(float x) //class II 
        {
            v[0] = v[1];
            v[1] = v[2];
            v[2] = (2.472202237914441769e-1 * x)
                 + (-0.07334140686228005079 * v[0])
                 + (0.08446051169650338475 * v[1]);
            return 
                 (v[0] + v[2])
                +2 * v[1];
        }
};

class  FilterBeLp1000Hz
{
  public:
    FilterBeLp1000Hz()
    {
      v[0] = 0.0;
      v[1] = 0.0;
      v[2] = 0.0;
    }
  private:
    float v[3];
  public:
    float step(float x) //class II
    {
      v[0] = v[1];
      v[1] = v[2];
      v[2] = (8.468721060604257958e-3 * x)
             + (-0.70695758802726427206 * v[0])
             + (1.67308270378484724716 * v[1]);
      return
        (v[0] + v[2])
        + 2 * v[1];
    }
};

FilterBeLp250Hz filter[2];

volatile int currentWritePos = 0;
volatile int currentBuffer = 0;
volatile bool bufferReady = false;
volatile int bufferWrittenTo = 0;
#define CHUNKSIZE 5000
uint16_t values[2][CHUNKSIZE];

bool noData = true;

void measure()
{
    if ((digitalRead(2) == 1) || (digitalRead(1) == 1)) {
        noData = true;
        return;
    }
    noData = false;
    uint16_t value = analogRead(A6);
    values[currentBuffer][currentWritePos] = (uint16_t)value;
    currentWritePos++;
    if (currentWritePos >= CHUNKSIZE)
    {
        bufferWrittenTo = currentBuffer;
        currentBuffer = 1 - currentBuffer;
        currentWritePos = 0;
        bufferReady = true;
    }
}


int runNumber = 0;

unsigned long nextShow = 0;
unsigned long nextBlink = 0;

void loop() 
{
    if (noData)
    {
         digitalWrite(LED_BUILTIN, 1);
         delay(10);
         digitalWrite(LED_BUILTIN, 0);
         delay(50);
    }
    if (millis()>=nextShow)
    {
        Serial.print("B:");
        Serial.print(currentBuffer);
        Serial.print(" Pos:");
        Serial.print(currentWritePos);
        Serial.print(" SD:");
        Serial.print(SDAvailable);
        Serial.println(" #");
        nextShow = millis()+1000;
        digitalWrite(LED_BUILTIN, 1);
        delay(50);
        digitalWrite(LED_BUILTIN, 0);
    }
    if (bufferReady)
    {
        bufferReady = false;
        if (SDAvailable) 
        {
          digitalWrite(LED_BUILTIN, 1);

          int bufferIndex = bufferWrittenTo;
          char logFile[32];

          sprintf(logFile, "EKG_%04d.BIN", filecnt);
          Serial.print("chunk count: ");
          Serial.print(chunksWritten);
          Serial.print(" Writing new set: ");
          Serial.println(logFile);
          File dataFile = SD.open(logFile, FILE_WRITE);
          if (dataFile)
          {
              dataFile.write((uint8_t*)&values[bufferIndex][0], CHUNKSIZE*sizeof(uint16_t));
              dataFile.close();
          }
          else
          {
            SDAvailable = false;
          }
          chunksWritten++;
          if (chunksWritten>=CHUNKMAXWRITE)
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
          SDAvailable = false;
          for (int i=0; i < 5; ++i)
          {
                digitalWrite(LED_BUILTIN, 1);
                delay(50);
                digitalWrite(LED_BUILTIN, 0);
                delay(100);
          }
          openSDCard();
        }
    }
}
