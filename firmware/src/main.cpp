#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"
#ifndef DHT_TYPE
#define DHT_TYPE DHT22
#endif
DHT dht(DHT_PIN, DHT_TYPE);
WiFiClientSecure tls;
PubSubClient mqtt(tls);
unsigned long lastPublish=0, retryAt=0;
uint32_t backoff=1000;
String baseTopic(){ return String("home/")+HOME_ID+"/devices/"+DEVICE_ID; }
void connectWifi(){
  if(WiFi.status()==WL_CONNECTED)return;
  Serial.println("Connecting to configured Wi-Fi");
  WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  unsigned long start=millis();
  while(WiFi.status()!=WL_CONNECTED && millis()-start<15000) delay(250);
}
void connectMqtt(){
  if(mqtt.connected() || millis()<retryAt)return;
  connectWifi(); if(WiFi.status()!=WL_CONNECTED){ retryAt=millis()+backoff; backoff=min(backoff*2,60000UL); return; }
  String statusTopic=baseTopic()+"/status";
  String will="{\"device_id\":\""+String(DEVICE_ID)+"\",\"status\":\"offline\"}";
  if(mqtt.connect(DEVICE_ID,nullptr,nullptr,statusTopic.c_str(),1,true,will.c_str())){
    mqtt.publish(statusTopic.c_str(),"{\"status\":\"online\"}",true);
    backoff=1000; Serial.println("MQTT connected");
  } else { retryAt=millis()+backoff; backoff=min(backoff*2,60000UL); Serial.printf("MQTT connect failed: %d\n",mqtt.state()); }
}
void setup(){
  Serial.begin(115200); dht.begin();
  tls.setCACert(AWS_ROOT_CA); tls.setCertificate(DEVICE_CERT); tls.setPrivateKey(DEVICE_PRIVATE_KEY);
  mqtt.setServer(MQTT_HOST,MQTT_PORT); mqtt.setBufferSize(512); connectWifi();
}
void loop(){
  connectMqtt(); mqtt.loop();
  if(mqtt.connected() && millis()-lastPublish>=TELEMETRY_INTERVAL_MS){
    lastPublish=millis(); float temp=dht.readTemperature(), hum=dht.readHumidity(); int air=analogRead(MQ135_PIN);
    if(isnan(temp)||isnan(hum)||temp < -40||temp>85||hum<0||hum>100){ Serial.println("Invalid DHT reading; skipped"); return; }
    char payload[256]; snprintf(payload,sizeof(payload),"{\"device_id\":\"%s\",\"timestamp\":\"%lu\",\"temperature\":%.1f,\"humidity\":%.1f,\"air_quality\":%d,\"status\":\"online\"}",DEVICE_ID,(unsigned long)time(nullptr),temp,hum,air);
    String topic=baseTopic()+"/telemetry";
    if(mqtt.publish(topic.c_str(),payload,false)) Serial.println("Telemetry published"); else Serial.println("Telemetry publish failed");
  }
  delay(20);
}
