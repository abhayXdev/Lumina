import re

with open("main.c", "r") as f:
    content = f.read()

# Replace include
content = content.replace("#include \"driver/i2s.h\"", "#include \"driver/i2s_std.h\"")

# Replace global vars
i2s_globals = "i2s_chan_handle_t rx_handle = NULL;\n"

content = re.sub(r"esp_websocket_client_handle_t ws_client;", i2s_globals + "esp_websocket_client_handle_t ws_client;", content)

# Replace i2s_init
new_i2s_init = """static void i2s_init() {
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
}"""

content = re.sub(r"static void i2s_init\(\) \{.*?\n\}", new_i2s_init, content, flags=re.DOTALL)

# Replace i2s_read
content = content.replace("i2s_read(I2S_PORT, audio_buffer, AUDIO_CHUNK_SIZE, &bytes_read, portMAX_DELAY);", "i2s_channel_read(rx_handle, audio_buffer, AUDIO_CHUNK_SIZE, &bytes_read, portMAX_DELAY);")

with open("main.c", "w") as f:
    f.write(content)
