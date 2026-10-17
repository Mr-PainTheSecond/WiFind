#include <esp_event.h>
#include <esp_wifi.h>
#include <esp_wifi_types.h>
#include <nvs_flash.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <probe.h>
#include <cstdint>
#include <cstring>

struct Sighting {
    uint8_t  mac[6];
    int8_t   rssi;
    uint8_t  channel;
    uint32_t timestamp_us;
};

static QueueHandle_t sightingQueue;

// Minimal 802.11 management header layout
struct __attribute__((packed)) MgmtHeader {
    uint8_t  frameControl[2];
    uint16_t duration;
    uint8_t  addr1[6];   // receiver
    uint8_t  addr2[6];   // transmitter (the phone)
    uint8_t  addr3[6];
    uint16_t seqCtrl;
};

static void IRAM_ATTR snifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
    if (type != WIFI_PKT_MGMT) return;

    const auto* pkt = static_cast<const wifi_promiscuous_pkt_t*>(buf);
    const auto* hdr = reinterpret_cast<const MgmtHeader*>(pkt->payload);

    // type = management (0), subtype = probe request (4)  ->  0x40
    if ((hdr->frameControl[0] & 0xFC) != 0x40) return;

    Sighting s{};
    std::memcpy(s.mac, hdr->addr2, 6);
    s.rssi         = pkt->rx_ctrl.rssi;
    s.channel      = pkt->rx_ctrl.channel;
    s.timestamp_us = pkt->rx_ctrl.timestamp;

    xQueueSendFromISR(sightingQueue, &s, nullptr);  // non-blocking handoff
}

// Channel the sniffer listens on. Phones send probe requests on every channel
// while scanning, so a single fixed channel still catches them.
static constexpr uint8_t kSnifferChannel = 1;

// The Wi-Fi driver stores calibration data in NVS (flash), so NVS must be ready
// before esp_wifi_init(). If the NVS partition is full or was written by a newer
// IDF version, erase it and try again.
static void initNvs() {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

// Bring the Wi-Fi radio up without joining or hosting a network.
// WIFI_MODE_NULL powers the radio for promiscuous capture only.
static void initWifi() {
    initNvs();

    // The Wi-Fi driver posts its events (started, stopped, ...) to the default loop.
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    wifi_init_config_t config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&config));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));  // nothing to persist
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_NULL));
    ESP_ERROR_CHECK(esp_wifi_start());
}

void startSniffer() {
    sightingQueue = xQueueCreate(64, sizeof(Sighting));

    initWifi();

    wifi_promiscuous_filter_t filter{};
    filter.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT;

    ESP_ERROR_CHECK(esp_wifi_set_promiscuous_filter(&filter));
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous_rx_cb(&snifferCallback));
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));

    // The channel can only be set once promiscuous mode is on (no AP to follow).
    ESP_ERROR_CHECK(esp_wifi_set_channel(kSnifferChannel, WIFI_SECOND_CHAN_NONE));
}