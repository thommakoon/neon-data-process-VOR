import pandas as pd
import matplotlib.pyplot as plt

# CSV 파일 읽기
df = pd.read_csv("/Users/witlab/Downloads/EatingMoment/Data collection/Turning head/imu_data_20241203_152817.csv")

# 그래프 생성 (가로로 더 길게)
fig = plt.figure(figsize=(20, 12))

# Front IMU 가속도
ax1 = plt.subplot(611)
ax1.plot(df['Time'], df['AccX1'], label='X', alpha=0.8)
ax1.plot(df['Time'], df['AccY1'], label='Y', alpha=0.8)
ax1.plot(df['Time'], df['AccZ1'], label='Z', alpha=0.8)
ax1.set_title('Front IMU Acceleration')
ax1.set_ylabel('m/s²')
ax1.grid(True)
ax1.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# Front IMU 자이로
ax2 = plt.subplot(612)
ax2.plot(df['Time'], df['GyroX1'], label='X', alpha=0.8)
ax2.plot(df['Time'], df['GyroY1'], label='Y', alpha=0.8)
ax2.plot(df['Time'], df['GyroZ1'], label='Z', alpha=0.8)
ax2.set_title('Front IMU Gyroscope')
ax2.set_ylabel('rad/s')
ax2.grid(True)
ax2.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# Behind Ear IMU 가속도
ax3 = plt.subplot(613)
ax3.plot(df['Time'], df['AccX2'], label='X', alpha=0.8)
ax3.plot(df['Time'], df['AccY2'], label='Y', alpha=0.8)
ax3.plot(df['Time'], df['AccZ2'], label='Z', alpha=0.8)
ax3.set_title('Behind Ear IMU Acceleration')
ax3.set_ylabel('m/s²')
ax3.grid(True)
ax3.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# Behind Ear IMU 자이로
ax4 = plt.subplot(614)
ax4.plot(df['Time'], df['GyroX2'], label='X', alpha=0.8)
ax4.plot(df['Time'], df['GyroY2'], label='Y', alpha=0.8)
ax4.plot(df['Time'], df['GyroZ2'], label='Z', alpha=0.8)
ax4.set_title('Behind Ear IMU Gyroscope')
ax4.set_ylabel('rad/s')
ax4.grid(True)
ax4.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# Temple IMU 가속도
ax5 = plt.subplot(615)
ax5.plot(df['Time'], df['AccX3'], label='X', alpha=0.8)
ax5.plot(df['Time'], df['AccY3'], label='Y', alpha=0.8)
ax5.plot(df['Time'], df['AccZ3'], label='Z', alpha=0.8)
ax5.set_title('Temple IMU Acceleration')
ax5.set_ylabel('m/s²')
ax5.grid(True)
ax5.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# Temple IMU 자이로
ax6 = plt.subplot(616)
ax6.plot(df['Time'], df['GyroX3'], label='X', alpha=0.8)
ax6.plot(df['Time'], df['GyroY3'], label='Y', alpha=0.8)
ax6.plot(df['Time'], df['GyroZ3'], label='Z', alpha=0.8)
ax6.set_title('Temple IMU Gyroscope')
ax6.set_xlabel('Time')
ax6.set_ylabel('rad/s')
ax6.grid(True)
ax6.legend(loc='center right', bbox_to_anchor=(1.15, 0.5))

# 그래프 간격 조정
from datetime import datetime
plt.tight_layout(rect=[0, 0, 0.9, 1], h_pad=1.0) 
plt.savefig(f'imu_plot_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png', dpi=300, bbox_inches='tight')