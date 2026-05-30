idf_component_register(SRCS "main.c"
                    INCLUDE_DIRS "."
                    REQUIRES esp_wifi nvs_flash esp_event esp_netif esp_websocket_client cjson driver esp_driver_i2s esp_driver_gpio)
