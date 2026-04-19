"""
=============================================================================
СЕРВЕРНАЯ ЧАСТЬ (Server)
=============================================================================
Образовательный проект: "Инструмент для удалённой помощи члену семьи"

Назначение: Программа устанавливается на ПК того, кто помогает.
            Она позволяет видеть экран другого ПК и управлять файлами.

Автор: [Имя ученика]
Дата: 2026
Школа: [Название школы]
Предмет: Сетевые протоколы / Python

=============================================================================
ТЕОРЕТИЧЕСКАЯ ЧАСТЬ (для понимания принципа работы):
=============================================================================

1. Сервер - это программа, которая ожидает подключения от клиентов.
   - Сервер слушает определённый порт (в нашем случае 9999)
   - Когда клиент подключается, сервер принимает соединение
   - Затем они обмениваются данными

2. Tkinter - это встроенная библиотека Python для создания GUI.
   - Позволяет создавать окна, кнопки, изображения и т.д.
   - Проста в изучении, идеальна для учебных проектов

3. TCP-сервер работает так:
   1. socket() - создаём сокет
   2. bind() - связываем сокет с адресом и портом
   3. listen() - начинаем слушать (максимум 1 клиент)
   4. accept() - принимаем подключение клиента
   5. recv()/send() - обмен данными
   6. close() - закрываем соединение

=============================================================================
"""

import socket       # Библиотека для работы с сетью (TCP/IP)
import tkinter      # Библиотека для графического интерфейса
from tkinter import ttk, messagebox, scrolledtext  # Дополнительные виджеты Tkinter
import threading    # Библиотека для многозадачности
import base64       # Библиотека для декодирования данных (изображения)
import io           # Библиотека для работы с потоками данных
from PIL import Image, ImageTk  # Библиотека для работы с изображениями


# =============================================================================
# КОНФИГУРАЦИЯ ПРОГРАММЫ
# =============================================================================

# Порт, который слушает сервер (должен совпадать с портом клиента)
LISTEN_PORT = 9999

# Размер буфера для приёма данных (в байтах)
BUFFER_SIZE = 4096


# =============================================================================
# КЛАСС ГЛАВНОГО ОКНА ПРИЛОЖЕНИЯ
# =============================================================================

