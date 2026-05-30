#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/i2s_std.h"
#include "driver/gpio.h"
#include "esp_websocket_client.h"
#include "cJSON.h"

// Configuration
#define WIFI_SSID      "YOUR_WIFI_SSID"
#define WIFI_PASS      "YOUR_WIFI_PASSWORD"
#define WEBSOCKET_URL  "wss://typically-capacity-build-peace.trycloudflare.com/ws/esp32_001?api_key=your_api_key_here"

#define I2S_WS 25
#define I2S_SD 32
#define I2S_SCK 33
#define I2S_PORT I2S_NUM_0

#define LED_PIN 2 // Built-in LED

#define AUDIO_CHUNK_SIZE 1024

static const char *TAG = "JARVIS_CLIENT";

static EventGroupHandle_t wifi_event_group;
const int WIFI_CONNECTED_BIT = BIT0;

i2s_chan_handle_t rx_handle = NULL;
esp_websocket_client_handle_t ws_client;
bool ws_connected = false;

// Wi-Fi Event Handler
static void wifi_event_handler(void* arg, esp_event_base_t event_base, int32_t event_id, void* event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        esp_wifi_connect();
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
        ESP_LOGI(TAG, "Retry connecting to the AP");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "Got IP:" IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

// WebSocket Event Handler
static void websocket_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            ESP_LOGI(TAG, "WEBSOCKET_EVENT_CONNECTED");
            ws_connected = true;
            break;
        case WEBSOCKET_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "WEBSOCKET_EVENT_DISCONNECTED");
            ws_connected = false;
            break;
        case WEBSOCKET_EVENT_DATA:
            if (data->op_code == 0x01) { // Text frame
                ESP_LOGI(TAG, "Received message: %.*s", data->data_len, (char *)data->data_ptr);
                cJSON *json = cJSON_Parse((char *)data->data_ptr);
                if (json) {
                    cJSON *type = cJSON_GetObjectItem(json, "type");
                    if (type && strcmp(type->valuestring, "command") == 0) {
                        cJSON *cmd = cJSON_GetObjectItem(json, "command");
                        if (cmd) {
                            if (strcmp(cmd->valuestring, "led_on") == 0) {
                                gpio_set_level(LED_PIN, 1);
                                ESP_LOGI(TAG, "LED turned ON");
                            } else if (strcmp(cmd->valuestring, "led_off") == 0) {
                                gpio_set_level(LED_PIN, 0);
                                ESP_LOGI(TAG, "LED turned OFF");
                            }
                        }
                    }
                    cJSON_Delete(json);
                }
            }
            break;
        case WEBSOCKET_EVENT_ERROR:
            ESP_LOGI(TAG, "WEBSOCKET_EVENT_ERROR");
            break;
    }
}

// I2S Initialization
static void i2s_init() {
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, NULL, &rx_handle));

    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(16000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = I2S_SCK,
            .ws   = I2S_WS,
            .dout = I2S_GPIO_UNUSED,
            .din  = I2S_SD,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv   = false,
            },
        },
    };
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_handle, &std_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(rx_handle));
}

// Audio Capture and Streaming Task
void audio_stream_task(void *pvParameters) {
    char *audio_buffer = (char *)malloc(AUDIO_CHUNK_SIZE);
    size_t bytes_read;

    while (1) {
        if (ws_connected) {
            i2s_channel_read(rx_handle, audio_buffer, AUDIO_CHUNK_SIZE, &bytes_read, portMAX_DELAY);
            if (bytes_read > 0) {
                esp_websocket_client_send_bin(ws_client, audio_buffer, bytes_read, portMAX_DELAY);
            }
        } else {
            vTaskDelay(100 / portTICK_PERIOD_MS);
        }
    }
}

// Heartbeat Task
void heartbeat_task(void *pvParameters) {
    const char *heartbeat_msg = "{\"type\": \"heartbeat\", \"device_id\": \"esp32_001\"}";
    while (1) {
        if (ws_connected) {
            esp_websocket_client_send_text(ws_client, heartbeat_msg, strlen(heartbeat_msg), portMAX_DELAY);
        }
        vTaskDelay(30000 / portTICK_PERIOD_MS); // 30 seconds
    }
}

void app_main(void) {
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize GPIO for LED
    gpio_reset_pin(LED_PIN);
    gpio_set_direction(LED_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(LED_PIN, 0);

    // Initialize WiFi
    wifi_event_group = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASS,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());

    // Wait for WiFi
    xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);

    // Initialize I2S
    i2s_init();

    // Initialize WebSocket
    esp_websocket_client_config_t websocket_cfg = {};
    websocket_cfg.uri = WEBSOCKET_URL;

    ws_client = esp_websocket_client_init(&websocket_cfg);
    esp_websocket_register_events(ws_client, WEBSOCKET_EVENT_ANY, websocket_event_handler, (void *)ws_client);
    esp_websocket_client_start(ws_client);

    // Start Tasks
    xTaskCreatePinnedToCore(audio_stream_task, "audio_stream_task", 4096, NULL, 5, NULL, 1);
    xTaskCreatePinnedToCore(heartbeat_task, "heartbeat_task", 2048, NULL, 4, NULL, 1);
}
