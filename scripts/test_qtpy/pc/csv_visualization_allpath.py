import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

def calculate_magnitude(x, y, z):
    """3축 데이터의 magnitude를 계산"""
    return np.sqrt(x**2 + y**2 + z**2)

def plot_and_save_imu_data(csv_path, output_path):
    # CSV 파일 읽기
    df = pd.read_csv(csv_path)
    
    # Magnitude 계산
    df['Acc1_Mag'] = calculate_magnitude(df['AccX1'], df['AccY1'], df['AccZ1'])
    df['Gyro1_Mag'] = calculate_magnitude(df['GyroX1'], df['GyroY1'], df['GyroZ1'])
    df['Acc2_Mag'] = calculate_magnitude(df['AccX2'], df['AccY2'], df['AccZ2'])
    df['Gyro2_Mag'] = calculate_magnitude(df['GyroX2'], df['GyroY2'], df['GyroZ2'])
    df['Acc3_Mag'] = calculate_magnitude(df['AccX3'], df['AccY3'], df['AccZ3'])
    df['Gyro3_Mag'] = calculate_magnitude(df['GyroX3'], df['GyroY3'], df['GyroZ3'])
    
    # 원본 데이터 그래프
    fig1 = plt.figure(figsize=(20, 12))
    
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
    
    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.9, hspace=0.4, wspace=0.2)
    
    # 원본 데이터 그래프 저장
    output_filename = os.path.join(output_path, os.path.splitext(os.path.basename(csv_path))[0] + '_original.png')
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Magnitude 그래프 (6줄)
    fig2 = plt.figure(figsize=(20, 12))
    
    # Front IMU Acceleration Magnitude
    ax1 = plt.subplot(611)
    ax1.plot(df['Time'], df['Acc1_Mag'], color='blue', alpha=0.8)
    ax1.set_title('Front IMU Acceleration Magnitude')
    ax1.set_ylabel('m/s²')
    ax1.grid(True)
    
    # Front IMU Gyroscope Magnitude
    ax2 = plt.subplot(612)
    ax2.plot(df['Time'], df['Gyro1_Mag'], color='red', alpha=0.8)
    ax2.set_title('Front IMU Gyroscope Magnitude')
    ax2.set_ylabel('rad/s')
    ax2.grid(True)
    
    # Behind Ear IMU Acceleration Magnitude
    ax3 = plt.subplot(613)
    ax3.plot(df['Time'], df['Acc2_Mag'], color='blue', alpha=0.8)
    ax3.set_title('Behind Ear IMU Acceleration Magnitude')
    ax3.set_ylabel('m/s²')
    ax3.grid(True)
    
    # Behind Ear IMU Gyroscope Magnitude
    ax4 = plt.subplot(614)
    ax4.plot(df['Time'], df['Gyro2_Mag'], color='red', alpha=0.8)
    ax4.set_title('Behind Ear IMU Gyroscope Magnitude')
    ax4.set_ylabel('rad/s')
    ax4.grid(True)
    
    # Temple IMU Acceleration Magnitude
    ax5 = plt.subplot(615)
    ax5.plot(df['Time'], df['Acc3_Mag'], color='blue', alpha=0.8)
    ax5.set_title('Temple IMU Acceleration Magnitude')
    ax5.set_ylabel('m/s²')
    ax5.grid(True)
    
    # Temple IMU Gyroscope Magnitude
    ax6 = plt.subplot(616)
    ax6.plot(df['Time'], df['Gyro3_Mag'], color='red', alpha=0.8)
    ax6.set_title('Temple IMU Gyroscope Magnitude')
    ax6.set_xlabel('Time')
    ax6.set_ylabel('rad/s')
    ax6.grid(True)
    
    plt.subplots_adjust(top=0.95, bottom=0.05, left=0.1, right=0.9, hspace=0.4, wspace=0.2)
    
    # Magnitude 그래프 저장
    output_filename = os.path.join(output_path, os.path.splitext(os.path.basename(csv_path))[0] + '_magnitude.png')
    plt.savefig(output_filename, dpi=300, bbox_inches='tight')
    plt.close()
    
    # Magnitude 데이터를 Excel 파일로 저장
    magnitude_df = df[['Time', 'Acc1_Mag', 'Gyro1_Mag', 
                      'Acc2_Mag', 'Gyro2_Mag',
                      'Acc3_Mag', 'Gyro3_Mag']]
    excel_filename = os.path.join(output_path, os.path.splitext(os.path.basename(csv_path))[0] + '_magnitude.xlsx')
    magnitude_df.to_excel(excel_filename, index=False)

def process_folder(input_folder):
    # 출력 폴더 생성 (input_folder 안에 'plots' 폴더)
    output_folder = os.path.join(input_folder, 'plots')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 모든 CSV 파일 처리
    for filename in os.listdir(input_folder):
        if filename.endswith('.csv'):
            csv_path = os.path.join(input_folder, filename)
            print(f"Processing {filename}...")
            plot_and_save_imu_data(csv_path, output_folder)
            print(f"Saved plots and magnitude data for {filename}")

# 실행
folder_path = "/Users/witlab/Downloads/EatingMoment/Data collection/eating"
process_folder(folder_path)
print("All plots and magnitude data have been generated!")