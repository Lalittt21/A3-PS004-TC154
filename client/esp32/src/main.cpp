#include <Arduino.h>
#include <WiFi.h>
#include <esp_tls.h>
#include <esp_system.h>
#include <sys/time.h>
#include <time.h>
#include "ca_cert.h"
#if __has_include("config.h")
#include "config.h"
#else
#include "config.example.h"
#endif

static uint8_t packet[2048];
static bool clockReady = false;
static uint32_t lastAttempt = 0;
static unsigned scenario = 0;
static const char *names[] = {"sensor.trustgate.test", "sensor.unsigned.trustgate.test", "tampered.trustgate.test", "missing.trustgate.test"};
static uint16_t u16(const uint8_t *p) { return (uint16_t(p[0]) << 8) | p[1]; }

// Bounded DNS decompression. Reject cycles, oversized names and invalid labels.
static bool readName(size_t &pos, size_t size, String &name) {
  size_t at = pos; bool jumped = false; unsigned steps = 0;
  name = "";
  while (at < size && ++steps <= 128) {
    uint8_t len = packet[at++];
    if (!len) { if (!jumped) pos = at; return true; }
    if ((len & 0xc0) == 0xc0) {
      if (at >= size) return false;
      size_t target = ((len & 0x3f) << 8) | packet[at++];
      if (target >= size) return false;
      if (!jumped) pos = at;
      jumped = true; at = target; continue;
    }
    if ((len & 0xc0) || at + len > size || name.length() + len + 1 > 253) return false;
    if (name.length()) name += '.';
    while (len--) { char c = packet[at++]; if (!isalnum((unsigned char)c) && c != '-' && c != '_') return false; name += c; }
  }
  return false;
}

static void evaluate(size_t size, uint16_t id, const char *query) {
  if (size < 12 || u16(packet) != id || !(packet[2] & 0x80) ||
      (packet[2] & 0x7a) || u16(packet + 4) != 1) {
    Serial.println("BLOCK malformed header"); return;
  }
  size_t pos = 12; String question;
  if (!readName(pos, size, question) || !question.equalsIgnoreCase(query) || pos + 4 > size ||
      u16(packet + pos) != 1 || u16(packet + pos + 2) != 1) {
    Serial.println("BLOCK mismatched question"); return;
  }
  pos += 4;
  unsigned rcode = packet[3] & 15;
  if (rcode) { Serial.printf("BLOCK DNS rcode=%u (SERVFAIL alone does not identify cause)\n", rcode); return; }
  if (!(packet[3] & 0x20)) { Serial.println("BLOCK no authenticated-data flag"); return; }
  uint16_t count = u16(packet + 6); bool found = false; uint8_t ip[4] = {};
  for (unsigned i = 0; i < count; i++) {
    String owner;
    if (!readName(pos, size, owner) || pos + 10 > size) { Serial.println("BLOCK malformed answer"); return; }
    uint16_t type = u16(packet + pos), cls = u16(packet + pos + 2), length = u16(packet + pos + 8);
    pos += 10;
    if (pos + length > size) { Serial.println("BLOCK truncated answer"); return; }
    if (type == 1 && cls == 1 && owner.equalsIgnoreCase(query)) {
      if (length != 4) { Serial.println("BLOCK invalid A record"); return; }
      memcpy(ip, packet + pos, 4); found = true;
    }
    pos += length;
  }
  if (found) Serial.printf("ACCEPT %u.%u.%u.%u\n", ip[0], ip[1], ip[2], ip[3]);
  else Serial.println("BLOCK no direct A record (CNAME unsupported)");
}

static bool transfer(esp_tls_t *tls, uint8_t *data, size_t size, bool writing) {
  uint32_t start = millis(); size_t done = 0;
  while (done < size && millis() - start < 5000) {
    int n = writing ? esp_tls_conn_write(tls, data + done, size - done) : esp_tls_conn_read(tls, data + done, size - done);
    if (n > 0) done += n;
    else if (n == ESP_TLS_ERR_SSL_WANT_READ || n == ESP_TLS_ERR_SSL_WANT_WRITE) delay(10);
    else return false;
  }
  return done == size;
}

