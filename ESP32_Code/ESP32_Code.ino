#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include "FS.h"
#include "SD.h"
#include "SPI.h"

#include "AudioFileSourceHTTPStream.h"
#include "AudioFileSourceBuffer.h"
#include "AudioFileSourceSD.h"
#include "AudioGeneratorMP3.h"
#include "AudioGeneratorAAC.h"
#include "AudioOutputI2S.h"

// WiFi Credentials
const char* ssid = "CyberPhonix_2.4G";
const char* password = "Hello_mighty_raju_@1234";

// Pins for SD Card (Adjust if your pins are different)
#define SD_CS 5
#define SPI_SCK 18
#define SPI_MISO 19
#define SPI_MOSI 23

// Audio Objects
AudioGenerator *audioGen = NULL;
AudioFileSourceHTTPStream *file = NULL;
AudioFileSourceBuffer *buff = NULL;
AudioFileSourceSD *fileSD = NULL;
AudioOutputI2S *out = NULL;

WebServer server(80);

void stopAudio()
{
    if (audioGen) {
        audioGen->stop();
        delete audioGen;
        audioGen = NULL;
    }
    if (buff) {
        buff->close();
        delete buff;
        buff = NULL;
    }
    if (file) {
        file->close();
        delete file;
        file = NULL;
    }
    if (fileSD) {
        fileSD->close();
        delete fileSD;
        fileSD = NULL;
    }
}

void handlePlay()
{
    if (!server.hasArg("url")) {
        server.send(400, "text/plain", "No URL");
        return;
    }

    String url = server.arg("url");
    Serial.println("Streaming URL: " + url);

    stopAudio();

    file = new AudioFileSourceHTTPStream(url.c_str());
    buff = new AudioFileSourceBuffer(file, 2048 * 8); // 16KB buffer

    // Auto-detect format based on URL extension
    if (url.indexOf(".mp4") != -1 || url.indexOf(".m4a") != -1 || url.indexOf(".aac") != -1) {
        Serial.println("Starting AAC Decoder");
        audioGen = new AudioGeneratorAAC();
    } else {
        Serial.println("Starting MP3 Decoder");
        audioGen = new AudioGeneratorMP3();
    }

    if (!audioGen->begin(buff, out)) {
        Serial.println("Audio start failed");
        server.send(500, "text/plain", "Decoder failed");
        return;
    }

    server.send(200, "text/plain", "Playing Stream");
}

void handlePlayTTS()
{
    if (!server.hasArg("url")) {
        server.send(400, "text/plain", "No URL");
        return;
    }

    String url = server.arg("url");
    Serial.println("Downloading TTS: " + url);

    stopAudio();

    // Download to SD to fix short audio truncation
    HTTPClient http;
    http.begin(url);
    int httpCode = http.GET();
    
    if (httpCode == HTTP_CODE_OK) {
        File ttsFile = SD.open("/tts.mp3", FILE_WRITE);
        if (ttsFile) {
            http.writeToStream(&ttsFile);
            ttsFile.close();
            Serial.println("TTS Saved to SD");
            
            fileSD = new AudioFileSourceSD("/tts.mp3");
            audioGen = new AudioGeneratorMP3();
            if (audioGen->begin(fileSD, out)) {
                server.send(200, "text/plain", "Playing TTS from SD");
                return;
            }
        }
    }
    
    http.end();
    server.send(500, "text/plain", "TTS Download Failed");
}

void handleStop()
{
    stopAudio();
    server.send(200, "text/plain", "Stopped");
}

void setup()
{
    Serial.begin(115200);

    // Init SD Card
    SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI, SD_CS);
    if (!SD.begin(SD_CS)) {
        Serial.println("SD Card Mount Failed!");
    } else {
        Serial.println("SD Card Mounted.");
    }

    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi Connected: " + WiFi.localIP().toString());

    // I2S Output Configuration
    out = new AudioOutputI2S();
    out->SetPinout(26, 25, 22); // BCLK, LRC, DIN
    out->SetGain(1.0);

    server.on("/", []() { server.send(200, "text/plain", "ESP32 Jarvis Ready"); });
    server.on("/play", handlePlay);
    server.on("/playTTS", handlePlayTTS);
    server.on("/stop", handleStop);

    server.begin();
    Serial.println("Web Server Started");
}

void loop()
{
    server.handleClient();

    if (audioGen && audioGen->isRunning()) {
        if (!audioGen->loop()) {
            Serial.println("Playback Finished");
            stopAudio();
        }
    }
}
