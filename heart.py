import sys
import time
import board
import busio
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from adafruit_max30102 import MAX30102
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMessageBox, QPushButton, QComboBox, QInputDialog
from PyQt5.QtCore import QTimer

class HeartRateMonitor(QMainWindow):
    def __init__(self):
        super().__init__()

        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.sensor = MAX30102(self.i2c)
        
        # Thiết lập giao diện người dùng
        self.setWindowTitle('Heart Rate Monitor')
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()

        self.label_heart_rate = QLabel('Nhịp Tim: 0 bpm', self)
        self.label_oxygen = QLabel('Nồng độ Oxy: 0 %', self)
        self.label_analysis = QLabel('', self)
        
        self.layout.addWidget(self.label_heart_rate)
        self.layout.addWidget(self.label_oxygen)
        self.layout.addWidget(self.label_analysis)
        
        # Tạo khu vực cho biểu đồ
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # Thêm lựa chọn người dùng
        self.combo_box_users = QComboBox(self)
        self.combo_box_users.addItems(['Người dùng 1', 'Người dùng 2', 'Người dùng 3'])
        self.combo_box_users.currentIndexChanged.connect(self.change_user)
        self.layout.addWidget(self.combo_box_users)

        # Thêm nút để thay đổi ngưỡng
        self.button_set_threshold = QPushButton('Đặt Ngưỡng', self)
        self.button_set_threshold.clicked.connect(self.set_thresholds)
        self.layout.addWidget(self.button_set_threshold)
        
        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

        # Khởi tạo file CSV cho người dùng
        self.current_user = self.combo_box_users.currentText()
        self.csv_file = open(f'{self.current_user}_health_data.csv', mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['Timestamp', 'Heart Rate (bpm)', 'Oxygen (%)'])
        
        # Giá trị ngưỡng mặc định
        self.heart_rate_threshold_low = 60
        self.heart_rate_threshold_high = 100
        self.oxygen_threshold = 95

        # Khởi tạo dữ liệu cho biểu đồ
        self.heart_rate_data = []
        self.oxygen_data = []
        self.timestamps = []

        # Thiết lập bộ đếm thời gian để cập nhật dữ liệu
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(5000)  # Cập nhật mỗi 5 giây
    
    def update_data(self):
        """Đọc nhịp tim và nồng độ oxy từ cảm biến và cập nhật giao diện"""
        try:
            heart_rate = self.sensor.get_heart_rate()
            oxygen_saturation = self.sensor.get_oxygen_saturation()

            # Lưu dữ liệu vào CSV
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.csv_writer.writerow([timestamp, heart_rate, oxygen_saturation])
            self.csv_file.flush()
            
            # Cập nhật dữ liệu biểu đồ
            self.timestamps.append(timestamp)
            self.heart_rate_data.append(heart_rate)
            self.oxygen_data.append(oxygen_saturation)

            # Vẽ biểu đồ
            self.figure.clear()
            ax1 = self.figure.add_subplot(211)
            ax1.plot(self.timestamps, self.heart_rate_data, label='Nhịp Tim (bpm)')
            ax1.set_ylabel('Nhịp Tim (bpm)')
            ax1.legend()
            
            ax2 = self.figure.add_subplot(212)
            ax2.plot(self.timestamps, self.oxygen_data, label='Nồng độ Oxy (%)', color='orange')
            ax2.set_xlabel('Thời gian')
            ax2.set_ylabel('Nồng độ Oxy (%)')
            ax2.legend()
            
            self.canvas.draw()
            
            # Cập nhật giao diện với dữ liệu mới
            self.label_heart_rate.setText(f'Nhịp Tim: {heart_rate} bpm')
            self.label_oxygen.setText(f'Nồng độ Oxy: {oxygen_saturation} %')
            
            # Phân tích và cập nhật tình trạng sức khỏe
            analysis = self.analyze_condition(heart_rate, oxygen_saturation)
            self.label_analysis.setText(analysis)
        
        except Exception as e:
            print(f"Error reading sensor data: {e}")
    
    def analyze_condition(self, heart_rate, oxygen_saturation):
        """Phân tích tình trạng sức khỏe dựa trên nhịp tim và nồng độ oxy"""
        analysis = ''
        
        # Phân tích nhịp tim
        if heart_rate < self.heart_rate_threshold_low:
            analysis += 'Nhịp tim thấp. Bạn có thể bị hạ huyết áp.\n'
            self.show_warning('Nhịp tim thấp!', 'Nhịp tim của bạn thấp, bạn có thể bị hạ huyết áp.')
        elif self.heart_rate_threshold_low <= heart_rate <= self.heart_rate_threshold_high:
            analysis += 'Nhịp tim bình thường.\n'
        else:
            analysis += 'Nhịp tim cao. Bạn có thể bị căng thẳng hoặc gặp vấn đề về tim.\n'
            self.show_warning('Nhịp tim cao!', 'Nhịp tim của bạn cao, bạn có thể bị căng thẳng hoặc gặp vấn đề về tim.')
        
        # Phân tích nồng độ oxy
        if oxygen_saturation < self.oxygen_threshold:
            analysis += 'Nồng độ oxy thấp. Bạn có thể gặp vấn đề về hô hấp.\n'
            self.show_warning('Nồng độ oxy thấp!', 'Nồng độ oxy của bạn thấp, bạn có thể gặp vấn đề về hô hấp.')
        else:
            analysis += 'Nồng độ oxy bình thường.\n'
        
        return analysis
    
    def show_warning(self, title, message):
        """Hiển thị cửa sổ cảnh báo"""
        QMessageBox.warning(self, title, message)

    def set_thresholds(self):
        """Cho phép người dùng thay đổi ngưỡng cảnh báo"""
        heart_rate_low, ok = QInputDialog.getInt(self, 'Thiết lập ngưỡng', 'Nhịp tim thấp ngưỡng:', self.heart_rate_threshold_low, 0, 200)
        if ok:
            self.heart_rate_threshold_low = heart_rate_low

        heart_rate_high, ok = QInputDialog.getInt(self, 'Thiết lập ngưỡng', 'Nhịp tim cao ngưỡng:', self.heart_rate_threshold_high, 0, 200)
        if ok:
            self.heart_rate_threshold_high = heart_rate_high

        oxygen_threshold, ok = QInputDialog.getInt(self, 'Thiết lập ngưỡng', 'Nồng độ oxy ngưỡng:', self.oxygen_threshold, 0, 100)
        if ok:
            self.oxygen_threshold = oxygen_threshold

    def change_user(self):
        """Thay đổi người dùng và khởi tạo file CSV mới"""
        self.csv_file.close()
        self.current_user = self.combo_box_users.currentText()
        self.csv_file = open(f'{self.current_user}_health_data.csv', mode='w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['Timestamp', 'Heart Rate (bpm)', 'Oxygen (%)'])

    def closeEvent(self, event):
        """Đóng file CSV khi ứng dụng đóng"""
        self.csv_file.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HeartRateMonitor()
    window.show()
    sys.exit(app.exec_())
