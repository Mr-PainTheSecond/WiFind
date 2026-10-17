idf_component_register(SRCS "../probe.cpp" "../main.cpp"
                       INCLUDE_DIRS ".."
                       PRIV_REQUIRES esp_wifi esp_event nvs_flash)
