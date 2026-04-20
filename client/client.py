import socket
import threading
import zlib
import io
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTabWidget, QTextEdit, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap
from PIL import Image


SERVER_PORT = 5555
DISCOVERY_PORT = 5556
DISCOVERY_MESSAGE = "UA_HORIZON_SERVER"


class SignalEmitter(QObject):
    update_screenshot = pyqtSignal(object)
    update_status = pyqtSignal(str)
    connection_lost = pyqtSignal()
    server_found = pyqtSignal(str)


class RemoteControlClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_socket = None
        self.connected = False
        self.running = True
        self.server_screen_size = None
        self.viewport_size = None
        self.discovery_running = False
        self.found_ip = None
        self.emitter = SignalEmitter()
        
        self.emitter.update_screenshot.connect(self.display_screenshot)
        self.emitter.update_status.connect(self.update_status_label)
        self.emitter.connection_lost.connect(self.handle_connection_lost)
        self.emitter.server_found.connect(self.on_server_found)
        
        self.init_ui()
        self.start_discovery()
    
    
    def start_discovery(self):
        """Запуск прослушивания UDP для автообнаружения сервера"""
        self.discovery_running = True
        self.status_label.setText("Поиск сервера...")
        threading.Thread(target=self.discovery_listener, daemon=True).start()
    
    
    def discovery_listener(self):
        """Слушает UDP порт 5556 для обнаружения сервера"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            sock.bind(("", DISCOVERY_PORT))
        except Exception as e:
            print(f"Не удалось открыть порт: {e}")
            return
        
        sock.settimeout(1.0)
        
        while self.discovery_running:
            try:
                data, addr = sock.recvfrom(4096)
                message = data.decode('utf-8', errors='ignore')
                
                if message == DISCOVERY_MESSAGE:
                    self.found_ip = addr[0]
                    self.emitter.server_found.emit(addr[0])
            except socket.timeout:
                continue
            except Exception as e:
                if self.discovery_running:
                    print(f"Ошибка discovery: {e}")
        
        sock.close()
    
    
    def on_server_found(self, ip):
        """Обработка найденного сервера"""
        self.ip_input.setText(ip)
        self.status_label.setText(f"Найден: {ip}")
        # Автоподключение
        self.connect_to_server()
    
    
    def init_ui(self):
        self.setWindowTitle("Remote Control Client")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Подключение
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Server IP:"))
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.ip_input.setText("192.168.1.100")
        connection_layout.addWidget(self.ip_input)
        
        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self.connect_to_server)
        connection_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("Не подключено")
        connection_layout.addWidget(self.status_label)
        
        layout.addLayout(connection_layout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Вкладка просмотра
        self.remote_view_tab = QWidget()
        self.tabs.addTab(self.remote_view_tab, "Удалённый рабочий стол")
        self.setup_remote_view()
        
        # Вкладка информации
        self.info_tab = QTextEdit()
        self.info_tab.setReadOnly(True)
        self.tabs.addTab(self.info_tab, "Информация о системе")
        
        # Вкладка клавиатуры
        self.keyboard_tab = QWidget()
        self.tabs.addTab(self.keyboard_tab, "Клавиатура")
        self.setup_keyboard_tab()
    
    
    def setup_remote_view(self):
        layout = QVBoxLayout(self.remote_view_tab)
        
        self.viewport = QLabel()
        self.viewport.setAlignment(Qt.AlignCenter)
        self.viewport.setStyleSheet("background-color: #1a1a1a; border: 2px solid #333;")
        self.viewport.setMinimumSize(800, 600)
        self.viewport.setScaledContents(False)
        
        self.viewport.mousePressEvent = self.mouse_press
        self.viewport.mouseReleaseEvent = self.mouse_release
        self.viewport.mouseMoveEvent = self.mouse_move
        
        scroll = QScrollArea()
        scroll.setWidget(self.viewport)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
    
    
    def setup_keyboard_tab(self):
        layout = QVBoxLayout(self.keyboard_tab)
        
        info_label = QLabel("Кликните на 'Удалённый рабочий стол' для фокуса, затем печатайте. Специальные клавиши:")
        layout.addWidget(info_label)
        
        keys_layout = QHBoxLayout()
        
        special_keys = [
            ("Enter", "ENTER"), ("Tab", "TAB"), ("Esc", "ESC"),
            ("Space", "SPACE"), ("Backspace", "BACKSPACE")
        ]
        
        for name, key in special_keys:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, k=key: self.send_key(k))
            keys_layout.addWidget(btn)
        
        layout.addLayout(keys_layout)
        
        text_layout = QHBoxLayout()
        text_layout.addWidget(QLabel("Ввести текст:"))
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Введите текст и нажмите Отправить")
        self.text_input.returnPressed.connect(self.send_text)
        text_layout.addWidget(self.text_input)
        
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.send_text)
        text_layout.addWidget(send_btn)
        
        layout.addLayout(text_layout)
    
    
    def connect_to_server(self):
        server_ip = self.ip_input.text().strip()
        
        if not server_ip:
            QMessageBox.warning(self, "Ошибка", "Введите IP адрес сервера")
            return
        
        self.status_label.setText("Подключение...")
        self.connect_btn.setEnabled(False)
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.settimeout(10)
            self.server_socket.connect((server_ip, SERVER_PORT))
            
            response = self.server_socket.recv(1024).decode('utf-8')
            
            if response.startswith("INFO:"):
                system_info = response[5:]
                parts = system_info.split("|")
                pc_name = parts[0] if len(parts) > 0 else "Unknown"
                os_version = parts[1] if len(parts) > 1 else "Unknown"
                
                self.info_tab.setText(f"Имя ПК: {pc_name}\nОС: {os_version}")
                self.connected = True
                self.discovery_running = False  # Остановить поиск
                self.status_label.setText(f"Подключено к {server_ip}")
                self.connect_btn.setText("Отключиться")
                self.connect_btn.clicked.disconnect()
                self.connect_btn.clicked.connect(self.disconnect)
                self.connect_btn.setEnabled(True)
                
                threading.Thread(target=self.receive_data, daemon=True).start()
                
            elif response == "CONNECTED":
                self.connected = True
                self.discovery_running = False  # Остановить поиск
                self.status_label.setText(f"Подключено к {server_ip}")
                threading.Thread(target=self.receive_data, daemon=True).start()
                
            elif response.startswith("BLOCKED"):
                QMessageBox.warning(self, "Заблокировано", "Доступ запрещён сервером")
                self.server_socket.close()
                self.status_label.setText("Заблокировано")
                self.connect_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "Ошибка", f"Неожиданный ответ: {response}")
                self.server_socket.close()
                self.connect_btn.setEnabled(True)
                
        except socket.timeout:
            QMessageBox.warning(self, "Ошибка", "Время подключения истекло")
            self.status_label.setText("Таймаут")
            self.connect_btn.setEnabled(True)
        except ConnectionRefusedError:
            QMessageBox.warning(self, "Ошибка", "Сервер недоступен")
            self.status_label.setText("Отказано")
            self.connect_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            self.status_label.setText("Ошибка")
            self.connect_btn.setEnabled(True)
    
    
    def disconnect(self):
        self.running = False
        self.connected = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.status_label.setText("Отключено")
        self.connect_btn.setText("Подключиться")
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.connect_btn.setEnabled(True)
        self.viewport.setText("Отключено")
        self.viewport.setStyleSheet("background-color: #1a1a1a;")
        # Перезапуск поиска сервера
        self.start_discovery()
    
    
    def handle_connection_lost(self):
        QMessageBox.warning(self, "Соединение потеряно", "Связь с сервером потеряна")
        self.disconnect()
    
    
    def receive_data(self):
        while self.running and self.connected:
            try:
                # Стабильность: проверка данных
                size_data = self.server_socket.recv(4)
                if not size_data:
                    break
                
                # Проверка что получили 4 байта
                if len(size_data) < 4:
                    continue
                
                try:
                    size = int.from_bytes(size_data, byteorder='big')
                except Exception:
                    continue
                
                if size <= 0 or size > 10_000_000:
                    continue
                
                data = b''
                while len(data) < size:
                    chunk = self.server_socket.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                
                if len(data) != size:
                    continue
                
                try:
                    decompressed = zlib.decompress(data)
                    buffer = io.BytesIO(decompressed)
                    img = Image.open(buffer)
                    
                    if not self.server_screen_size:
                        self.server_screen_size = img.size
                    
                    self.emitter.update_screenshot.emit(img)
                    
                except Exception as e:
                    print(f"Ошибка изображения: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Ошибка приёма: {e}")
                break
        
        if self.running:
            self.emitter.connection_lost.emit()
    
    
    def display_screenshot(self, img):
        try:
            w = self.viewport.width()
            h = self.viewport.height()
            
            if w > 1 and h > 1:
                iw, ih = img.size
                r = min(w / iw, h / ih)
                new_size = (int(iw * r), int(ih * r))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Сохраняем размер viewport для масштабирования
            if not self.viewport_size:
                self.viewport_size = (w, h)
            
            img_bytes = img.tobytes("raw", "RGB")
            qimg = QImage(img_bytes, img.width, img.height, img.width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            self.viewport.setPixmap(pixmap)
            self.viewport.setText("")
            
        except Exception as e:
            print(f"Ошибка отображения: {e}")
    
    
    def update_status_label(self, text):
        self.status_label.setText(text)
    
    
    def calculate_scaled_coords(self, x, y):
        """Масштабирование координат под разрешение сервера"""
        if not self.server_screen_size:
            return x, y
        
        # Получаем размер отображаемого изображения
        pixmap = self.viewport.pixmap()
        if pixmap is None or pixmap.isNull():
            return x, y
        
        viewport_w = pixmap.width()
        viewport_h = pixmap.height()
        
        if viewport_w <= 0 or viewport_h <= 0:
            return x, y
        
        # Масштабирование
        scale_x = self.server_screen_size[0] / viewport_w
        scale_y = self.server_screen_size[1] / viewport_h
        
        return int(x * scale_x), int(y * scale_y)
    
    
    def send_mouse_event(self, action, x, y):
        if not self.connected or not self.server_socket:
            return
        
        scaled_x, scaled_y = self.calculate_scaled_coords(x, y)
        
        try:
            self.server_socket.sendall(f"MOUSE:{action},{scaled_x},{scaled_y}".encode('utf-8'))
        except:
            pass
    
    
    def mouse_press(self, event):
        if not self.connected:
            return
        
        if event.button() == Qt.LeftButton:
            self.send_mouse_event("LEFT_DOWN", event.x(), event.y())
        elif event.button() == Qt.RightButton:
            self.send_mouse_event("RIGHT_DOWN", event.x(), event.y())
    
    
    def mouse_release(self, event):
        if not self.connected:
            return
        
        if event.button() == Qt.LeftButton:
            self.send_mouse_event("LEFT_UP", event.x(), event.y())
        elif event.button() == Qt.RightButton:
            self.send_mouse_event("RIGHT_UP", event.x(), event.y())
    
    
    def mouse_move(self, event):
        if not self.connected:
            return
        
        self.send_mouse_event("MOVE", event.x(), event.y())
    
    
    def send_key(self, key):
        if not self.connected or not self.server_socket:
            return
        
        try:
            self.server_socket.sendall(f"KEY:{key}".encode('utf-8'))
        except:
            pass
    
    
    def send_text(self):
        if not self.connected or not self.server_socket:
            return
        
        text = self.text_input.text()
        if text:
            try:
                self.server_socket.sendall(f"KEY:TEXT:{text}".encode('utf-8'))
                self.text_input.clear()
            except:
                pass
    
    
    def closeEvent(self, event):
        self.running = False
        self.connected = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = RemoteControlClient()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
