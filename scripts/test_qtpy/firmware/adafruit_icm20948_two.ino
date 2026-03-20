#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

Adafruit_ICM20948 icm1;  // 첫 번째 센서 (0x69)
Adafruit_ICM20948 icm2;  // 두 번째 센서 (0x68)

void setup(void) {
  Serial.begin(921600);
  while (!Serial)
    delay(10);

  Serial.println("Dual ICM20948 test!");

  // 첫 번째 센서 초기화 (0x69)
  if (!icm1.begin_I2C(0x69, &Wire1)) {
    Serial.println("Failed to find first ICM20948 chip");
    while (1) { delay(10); }
  }
  Serial.println("First ICM20948 Found!");

  // 두 번째 센서 초기화 (0x68)
  if (!icm2.begin_I2C(0x68, &Wire1)) {
    Serial.println("Failed to find second ICM20948 chip");
    while (1) { delay(10); }
  }
  Serial.println("Second ICM20948 Found!");

  // CSV 헤더 출력
  Serial.println("Time,Temp1,AccX1,AccY1,AccZ1,GyroX1,GyroY1,GyroZ1,MagX1,MagY1,MagZ1,Temp2,AccX2,AccY2,AccZ2,GyroX2,GyroY2,GyroZ2,MagX2,MagY2,MagZ2");
}

void loop() {
  // 첫 번째 센서 데이터 읽기
  sensors_event_t accel1, gyro1, mag1, temp1;
  icm1.getEvent(&accel1, &gyro1, &temp1, &mag1);

  // 두 번째 센서 데이터 읽기
  sensors_event_t accel2, gyro2, mag2, temp2;
  icm2.getEvent(&accel2, &gyro2, &temp2, &mag2);

  // 시간 기록 (밀리초)
  Serial.print(millis());
  Serial.print(",");

  // 첫 번째 센서 데이터 출력
  Serial.print(temp1.temperature); Serial.print(",");
  Serial.print(accel1.acceleration.x); Serial.print(",");
  Serial.print(accel1.acceleration.y); Serial.print(",");
  Serial.print(accel1.acceleration.z); Serial.print(",");
  Serial.print(gyro1.gyro.x); Serial.print(",");
  Serial.print(gyro1.gyro.y); Serial.print(",");
  Serial.print(gyro1.gyro.z); Serial.print(",");
  Serial.print(mag1.magnetic.x); Serial.print(",");
  Serial.print(mag1.magnetic.y); Serial.print(",");
  Serial.print(mag1.magnetic.z); Serial.print(",");

  // 두 번째 센서 데이터 출력
  Serial.print(temp2.temperature); Serial.print(",");
  Serial.print(accel2.acceleration.x); Serial.print(",");
  Serial.print(accel2.acceleration.y); Serial.print(",");
  Serial.print(accel2.acceleration.z); Serial.print(",");
  Serial.print(gyro2.gyro.x); Serial.print(",");
  Serial.print(gyro2.gyro.y); Serial.print(",");
  Serial.print(gyro2.gyro.z); Serial.print(",");
  Serial.print(mag2.magnetic.x); Serial.print(",");
  Serial.print(mag2.magnetic.y); Serial.print(",");
  Serial.print(mag2.magnetic.z);
  
  Serial.println();  // 줄 바꿈

  delay(1);  // 100Hz 샘플링 속도
}