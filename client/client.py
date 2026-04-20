import socket
import threading
import zlib
import base64
import io
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTabWidget, QTextEdit, QMessageBox, QScrollArea)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QPainter, QCursor


SERVER_PORT = 5555


class SignalEmitter(QObject):
    update_screenshot = pyqtSignal(object)
    update_status = pyqtSignal(str)
    connection_lost = pyqtSignal()


class RemoteControlClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.server_socket = None
        self.connected = False
        self.running = True
        self.server_screen_size = None
        self.client_screen_size = None
        self.emitter = SignalEmitter()
        
        self.emitter.update_screenshot.connect(self.display_screenshot)
        self.emitter.update_status.connect(self.update_status_label)
        self.emitter.connection_lost.connect(self.handle_connection_lost)
        
        self.init_ui()
    
    
    def init_ui(self):
        self.setWindowTitle("Remote Control Client")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(QLabel("Server IP:"))
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        self.ip_input.setText("192.168.31.11")
        connection_layout.addWidget(self.ip_input)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.connect_to_server)
        connection_layout.addWidget(self.connect_btn)
        
        self.status_label = QLabel("Not connected")
        connection_layout.addWidget(self.status_label)
        
        layout.addLayout(connection_layout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.remote_view_tab = QWidget()
        self.tabs.addTab(self.remote_view_tab, "Remote View")
        self.setup_remote_view()
        
        self.info_tab = QTextEdit()
        self.info_tab.setReadOnly(True)
        self.tabs.addTab(self.info_tab, "System Info")
        
        self.keyboard_tab = QWidget()
        self.tabs.addTab(self.keyboard_tab, "Keyboard")
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
        
        info_label = QLabel("Click on Remote View to focus, then type. Special keys below:")
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
        text_layout.addWidget(QLabel("Type text:"))
        
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text and press Send")
        self.text_input.returnPressed.connect(self.send_text)
        text_layout.addWidget(self.text_input)
        
        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.send_text)
        text_layout.addWidget(send_btn)
        
        layout.addLayout(text_layout)
    
    
    def connect_to_server(self):
        server_ip = self.ip_input.text().strip()
        
        if not server_ip:
            QMessageBox.warning(self, "Error", "Enter server IP address")
            return
        
        self.status_label.setText("Connecting...")
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
                
                self.info_tab.setText(f"PC Name: {pc_name}\nOS: {os_version}")
                self.connected = True
                self.status_label.setText(f"Connected to {server_ip}")
                self.connect_btn.setText("Disconnect")
                self.connect_btn.clicked.disconnect()
                self.connect_btn.clicked.connect(self.disconnect)
                self.connect_btn.setEnabled(True)
                
                threading.Thread(target=self.receive_data, daemon=True).start()
                
            elif response == "CONNECTED":
                self.connected = True
                self.status_label.setText(f"Connected to {server_ip}")
                threading.Thread(target=self.receive_data, daemon=True).start()
                
            elif response.startswith("BLOCKED"):
                QMessageBox.warning(self, "Blocked", "Access denied by server")
                self.server_socket.close()
                self.status_label.setText("Blocked")
                self.connect_btn.setEnabled(True)
            else:
                QMessageBox.warning(self, "Error", f"Unexpected response: {response}")
                self.server_socket.close()
                self.connect_btn.setEnabled(True)
                
        except socket.timeout:
            QMessageBox.warning(self, "Error", "Connection timeout")
            self.status_label.setText("Timeout")
            self.connect_btn.setEnabled(True)
        except ConnectionRefusedError:
            QMessageBox.warning(self, "Error", "Server not available")
            self.status_label.setText("Refused")
            self.connect_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
            self.status_label.setText("Error")
            self.connect_btn.setEnabled(True)
    
    
    def disconnect(self):
        self.running = False
        self.connected = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.status_label.setText("Disconnected")
        self.connect_btn.setText("Connect")
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.connect_btn.setEnabled(True)
        self.viewport.setText("Disconnected")
        self.viewport.setStyleSheet("background-color: #1a1a1a;")
    
    
    def handle_connection_lost(self):
        QMessageBox.warning(self, "Connection Lost", "Server connection lost")
        self.disconnect()
    
    
    def receive_data(self):
        while self.running and self.connected:
            try:
                size_data = self.server_socket.recv(4)
                if not size_data:
                    break
                
                size = int.from_bytes(size_data, byteorder='big')
                data = b''
                
                while len(data) < size:
                    chunk = self.server_socket.recv(8192)
                    if not chunk:
                        break
                    data += chunk
                
                try:
                    decompressed = zlib.decompress(data)
                    buffer = io.BytesIO(decompressed)
                    from PIL import Image
                    img = Image.open(buffer)
                    
                    if not self.server_screen_size:
                        self.server_screen_size = img.size
                    
                    self.emitter.update_screenshot.emit(img)
                    
                except Exception as e:
                    print(f"Image error: {e}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Receive error: {e}")
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
            
            img_bytes = img.tobytes("raw", "RGB")
            qimg = QImage(img_bytes, img.width, img.height, img.width * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)
            
            self.viewport.setPixmap(pixmap)
            self.viewport.setText("")
            
            if not self.client_screen_size:
                self.client_screen_size = (w, h)
                
        except Exception as e:
            print(f"Display error: {e}")
    
    
    def update_status_label(self, text):
        self.status_label.setText(text)
    
    
    def calculate_scaled_coords(self, x, y):
        if not self.server_screen_size or not self.client_screen_size:
            return x, y
        
        viewport_w = self.viewport.pixmap().width() if self.viewport.pixmap() else self.client_screen_size[0]
        viewport_h = self.viewport.pixmap().height() if self.viewport.pixmap() else self.client_screen_size[1]
        
        if viewport_w <= 0 or viewport_h <= 0:
            return x, y
        
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
    
    
    def keyPressEvent(self, event):
        if not self.connected:
            super().keyPressEvent(event)
            return
        
        key = event.key()
        
        if key == Qt.Key_Return:
            self.send_key("ENTER")
        elif key == Qt.Key_Tab:
            self.send_key("TAB")
        elif key == Qt.Key_Escape:
            self.send_key("ESC")
        elif key == Qt.Key_Backspace:
            self.send_key("BACKSPACE")
        elif key == Qt.Key_Space:
            self.send_key("SPACE")
        elif event.text():
            self.send_key(f"TEXT:{event.text()}")
        else:
            super().keyPressEvent(event)
    
    
    def closeEvent(self, event):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        event.accept()


def main():
    app = QApplication([])
    window = RemoteControlClient()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
