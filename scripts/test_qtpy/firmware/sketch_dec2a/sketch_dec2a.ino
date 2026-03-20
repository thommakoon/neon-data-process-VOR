#include <Wire.h>
#include <SparkFun_I2C_Mux_Arduino_Library.h>
#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>

QWIICMUX myMux;
Adafruit_ICM20948 icm1;  // Port 0의 센서 (0x69)
Adafruit_ICM20948 icm2;  // Port 1의 센서 (0x69)

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  Serial.println("Starting IMU Test");
  
  Wire1.begin();  // Wire 대신 Wire1 사용
  
  if (myMux.begin(0x70, Wire1) == false) {
    Serial.println("Mux not detected. Freezing...");
    while (1);
  }
  Serial.println("Mux detected");

  // 각 포트의 I2C 장치 스캔
  for (uint8_t port = 0; port < 8; port++) {
    myMux.setPort(port);
    Serial.print("\nScanning Port ");
    Serial.println(port);
    
    for (uint8_t addr = 0; addr < 127; addr++) {
      Wire1.beginTransmission(addr);
      if (Wire1.endTransmission() == 0) {
        Serial.print("Found I2C device at address 0x");
        if (addr < 16) Serial.print("0");
        Serial.println(addr, HEX);
      }
    }
  }

  // Port 0의 센서 초기화
  Serial.println("\nInitializing Port 0 IMU");
  myMux.setPort(0);
  if (!icm1.begin_I2C(0x69, &Wire1)) {
    Serial.println("Failed to find ICM20948 chip on port 0");
    while (1) delay(10);
  }
  Serial.println("Port 0 IMU initialized");
  configureICM(icm1);

  // Port 1의 센서 초기화
  Serial.println("\nInitializing Port 1 IMU");
  myMux.setPort(1);
  if (!icm2.begin_I2C(0x69, &Wire1)) {
    Serial.println("Failed to find ICM20948 chip on port 1");
    while (1) delay(10);
  }
  Serial.println("Port 1 IMU initialized");
  configureICM(icm2);

  Serial.println("\nAll devices initialized!");
  Serial.println("Time,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,MagX1,MagY1,MagZ1,AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2,MagX2,MagY2,MagZ2");
}

void configureICM(Adafruit_ICM20948 &icm) {
  icm.setAccelRange(ICM20948_ACCEL_RANGE_16_G);
  icm.setGyroRange(ICM20948_GYRO_RANGE_2000_DPS);
  icm.setAccelRateDivisor(0);
  icm.setGyroRateDivisor(0);
}
void loop() {
  static unsigned long lastTime = 0;
  unsigned long currentTime = micros();
  
  // 100Hz 샘플링 (10ms 간격)
  if (currentTime - lastTime >= 12500) {
    lastTime = currentTime;
    
    sensors_event_t accel1, gyro1, temp1, mag1;
    sensors_event_t accel2, gyro2, temp2, mag2;

    // Port 0의 센서 읽기
    myMux.setPort(0);
    icm1.getEvent(&accel1, &gyro1, &temp1, &mag1);
    
    // Port 1의 센서 읽기
    myMux.setPort(1);
    icm2.getEvent(&accel2, &gyro2, &temp2, &mag2);
    
    // CSV 출력 (PC logger가 LF/RF 포맷으로 분리 저장)
    Serial.printf("%lu,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f\n",
      currentTime,
      accel1.acceleration.x, accel1.acceleration.y, accel1.acceleration.z,
      gyro1.gyro.x, gyro1.gyro.y, gyro1.gyro.z,
      mag1.magnetic.x, mag1.magnetic.y, mag1.magnetic.z,
      accel2.acceleration.x, accel2.acceleration.y, accel2.acceleration.z,
      gyro2.gyro.x, gyro2.gyro.y, gyro2.gyro.z,
      mag2.magnetic.x, mag2.magnetic.y, mag2.magnetic.z);
  }
}