static void queryDNS(const char *name) {
  uint32_t start = millis();
  esp_tls_cfg_t cfg = {};
  cfg.cacert_buf = (const unsigned char *)TG_CA;
  cfg.cacert_bytes = strlen(TG_CA) + 1;
  cfg.common_name = TG_GATEWAY_NAME;
  cfg.skip_common_name = false;
  cfg.timeout_ms = 3000;
  esp_tls_t *tls = esp_tls_init();
  if (!tls) { Serial.println("BLOCK no TLS memory"); return; }
  if (esp_tls_conn_new_sync(TG_GATEWAY_IP, strlen(TG_GATEWAY_IP), TG_GATEWAY_PORT, &cfg, tls) != 1) {
    Serial.println("BLOCK TLS connection or certificate failure; no fallback");
    esp_tls_conn_destroy(tls); return;
  }
  uint16_t id = esp_random() & 0xffff;
  memset(packet, 0, 12); packet[0] = id >> 8; packet[1] = id; packet[2] = 1;
  packet[3] = 0x20; packet[5] = 1; // RD + AD request; CD is never set.
  size_t used = 12; const char *label = name;
  while (*label) {
    const char *dot = strchr(label, '.'); size_t len = dot ? size_t(dot - label) : strlen(label);
    if (!len || len > 63 || used + len + 6 > sizeof(packet)) { esp_tls_conn_destroy(tls); return; }
    packet[used++] = len; memcpy(packet + used, label, len); used += len;
    if (!dot) break; label = dot + 1;
  }
  packet[used++] = 0; packet[used++] = 0; packet[used++] = 1; packet[used++] = 0; packet[used++] = 1;
  uint8_t prefix[2] = {uint8_t(used >> 8), uint8_t(used)};
  bool ok = transfer(tls, prefix, 2, true) && transfer(tls, packet, used, true) && transfer(tls, prefix, 2, false);
  size_t size = u16(prefix);
  if (ok && size >= 12 && size <= sizeof(packet) && transfer(tls, packet, size, false)) evaluate(size, id, name);
  else Serial.println("BLOCK incomplete or oversized DNS frame");
  esp_tls_conn_destroy(tls);
  Serial.printf("METRIC elapsed_ms=%lu free_heap=%u minimum_heap=%u\n", (unsigned long)(millis()-start), ESP.getFreeHeap(), ESP.getMinFreeHeap());
}

void setup() {
  Serial.begin(115200); Serial.setTimeout(1000);
  Serial.println("TrustGate lab. Provision time via USB: TIME <current Unix seconds>");
  Serial.println("No queries until time is provisioned. No plaintext DNS fallback.");
  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true);
  if (String(TG_WIFI_SSID) != "CHANGE_ME") WiFi.begin(TG_WIFI_SSID, TG_WIFI_PASSWORD);
  else Serial.println("Configure include/config.h with Wi-Fi credentials and gateway LAN IP first.");
}
void loop() {
  static bool wasConnected = false;
  bool connected = WiFi.status() == WL_CONNECTED;
  if (connected && !wasConnected) Serial.printf("WIFI connected IP=%s\n", WiFi.localIP().toString().c_str());
  if (!connected && wasConnected) Serial.println("WIFI disconnected; queries paused");
  wasConnected = connected;
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n'); line.trim();
    if (line.startsWith("TIME ")) {
      const char *input = line.c_str() + 5; char *end;
      long long epoch = strtoll(input, &end, 10);
      if (*input && !*end && epoch >= 1767225600LL && epoch < 4102444800LL) {
        timeval tv = {(time_t)epoch, 0}; clockReady = settimeofday(&tv, nullptr) == 0;
        Serial.println(clockReady ? "Time provisioned; certificate dates will be checked." : "Time setup failed.");
      } else Serial.println("Invalid TIME value");
    }
  }
  if (clockReady && WiFi.status() == WL_CONNECTED && millis() - lastAttempt >= 10000) {
    lastAttempt = millis(); const char *name = names[scenario++ % 4];
    Serial.printf("QUERY %s\n", name); queryDNS(name);
  }
  delay(20);
}
