#include <esp_wifi.h>
#include <esp_wifi_types.h>
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

void startSniffer() {
    sightingQueue = xQueueCreate(64, sizeof(Sighting));

    wifi_promiscuous_filter_t filter{};
    filter.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT;

    esp_wifi_set_promiscuous_filter(&filter);
    esp_wifi_set_promiscuous_rx_cb(&snifferCallback);
    esp_wifi_set_promiscuous(true);
}