class RemoteHelperServer:
    """
    Класс главного окна сервера.
    
    Содержит:
    - Окно просмотра экрана (Remote View)
    - Панель файлового браузера (File Explorer)
    - Меню и кнопки управления
    
    Tkinter работает по принципу:
    - Widget (виджет) - любой элемент интерфейса (кнопка, окно, текст)
    - Pack/Grid - менеджеры расположения элементов
    - Event Loop - бесконечный цикл ожидания событий
    """
    
    def __init__(self, root):
        """
        Конструктор класса - инициализирует окно и его компоненты.
        
        Параметры:
            root - корневое окно Tkinter
        """
        self.root = root
        self.root.title("Удалённая помощь - Сервер")
        self.root.geometry("1000x700")
        
        # Переменные для хранения состояния
        self.client_socket = None  # Сокет для связи с клиентом
        self.current_path = "C:\\"  # Текущая папка в файловом браузере
        self.running = True  # Флаг работы программы
        
        # Создаём интерфейс
        self.create_widgets()
        
        # Запускаем сервер в отдельном потоке
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()
        
        # Запускаем поток приёма изображений
        self.receive_thread = threading.Thread(target=self.receive_screenshots, daemon=True)
        self.receive_thread.start()
    
    
    def create_widgets(self):
        """
        Создаёт все элементы графического интерфейса.
        
        Структура окна:
        +------------------------------------------+
        |  Меню (Remote View | File Explorer)     |
        +------------------------------------------+
        |                                          |
        |     Область изображения (скриншот)      |
        |                                          |
        +------------------------------------------+
        |  Панель навигации (кнопки папок)        |
        +------------------------------------------+
        |  Список файлов (File Explorer)          |
        +------------------------------------------+
        """
        
        # -----------------------------------------------------------------------------
        # Создаём меню (вкладки сверху)
        # -----------------------------------------------------------------------------
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
        
        Компоненты:
        - Метка статуса подключения
        - Область для отображения скриншота
        - Кнопка обновления
        """
        # Метка статуса
        self.status_label = ttk.Label(
            self.view_frame, 
            text="Ожидание подключения клиента...",
            font=("Arial", 12)
        )
        self.status_label.pack(pady=10)
        
        # Рамка для изображения
        self.image_frame = ttk.Frame(self.view_frame, borderwidth=2, relief="solid")
        self.image_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Метка для отображения изображения (placeholder)
        self.image_label = ttk.Label(
            self.image_frame,
            text="Здесь будет отображаться экран клиента",
            font=("Arial", 14),
            foreground="gray"
        )
        self.image_label.pack(fill='both', expand=True)
        
        # Переменная для хранения изображения
        self.photo_image = None
    
    
    def create_file_explorer_tab(self):
        """
        Создаёт вкладку File Explorer (файловый браузер).
        
        Компоненты:
        - Текущий путь
        - Кнопки навигации (Вверх, Домой, Обновить)
        - Список файлов и папок
        """
        # -----------------------------------------------------------------------------
        # Панель навигации по папкам
        # -----------------------------------------------------------------------------
        nav_frame = ttk.Frame(self.explorer_frame)
        nav_frame.pack(fill='x', padx=10, pady=10)
        
        # Метка "Текущий путь:"
        ttk.Label(nav_frame, text="Текущий путь:").pack(side='left', padx=5)
        
        # Поле отображения текущего пути
        self.path_label = ttk.Label(nav_frame, text=self.current_path, font=("Courier", 10))
        self.path_label.pack(side='left', padx=5)
        
        # Кнопка "Вверх" (родительская папка)
        self.up_button = ttk.Button(
            nav_frame, 
            text="⬆ Вверх", 
            command=self.go_up
        )
        self.up_button.pack(side='left', padx=5)
        
        # Кнопка "Домой" (C:\)
        self.home_button = ttk.Button(
            nav_frame, 
            text="🏠 Домой", 
            command=self.go_home
        )
        self.home_button.pack(side='left', padx=5)
        
        # Кнопка "Обновить"
        self.refresh_button = ttk.Button(
            nav_frame, 
            text="🔄 Обновить", 
            command=self.refresh_files
        )
        self.refresh_button.pack(side='left', padx=5)
        
        # -----------------------------------------------------------------------------
        # Список файлов и папок (Listbox)
        # -----------------------------------------------------------------------------
        list_frame = ttk.Frame(self.explorer_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Скроллбар (полоса прокрутки)
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Listbox - список с возможностью выбора
        self.file_list = tkinter.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set,
            font=("Courier", 10),
            selectmode='single'  # Можно выбрать только один элемент
        )
        self.file_list.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.file_list.yview)
        
        # Привязываем событие двойного клика к открытию папки
        self.file_list.bind('<Double-Button-1>', self.on_file_double_click)
        
        # Кнопка "Открыть выбранное"
        open_button = ttk.Button(
            self.explorer_frame, 
            text="Открыть", 
            command=self.open_selected
        )
        open_button.pack(pady=5)
    
    
    # ============================================================================
    # ФУНКЦИИ СЕРВЕРА (сетевая часть)
    # ============================================================================
    
    def start_server(self):
        """
        Запускает TCP-сервер и ожидает подключения клиента.
        
        Процесс:
        1. Создаём сокет
        2. Привязываем к порту (bind)
        3. Слушаем порт (listen)
        4. Принимаем подключение (accept)
        5. Запускаем обработку данных
        
        Это работает в отдельном потоке, чтобы не блокировать GUI.
        """
        try:
            # Создаём TCP-сокет
            # socket.AF_INET - IPv4 адресация
            # socket.SOCK_STREAM - TCP протокол
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Разрешаем переиспользование адреса (полезно при перезапуске)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Привязываем сокет к адресу и порту
            # '' означает "слушать на всех интерфейсах"
            server_socket.bind(('', LISTEN_PORT))
            
            # Начинаем слушать (максимум 1 клиент в очереди)
            server_socket.listen(1)
            
            print(f"[Сервер] Ожидание подключения на порту {LISTEN_PORT}...")
            
            # Обновляем статус в GUI (используем after для безопасности в потоке)
            self.root.after(0, lambda: self.status_label.config(
                text=f"Ожидание подключения на порту {LISTEN_PORT}..."
            ))
            
            # Принимаем подключение (блокирующая операция)
            # accept() возвращает новый сокет для общения с клиентом
            self.client_socket, client_address = server_socket.accept()
            
            print(f"[Сервер] Клиент подключён: {client_address}")
            
            # Обновляем статус
            self.root.after(0, lambda: self.status_label.config(
                text=f"Подключено к: {client_address[0]}:{client_address[1]}"
            ))
            
            # Закрываем слушающий сокет (он нам больше не нужен)
            server_socket.close()
            
            # Запускаем приём скриншотов
            self.receive_thread = threading.Thread(target=self.receive_screenshots, daemon=True)
            self.receive_thread.start()
            
            # Запускаем обработку команд файлового браузера
            self.explorer_thread = threading.Thread(target=self.handle_file_commands, daemon=True)
            self.explorer_thread.start()
            
        except Exception as e:
            print(f"[Сервер] Ошибка: {e}")
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
    
    
    def receive_screenshots(self):
        """
        Принимает скриншоты от клиента и отображает их в окне.
        
        Процесс:
        1. Получаем размер данных (4 байта)
        2. Читаем данные изображения
        3. Декодируем из base64
        4. Конвертируем в формат Tkinter
        5. Отображаем в окне
        
        Цикл работает постоянно, пока есть подключение.
        """
        while self.running and self.client_socket is None:
            # Ждём, пока не подключится клиент
            time.sleep(0.5)
        
        while self.running and self.client_socket:
            try:
                # Шаг 1: Получаем размер данных (4 байта)
                # to_bytes(4, byteorder='big') означает 4-байтное число
                size_data = self.client_socket.recv(4)
                
                if not size_data:
                    # Клиент отключился
                    break
                
                # Преобразуем 4 байта в число
                size = int.from_bytes(size_data, byteorder='big')
                
                # Шаг 2: Получаем данные изображения
                # Может прийти несколько пакетов, поэтому читаем пока не получим всё
                data = b''
                while len(data) < size:
                    chunk = self.client_socket.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                
                # Шаг 3: Декодируем из base64
                image_data = base64.b64decode(data)
                
                # Шаг 4: Конвертируем в изображение PIL
                buffer = io.BytesIO(image_data)
                img = Image.open(buffer)
                
                # Шаг 5: Масштабируем, если слишком большое
                # Получаем размер окна
                width = self.image_frame.winfo_width()
                height = self.image_frame.winfo_height()
                
                if width > 1 and height > 1:  # Окно уже создано
                    # Вычисляем новый размер (сохраняем пропорции)
                    img_width, img_height = img.size
                    ratio = min(width / img_width, height / img_height)
                    new_size = (int(img_width * ratio), int(img_height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Шаг 6: Конвертируем в формат Tkinter
                self.photo_image = ImageTk.PhotoImage(img)
                
                # Шаг 7: Отображаем в окне
                # Используем after для безопасности в потоке
                self.root.after(0, self.update_image_display)
                
            except Exception as e:
                print(f"[Сервер] Ошибка приёма скриншота: {e}")
                break
        
        print("[Сервер] Поток приёма скриншотов завершён")
    
    
    def update_image_display(self):
        """
        Обновляет отображаемое изображение в окне.
        Вызывается из главного потока через after().
        """
        if self.photo_image:
            self.image_label.config(image=self.photo_image, text="")
    
    
    def handle_file_commands(self):
        """
        Обрабатывает команды файлового браузера.
        Ждёт команды от GUI и отправляет их клиенту.
        """
        while self.running and self.client_socket:
            time.sleep(0.5)
        
        print("[Сервер] Поток файлового браузера завершён")
    
    
    # ============================================================================
    # ФУНКЦИИ ФАЙЛОВОГО БРАУЗЕРА
    # ============================================================================
    
    def send_list_command(self, path):
        """
        Отправляет команду клиенту на получение списка файлов.
        
        Команда имеет формат: LIST:<путь>
        Клиент отвечает списком файлов (каждая строка: имя|тип)
        """
        if not self.client_socket:
            messagebox.showwarning("Предупреждение", "Клиент не подключён")
            return
        
        try:
            # Отправляем команду
            command = f"LIST:{path}"
            self.client_socket.sendall(command.encode('utf-8'))
            
            # Ждём ответ (с небольшим таймаутом)
            self.client_socket.settimeout(5)
            response = self.client_socket.recv(65536).decode('utf-8')
            
            # Разбираем ответ
            if response.startswith("ERROR:"):
                messagebox.showerror("Ошибка", response[6:])
                return
            
            # Очищаем список
            self.file_list.delete(0, tkinter.END)
            
            # Добавляем файлы в список
            lines = response.split('\n')
            for line in lines:
                if line:
                    parts = line.split('|')
                    name = parts[0]
                    file_type = parts[1] if len(parts) > 1 else "FILE"
                    
                    # Добавляем иконку в зависимости от типа
                    if file_type == "DIR":
                        self.file_list.insert(tkinter.END, f"📁 {name}")
                    else:
                        self.file_list.insert(tkinter.END, f"📄 {name}")
            
            # Обновляем текущий путь
            self.current_path = path
            self.path_label.config(text=path)
            
        except socket.timeout:
            messagebox.showwarning("Таймаут", "Клиент не отвечает")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    
    def go_up(self):
        """
        Переходит в родительскую папку (вверх по дереву).
        """
        parent = os.path.dirname(self.current_path)
        if parent:
            self.send_list_command(parent)
    
    
    def go_home(self):
        """
        Переходит в корневую папку диска C:\.
        """
        self.send_list_command("C:\\")
    
    
    def refresh_files(self):
        """
        Обновляет список файлов в текущей папке.
        """
        self.send_list_command(self.current_path)
    
    
    def on_file_double_click(self, event):
        """
        Обрабатывает двойной клик по файлу/папке.
        Если папка - переходим в неё.
        """
        selection = self.file_list.curselection()
        if selection:
            item = self.file_list.get(selection[0])
            # Убираем иконку из начала
            name = item[2:] if item.startswith("📁 ") or item.startswith("📄 ") else item
            
            # Формируем новый путь
            new_path = os.path.join(self.current_path, name)
            
            # Проверяем, папка ли это (по иконке)
            if item.startswith("📁 "):
                self.send_list_command(new_path)
            else:
                # Если файл - показываем информацию
                self.show_file_info(new_path)
    
    
    def open_selected(self):
        """
        Открывает выбранный файл или папку.
        """
        selection = self.file_list.curselection()
        if selection:
            self.on_file_double_click(None)
    
    
    def show_file_info(self, path):
        """
        Показывает информацию о выбранном файле.
        """
        if not self.client_socket:
            return
        
        try:
            # Запрашиваем информацию
            command = f"INFO:{path}"
            self.client_socket.sendall(command.encode('utf-8'))
            
            self.client_socket.settimeout(5)
            response = self.client_socket.recv(4096).decode('utf-8')
            
            messagebox.showinfo("Информация о файле", response)
            
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


# =============================================================================
# ДОПОЛНИТЕЛЬНЫЙ ИМПОРТ (нужен для os.path в функциях)
# =============================================================================

import os
import time


# =============================================================================
# ТОЧКА ВХОДА В ПРОГРАММУ
# =============================================================================

def main():
    """
    Главная функция - создаёт и запускает приложение.
    
    Tkinter работает по принципу event loop (цикл событий):
    1. Создаём корневое окно (Tk())
    2. Создаём приложение (класс RemoteHelperServer)
    3. Запускаем mainloop() - бесконечный цикл ожидания событий
    
    mainloop() обрабатывает:
    - Нажатия кнопок
    - Движения мыши
    - Сетевые события (через after())
    - И многое другое
    """
    # Создаём корневое окно Tkinter
    root = tkinter.Tk()
    
    # Создаём приложение
    app = RemoteHelperServer(root)
    
    # Обработка закрытия окна
    def on_closing():
        app.running = False
        if app.client_socket:
            app.client_socket.close()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Запускаем главный цикл (event loop)
    # Это бесконечный цикл, который ждёт события
    print("[Сервер] Запущен. Ожидание подключения...")
    root.mainloop()


# Запускаем программу
if __name__ == "__main__":
    main()