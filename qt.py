#!/usr/bin/python3

import sys
import random
import socket
import docker
import os
import shutil
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QLabel, QCheckBox, QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView, QTabWidget, QTextEdit, QComboBox, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QIntValidator

def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except socket.error:
            return False

class ContainerThread(QThread):
    update_signal = pyqtSignal(str, int, str, int, str)  # Имя, тип, IP, порт, статус, состояние
    log_signal = pyqtSignal(str, str)
    def __init__(self, index, container_type, image_name, script_path_host, script_path_cont, host_info_directory, command):
        QThread.__init__(self)
        self.index = index
        self.container_type = container_type
        self.image_name = image_name
        self.script_path_host = script_path_host
        self.script_path_cont = script_path_cont
        self.host_info_directory = host_info_directory
        self.command = command
        self.client = docker.from_env()

    def run(self):
        container_name = f"astra{self.index:02d}"
        used_ports = set()

        while True:
            host_port = random.randint(1024, 65535)
            if host_port not in used_ports and is_port_free(host_port):
                used_ports.add(host_port)
                break

        container_label = f"astra_type={self.container_type}"

        container_options = {
            "command": self.command,
            "restart_policy": {"Name": "always"},
            "stdin_open": True,
            "tty": True,
            "volumes": {"/root/space/archive": {"bind": "/mnt/host_archive", "mode": "ro"}},
            "ports": {"22/tcp": host_port},
            "labels": {"astra_type": str(self.container_type)}
        }

        try:
            container = self.client.containers.create(self.image_name, name=container_name, **container_options)

            self.update_signal.emit(container_name, self.container_type, None, None, "Создан")
            self.log_signal.emit(container_name, f"Контейнер {container_name} создан")

            max_attempts = 10
            for attempt in range(max_attempts):
                try:
                    container.start()
                    container.reload()
                    container_ip = container.attrs['NetworkSettings']['IPAddress']

                    print(f"Создан и запущен контейнер {container_name} типа {self.container_type} с IP-адресом {container_ip}, портом {host_port} и ID {container.id}")
                    self.log_signal.emit(container_name, f"Создан и запущен контейнер {container_name} типа {self.container_type} с IP-адресом {container_ip} и портом {host_port}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Запущен")
                    break
                except docker.errors.APIError as e:
                    print(f"Ошибка запуска: Попытка {attempt + 1} из {max_attempts}")
                    self.log_signal.emit(container_name, f"Ошибка запуска: Попытка {attempt + 1} из {max_attempts}")
                    self.update_signal.emit(container_name, self.container_type, None, None, "Ошибка запуска")
                    if attempt == max_attempts - 1:
                        raise

            if self.container_type == 1:
                try:
                    try:
                        copy_cmd = f"docker cp {os.path.join(self.script_path_host)} {container_name}:{self.script_path_cont}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                        self.log_signal.emit(container_name, f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                    print(f"Выполняется скрипт для контейнера: {container_name}")
                    self.log_signal.emit(container_name, f"Выполняется скрипт для контейнера: {container_name}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Выполняется скрипт")
                    exec_id = container.exec_run(cmd=["bin/sudo", "/bin/bash", "/home/poison/gg.sh"])
                    print(f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.log_signal.emit(container_name, f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Сркипт выполнен")
                    os.makedirs(os.path.join(self.host_info_directory, container_name), exist_ok=True)
                    try:
                        copy_cmd = f"docker cp {container_name}:/home/poison/info/. {os.path.join(self.host_info_directory, container_name)}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                        self.log_signal.emit(container_name, f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                    container.exec_run(cmd=["/bin/bash", "-c", "rm -r /home/poison/info"])
                    container.exec_run(cmd=["/bin/bash", "-c", "sudo service ssh start"])
                    print(f"Контейнер {container_name} готов!")
                    self.log_signal.emit(container_name, f"Контейнер {container_name} готов!")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Готово!")
                except Exception as e:
                    print(f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.log_signal.emit(container_name, f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Ошибка!")

            elif self.container_type == 2:
                try:
                    try:
                        copy_cmd = f"docker cp {os.path.join(self.script_path_host)} {container_name}:{self.script_path_cont}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                        self.log_signal.emit(container_name, f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                    print(f"Выполняется скрипт для контейнера: {container_name}")
                    self.log_signal.emit(container_name, f"Выполняется скрипт для контейнера: {container_name}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Выполняется скрипт")
                    exec_id = container.exec_run(cmd=["bin/sudo", "/bin/bash", "/home/poison/gg.sh"])
                    print(f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.log_signal.emit(container_name, f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Сркипт выполнен")
                    os.makedirs(os.path.join(self.host_info_directory, container_name), exist_ok=True)
                    try:
                        copy_cmd = f"docker cp {container_name}:/home/poison/info/. {os.path.join(self.host_info_directory, container_name)}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                        self.log_signal.emit(container_name, f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                    container.exec_run(cmd=["/bin/bash", "-c", "rm -r /home/poison/info"])
                    container.exec_run(cmd=["/bin/bash", "-c", "sudo service ssh start"])
                    print(f"Контейнер {container_name} готов!")
                    self.log_signal.emit(container_name, f"Контейнер {container_name} готов!")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Готово!")
                except Exception as e:
                    print(f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.log_signal.emit(container_name, f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Ошибка!")

            elif self.container_type == 3:
                try:
                    try:
                        copy_cmd = f"docker cp {os.path.join(self.script_path_host)} {container_name}:{self.script_path_cont}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                        self.log_signal.emit(container_name, f"Скрипт успешно скопирован из {os.path.join(self.script_path_host)} в контейнер {container_name}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из {os.path.join(self.script_path_host)} в контейнер {container_name}: {e}")
                    print(f"Выполняется скрипт для контейнера: {container_name}")
                    self.log_signal.emit(container_name, f"Выполняется скрипт для контейнера: {container_name}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Выполняется скрипт")
                    exec_id = container.exec_run(cmd=["bin/sudo", "/bin/bash", "/home/poison/gg.sh"])
                    print(f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.log_signal.emit(container_name, f"Результат выполнения скрипта в контейнере {container_name}:\n{exec_id.output.decode('utf-8')}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Сркипт выполнен")
                    os.makedirs(os.path.join(self.host_info_directory, container_name), exist_ok=True)
                    try:
                        copy_cmd = f"docker cp {container_name}:/home/poison/info/. {os.path.join(self.host_info_directory, container_name)}"
                        subprocess.run(copy_cmd, shell=True, check=True)
                        print(f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                        self.log_signal.emit(container_name, f"Информация успешно скопирована из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}")
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                        self.log_signal.emit(container_name, f"Ошибка при копировании из контейнера {container_name} в {os.path.join(self.host_info_directory, container_name)}: {e}")
                    container.exec_run(cmd=["/bin/bash", "-c", "rm -r /home/poison/info"])
                    container.exec_run(cmd=["/bin/bash", "-c", "sudo service ssh start"])
                    print(f"Контейнер {container_name} готов!")
                    self.log_signal.emit(container_name, f"Контейнер {container_name} готов!")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Готово!")
                except Exception as e:
                    print(f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.log_signal.emit(container_name, f"Ошибка при выполнении операций в контейнере {container_name}: {e}")
                    self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Ошибка!")

        except docker.errors.DockerException as e:
            print(f"Ошибка при создании контейнера {container_name}: {e}")
            self.log_signal.emit(container_name, f"Ошибка при создании контейнера {container_name}: {e}")
            self.update_signal.emit(container_name, self.container_type, container_ip, host_port, "Ошибка при создании!")

# Функционал для отключения сортировки первого столбца
class CustomHeader(QHeaderView):
    toggleCheckboxes = pyqtSignal()  # Сигнал для переключения чекбоксов

    def __init__(self, orientation, parent=None):
        super(CustomHeader, self).__init__(orientation, parent)

    def mousePressEvent(self, event):
        index = self.logicalIndexAt(event.pos())
        if index == 0:
            # Если клик по первому столбцу, отправляем сигнал для переключения чекбоксов
            self.toggleCheckboxes.emit()
        else:
            super(CustomHeader, self).mousePressEvent(event)

class DockerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.client = docker.from_env()
        self.initUI()
        self.threads = []
        self.host_info_directory = "/home/user/docker/info"

        # Таймер для периодического обновления статусов контейнеров
        self.statusUpdateTimer = QTimer(self)
        self.statusUpdateTimer.timeout.connect(self.refreshContainerStatuses)
        self.statusUpdateTimer.start(5000)  # Обновлять каждые 5 секунд

        self.loadExistingContainers()
        self.loadInfoExistingContainers()

        self.signals_connected = False

    def loadExistingContainers(self):
        existing_containers = self.client.containers.list(all=True)
        for container in existing_containers:
            self.containerSelector.addItem(container.name)

    def loadInfoExistingContainers(self):
        existing_containers = self.client.containers.list(all=True)
        for container in existing_containers:
            if container.name.startswith("astra"):
                try:
                    container.reload()
                    container_ip = container.attrs['NetworkSettings']['IPAddress']
                    host_port = list(container.attrs['NetworkSettings']['Ports'].values())[0][0]['HostPort']
                    container_type = container.attrs['Config']['Labels'].get('astra_type', 'Неизвестный тип')
                    container_status = self.translate_status(container.status)
                    self.updateTable(container.name, container_type, container_ip, host_port, container_status)
                except Exception as e:
                    print(f"Ошибка при получении информации о контейнере {container.name}: {e}")
                    self.log_signal.emit(container_name, f"Ошибка при получении информации о контейнере {container.name}: {e}")

    def refreshContainerStatuses(self):
        for row in range(self.table.rowCount()):
            container_name = self.table.item(row, 1).text()
            try:
                container = self.client.containers.get(container_name)
                status = container.status
                translated_status = self.translate_status(status)
            except docker.errors.NotFound:
                translated_status = "Не найден"
            except Exception as e:
                translated_status = f"Ошибка: {e}"

            status_item = self.table.item(row, 5)
            if status_item is None:
                status_item = QTableWidgetItem()
                self.table.setItem(row, 5, status_item)
            status_item.setText(translated_status)
            status_item.setTextAlignment(Qt.AlignCenter)

    def initUI(self):
        self.setWindowTitle('Программное средство генерации заданий')
        layout = QVBoxLayout()

        # Создаем виджет вкладок
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка управления контейнерами
        self.containerTab = QWidget()
        self.setupContainerTab()
        self.tabs.addTab(self.containerTab, "Управление контейнерами")

        # Вкладка для логов
        self.logTab = QWidget()
        self.setupLogTab()
        self.tabs.addTab(self.logTab, "Логи")

        self.setLayout(layout)
        self.resize(700, 600)

    def setupContainerTab(self):
        layout = QVBoxLayout(self.containerTab)

        edit_layout = QHBoxLayout()
        self.label = QLabel('Введите количество контейнеров:')
        edit_layout.addWidget(self.label)

        self.line_edit = QLineEdit()
        self.line_edit.setValidator(QIntValidator(1, 999))
        edit_layout.addWidget(self.line_edit)
        edit_layout.addWidget(self.line_edit)

        layout.addLayout(edit_layout)

        self.label = QLabel('Выберите типы контейнеров:')
        layout.addWidget(self.label)

        self.type_checkboxes = []
        for i in range(1, 4):
            checkbox = QCheckBox(f"Тип задания {i}")
            self.type_checkboxes.append(checkbox)
            layout.addWidget(checkbox)

        # Создаем горизонтальный макет для кнопок
        button_layout = QHBoxLayout()
        button1_layout = QHBoxLayout()
        self.button = QPushButton('Создать контейнер(ы)')
        self.button.clicked.connect(self.create_containers)
        button_layout.addWidget(self.button)

        self.deleteButton = QPushButton('Удалить контейнер(ы)')
        self.deleteButton.clicked.connect(self.deleteContainers)
        button1_layout.addWidget(self.deleteButton)

        self.stopButton = QPushButton('Остановить контейнер(ы)')
        self.stopButton.clicked.connect(self.stopContainers)
        button_layout.addWidget(self.stopButton)

        self.startButton = QPushButton('Запустить контейнер(ы)')
        self.startButton.clicked.connect(self.startContainers)
        button1_layout.addWidget(self.startButton)

        self.pauseButton = QPushButton('Приостановить контейнер(ы)')
        self.pauseButton.clicked.connect(self.pauseContainers)
        button_layout.addWidget(self.pauseButton)

        self.resumeButton = QPushButton('Возобновить контейнер(ы)')
        self.resumeButton.clicked.connect(self.resumeContainers)
        button1_layout.addWidget(self.resumeButton)

        layout.addLayout(button_layout)  # Добавляем горизонтальный макет в основной макет
        layout.addLayout(button1_layout)

        # Создаем таблицу
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(['', 'Имя', 'Тип', 'IP', 'Порт', 'Статус', 'Состояние'])
        # Функционал для отключения сортировки первого столбца
        header = CustomHeader(Qt.Horizontal, self.table)
        header.toggleCheckboxes.connect(self.toggleCheckboxes)  # Подключаем сигнал к слоту
        self.table.setHorizontalHeader(header)
        self.table.horizontalHeader().setStretchLastSection(True)  # Последний столбец заполняет оставшееся пространство
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)  # Выравнивание по содержимому
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)  # Первый столбец фиксированной ширины
        self.table.setColumnWidth(0, 25)  # Установка ширины первого столбца
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 120)

        layout.addWidget(self.table)

        # Устанавливаем сортировку по умолчанию по столбцу с именем контейнера
        self.table.horizontalHeader().setSortIndicator(1, Qt.AscendingOrder)
        self.table.setSortingEnabled(True)

        # Подключаем событие клика по заголовку столбца
        self.table.horizontalHeader().sectionClicked.connect(self.onHeaderClicked)

    def setupLogTab(self):
        log_layout = QVBoxLayout(self.logTab)
        self.containerSelector = QComboBox()
        log_layout.addWidget(self.containerSelector)

        self.logTextEdit = QTextEdit()
        self.logTextEdit.setReadOnly(True)
        log_layout.addWidget(self.logTextEdit)

        # Обновление логов при изменении выбранного контейнера
        self.containerSelector.currentTextChanged.connect(self.updateLogDisplay)

        # Словарь для хранения логов по контейнерам
        self.containerLogs = {}

    def logMessage(self, container_name, message):
        # Проверяем, существует ли уже имя контейнера в выпадающем списке
        if container_name not in self.containerLogs:
            self.containerLogs[container_name] = ""
            if self.containerSelector.findText(container_name) == -1:
                self.containerSelector.addItem(container_name)  # Добавляем имя контейнера, если его еще нет

        self.containerLogs[container_name] += message + "\n\n"

        # Обновляем отображение лога, если выбран соответствующий контейнер
        if self.containerSelector.currentText() == container_name:
            self.updateLogDisplay(container_name)

    def updateLogDisplay(self, container_name):
        # Обновление текстового поля с логами
        if container_name in self.containerLogs:
            self.logTextEdit.setText(self.containerLogs[container_name])
        else:
            self.logTextEdit.clear()

    def logContainerAction(self, container_name, message):
        print(message)
        self.logMessage(container_name, message)

    def find_available_indices(self, desired_count):
        existing_containers = self.client.containers.list(all=True)
        existing_indices = set()
        for container in existing_containers:
            if container.name.startswith("astra"):
                try:
                    index = int(container.name[5:])
                    existing_indices.add(index)
                except ValueError:
                    continue  # Если имя контейнера не соответствует ожидаемому формату

        available_indices = []
        for i in range(1, desired_count + len(existing_indices) + 1):
            if i not in existing_indices and len(available_indices) < desired_count:
                available_indices.append(i)

        return available_indices

    def create_containers(self):
        if not self.line_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, укажите количество контейнеров.")
            return

        # Проверка и создание директории /home/user/docker/info
        if not os.path.exists(self.host_info_directory):
            os.makedirs(self.host_info_directory)

        num_containers = int(self.line_edit.text())
        available_indices = self.find_available_indices(num_containers)
        selected_types = [i+1 for i, cb in enumerate(self.type_checkboxes) if cb.isChecked()]

        if not selected_types:
            QMessageBox.warning(self, 'Ошибка', 'Не выбран ни один тип контейнера.', QMessageBox.Ok)
            return

        num_containers = int(self.line_edit.text())
        image_name = "astra:1.0"
        script_path_host = "/root/space/scripts/type1.sh"
        script_path_cont = "/home/poison/"
        command = "/bin/bash"

        for index in available_indices:
            container_type = random.choice(selected_types)
            container_name = f"astra{index:02d}"
            # Проверяем, есть ли уже контейнер с таким именем в выпадающем списке
            if self.containerSelector.findText(container_name) == -1:
                self.containerSelector.addItem(container_name)
            thread = ContainerThread(index, container_type, image_name, script_path_host, script_path_cont, self.host_info_directory, command)
            thread.update_signal.connect(self.updateTable)
            if not self.signals_connected:
                thread.log_signal.connect(self.logMessage)
                self.signals_connected = True
            self.threads.append(thread)
            thread.start()

    def is_any_container_selected(self):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                return True
        return False

    def stopContainers(self):
        if not self.is_any_container_selected():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите хотя бы один контейнер.")
            return

        script_running_containers = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    state_item = self.table.item(row, 6)
                    if state_item and state_item.text() == "Выполняется скрипт":
                        script_running_containers.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if script_running_containers:
            reply = QMessageBox.question(self, "Предупреждение",
                                        "Остановка контейнера(ов) " + ", ".join(script_running_containers) +
                                        " прервет выполнение скрипта. Продолжить?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return

        already_stopped = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                status = self.table.item(row, 5).text()
                if status == "Остановлен":
                    already_stopped.append(container_name)
                elif status == "Выполняется скрипт":
                    reply = QMessageBox.question(self, 'Подтверждение остановки',
                                                "Один или несколько выбранных контейнеров выполняют скрипт. "
                                                "Остановка может нарушить их работу. Продолжить?",
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                    if reply == QMessageBox.No:
                        return

        if already_stopped:
            QMessageBox.warning(self, "Предупреждение", "Контейнер(ы) " + ", ".join(already_stopped) +
                                " уже остановлен(ы).")
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked and self.table.item(row, 1).text() not in already_stopped:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    container.stop()
                    self.logContainerAction(container_name, f"Контейнер {container_name} остановлен")
                    # Обновляем статус контейнера в таблице
                    self.updateTable(container_name, None, None, None, None)
                except docker.errors.NotFound:
                    self.logContainerAction(container_name, f"Контейнер {container_name} не найден")
                except Exception as e:
                    self.logContainerAction(container_name, f"Ошибка при остановке контейнера {container_name}: {e}")

    def deleteContainers(self):
        if not self.is_any_container_selected():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите хотя бы один контейнер.")
            return

        non_stopped_containers = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status != 'exited':  # Проверка, что контейнер остановлен
                        non_stopped_containers.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if non_stopped_containers:
            QMessageBox.warning(self, "Ошибка", "Невозможно удалить неостановленные контейнеры: " + ", ".join(non_stopped_containers))
            return

        non_existent = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    self.client.containers.get(container_name)
                except docker.errors.NotFound:
                    non_existent.append(container_name)

        if non_existent:
            QMessageBox.warning(self, "Предупреждение", "Контейнер(ы) " + ", ".join(non_existent) +
                                " не существуют или уже удалены.")
            return

        rows_to_delete = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked and self.table.item(row, 1).text() not in non_existent:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    container.remove()
                    self.logContainerAction(container_name, f"Контейнер {container_name} удален")
                    rows_to_delete.append(row)

                    # Удаление соответствующей директории
                    directory_path = os.path.join(self.host_info_directory, container_name)
                    if os.path.exists(directory_path):
                        shutil.rmtree(directory_path)
                        self.logContainerAction(container_name, f"Директория {directory_path} удалена")

                except docker.errors.NotFound:
                    self.logContainerAction(container_name, f"Контейнер {container_name} не найден или уже удален")
                except Exception as e:
                    self.logContainerAction(container_name, f"Ошибка при удалении контейнера {container_name}: {e}")

        for row in sorted(rows_to_delete, reverse=True):
            self.table.removeRow(row)

    def pauseContainers(self):
        if not self.is_any_container_selected():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите хотя бы один контейнер.")
            return

        non_running_containers = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status != 'running':  # Проверяем, что контейнер запущен
                        non_running_containers.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if non_running_containers:
            QMessageBox.warning(self, "Ошибка", "Невозможно приостановить не запущенные контейнеры: " + ", ".join(non_running_containers))
            return

        already_paused = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status == 'paused':
                        already_paused.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if already_paused:
            QMessageBox.warning(self, "Предупреждение", "Контейнер(ы) " + ", ".join(already_paused) +
                                " уже приостановлен(ы).")
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    container.pause()
                    self.logContainerAction(container_name, f"Контейнер {container_name} приостановлен")
                    # Обновляем статус контейнера в таблице
                    self.updateTable(container_name, None, None, None, None)
                except docker.errors.NotFound:
                    self.logContainerAction(container_name, f"Контейнер {container_name} не найден")
                except Exception as e:
                    self.logContainerAction(container_name, f"Ошибка при приостановке контейнера {container_name}: {e}")

    def resumeContainers(self):
        if not self.is_any_container_selected():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите хотя бы один контейнер.")
            return

        non_paused_containers = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status != 'paused':  # Проверяем, что контейнер приостановлен
                        non_paused_containers.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if non_paused_containers:
            QMessageBox.warning(self, "Ошибка", "Невозможно возобновить работу не приостановленных контейнеров: " + ", ".join(non_paused_containers))
            return

        already_resumed = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status == 'running':
                        already_resumed.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if already_resumed:
            QMessageBox.warning(self, "Предупреждение", "Контейнер(ы) " + ", ".join(already_resumed) +
                                " уже работают.")
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    container.unpause()
                    self.logContainerAction(container_name, f"Контейнер {container_name} возобновлен")
                    # Обновляем статус контейнера в таблице
                    self.updateTable(container_name, None, None, None, None)
                except docker.errors.NotFound:
                    self.logContainerAction(container_name, f"Контейнер {container_name} не найден")
                except Exception as e:
                    self.logContainerAction(container_name, f"Ошибка при возобновлении контейнера {container_name}: {e}")

    def startContainers(self):
        if not self.is_any_container_selected():
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите хотя бы один контейнер.")
            return

        non_stopped_containers = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status != 'exited':  # Проверяем, что контейнер остановлен
                        non_stopped_containers.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if non_stopped_containers:
            QMessageBox.warning(self, "Ошибка", "Невозможно запустить уже запущенные или приостановленные контейнеры: " + ", ".join(non_stopped_containers))
            return

        already_running = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    if container.status == 'running':
                        already_running.append(container_name)
                except docker.errors.NotFound:
                    QMessageBox.warning(self, "Ошибка", f"Контейнер {container_name} не найден.")
                    return

        if already_running:
            QMessageBox.warning(self, "Предупреждение", "Контейнер(ы) " + ", ".join(already_running) +
                                " уже запущены.")
            return

        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                container_name = self.table.item(row, 1).text()
                try:
                    container = self.client.containers.get(container_name)
                    container.start()
                    self.logContainerAction(container_name, f"Контейнер {container_name} запущен")
                    # Обновляем статус контейнера в таблице
                    self.updateTable(container_name, None, None, None, None)
                except docker.errors.NotFound:
                    self.logContainerAction(container_name, f"Контейнер {container_name} не найден")
                except Exception as e:
                    self.logContainerAction(container_name, f"Ошибка при запуске контейнера {container_name}: {e}")

    def translate_status(self, status):
        translations = {
            'created': 'Создан',
            'running': 'Запущен',
            'exited': 'Остановлен',
            'paused': 'Приостановлен',
            'restarting': 'Перезапускается',
            'removing': 'Удаляется',
            'dead': 'Поврежден'
        }
        return translations.get(status, status)

    def updateTable(self, name, type, ip, port, state):
        self.table.setSortingEnabled(False)  # Отключаем сортировку

        # Поиск строки с заданным именем контейнера
        row_to_update = None
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == name:
                row_to_update = row
                break

        if row_to_update is None:
            # Если контейнер новый, добавляем строку
            row_to_update = self.table.rowCount()
            self.table.insertRow(row_to_update)
            checkItem = QTableWidgetItem()
            checkItem.setCheckState(Qt.Unchecked)
            self.table.setItem(row_to_update, 0, checkItem)

        # Обновляем данные в строке, кроме статуса Docker
        data_values = [name, type, ip, port, state]
        for i in range(1, 6):  # Столбцы с 1 по 5
            if data_values[i-1] is not None:
                item = self.table.item(row_to_update, i)
                if item is None:
                    item = QTableWidgetItem()
                    self.table.setItem(row_to_update, i, item)
                item.setText(str(data_values[i-1]))
                item.setTextAlignment(Qt.AlignCenter)

        # Получаем и обновляем статус контейнера из Docker
        try:
            container = self.client.containers.get(name)
            status = container.status
            translated_status = self.translate_status(status)  # Переводим статус
        except docker.errors.NotFound:
            translated_status = "Не найден"
        except Exception as e:
            translated_status = f"Ошибка: {e}"

        status_item = self.table.item(row_to_update, 5)
        if status_item is None:
            status_item = QTableWidgetItem()
            self.table.setItem(row_to_update, 5, status_item)
        status_item.setText(translated_status)
        status_item.setTextAlignment(Qt.AlignCenter)

        if state is not None:
            state_item = self.table.item(row_to_update, 6)
            if state_item is None:
                state_item = QTableWidgetItem()
                self.table.setItem(row_to_update, 6, state_item)
            state_item.setText(state)
            state_item.setTextAlignment(Qt.AlignCenter)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)  # Включаем сортировку обратно

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Подтверждение',
                                     "Вы уверены, что хотите закрыть приложение?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Завершаем все активные потоки перед закрытием приложения
            for thread in self.threads:
                if thread.isRunning():
                    thread.terminate()
            event.accept()  # Закрыть приложение
        else:
            event.ignore()  # Отменить закрытие

    def onHeaderClicked(self, logicalIndex):
        # Проверяем, кликнули ли на заголовок первого столбца
        if logicalIndex == 0:
            self.toggleCheckboxes()

    def toggleCheckboxes(self):
        # Переключаем состояние всех чекбоксов
        current_state = self.table.item(0, 0).checkState()
        new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(new_state)

# Основная функция для запуска приложения
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = DockerApp()
    ex.show()
    sys.exit(app.exec_())
