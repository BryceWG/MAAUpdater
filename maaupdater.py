import os
import sys
import configparser
import urllib.request
import zipfile
import tempfile
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, 
                               QProgressBar, QLabel, QFileDialog, QCheckBox, QComboBox, 
                               QSystemTrayIcon, QMenu, QMessageBox)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QIcon, QAction

CONFIG_FILE = 'update_config.ini'

def load_config():
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return config.get('Settings', 'maa_directory', fallback=None)
    return None

def save_config(maa_directory):
    config = configparser.ConfigParser()
    config['Settings'] = {'maa_directory': maa_directory}
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)

class UpdateThread(QThread):
    update_progress = Signal(str, int, int)
    update_status = Signal(str)
    update_finished = Signal(bool, str)

    def __init__(self, maa_directory):
        super().__init__()
        self.maa_directory = maa_directory

    def run(self):
        download_url = "https://github.com/MaaAssistantArknights/MaaResource/archive/refs/heads/main.zip"
        try:
            self.download_and_extract(download_url, self.maa_directory)
            self.update_finished.emit(True, "更新完成！")
        except Exception as e:
            self.update_finished.emit(False, f"更新失败: {str(e)}")

    def download_and_extract(self, url, maa_path):
        with tempfile.TemporaryDirectory() as temp_dir:
            self.update_status.emit("正在下载...")
            temp_file_path = os.path.join(temp_dir, 'download.zip')
            
            def update_progress(count, block_size, total_size):
                if total_size > 0:
                    self.update_progress.emit("download", count * block_size, total_size)

            urllib.request.urlretrieve(url, temp_file_path, reporthook=update_progress)

            self.update_status.emit("正在解压...")
            with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            self.update_status.emit("正在更新文件...")
            self.total_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                  for dirpath, dirnames, filenames in os.walk(os.path.join(temp_dir, 'MaaResource-main'))
                                  for filename in filenames)
            self.copied_size = 0
            self.update_local_folders(temp_dir, maa_path)

    def update_local_folders(self, temp_dir, maa_path):
        for folder in ['resource', 'cache']:
            repo_folder = os.path.join(temp_dir, 'MaaResource-main', folder)
            local_folder = os.path.join(maa_path, folder)
            if os.path.exists(repo_folder):
                self.copy_folder(repo_folder, local_folder)

    def copy_folder(self, src, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                self.copy_folder(s, d)
            else:
                with open(s, 'rb') as f_src, open(d, 'wb') as f_dst:
                    f_dst.write(f_src.read())
                self.copied_size += os.path.getsize(s)
                self.update_progress.emit("copy", self.copied_size, self.total_size)

class UpdateApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAA资源更新器")
        self.setGeometry(100, 100, 400, 250)
        
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
        
        icon_path = os.path.join(application_path, 'maa.png')
        self.setWindowIcon(QIcon(icon_path))

        self.init_ui()
        self.load_settings()
        self.setup_auto_check()
        self.setup_tray()

        if not os.path.exists(CONFIG_FILE):
            self.first_time_setup()
        
        QTimer.singleShot(0, self.check_update)

    def init_ui(self):
        layout = QVBoxLayout()

        self.download_progress = QProgressBar()
        layout.addWidget(self.download_progress)

        self.copy_progress = QProgressBar()
        layout.addWidget(self.copy_progress)

        self.status_label = QLabel("准备更新...")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.check_update_button = QPushButton("检查更新")
        self.check_update_button.clicked.connect(self.check_update)
        layout.addWidget(self.check_update_button)

        self.start_button = QPushButton("开始更新")
        self.start_button.clicked.connect(self.start_update)
        layout.addWidget(self.start_button)

        self.autostart_checkbox = QCheckBox("开机自启动")
        self.autostart_checkbox.stateChanged.connect(self.toggle_autostart)
        layout.addWidget(self.autostart_checkbox)

        self.check_interval_combo = QComboBox()
        self.check_interval_combo.addItems(["不自动检查更新", "每小时检测更新", "每天检测更新", "每周检测更新"])
        self.check_interval_combo.currentIndexChanged.connect(self.set_check_interval)
        layout.addWidget(self.check_interval_combo)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def first_time_setup(self):
        QMessageBox.information(self, "首次启动", "欢迎使用MAA资源更新器！请选择MAA的安装路径。")
        maa_directory = QFileDialog.getExistingDirectory(self, "选择MAA安装路径")
        if not maa_directory:
            QMessageBox.critical(self, "错误", "未选择MAA安装路径，程序将退出。")
            sys.exit()
        save_config(maa_directory)

    def load_settings(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            autostart = config.getboolean('Settings', 'autostart', fallback=False)
            check_interval = config.get('Settings', 'check_interval', fallback="不自动检查")
            self.autostart_checkbox.setChecked(autostart)
            self.check_interval_combo.setCurrentText(check_interval)
        else:
            self.autostart_checkbox.setChecked(False)
            self.check_interval_combo.setCurrentText("不自动检查")

    def save_settings(self):
        config = configparser.ConfigParser()
        config['Settings'] = {
            'maa_directory': str(load_config() or ''),
            'autostart': str(self.autostart_checkbox.isChecked()),
            'check_interval': str(self.check_interval_combo.currentText())
        }
        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)

    def toggle_autostart(self, state):
        # 实现开机自启动的逻辑
        self.save_settings()

    def set_check_interval(self, index):
        self.save_settings()
        self.setup_auto_check()

    def setup_auto_check(self):
        if hasattr(self, 'auto_check_timer'):
            self.auto_check_timer.stop()

        interval = self.check_interval_combo.currentText()
        if interval == "每小时":
            self.auto_check_timer = QTimer(self)
            self.auto_check_timer.timeout.connect(self.check_update)
            self.auto_check_timer.start(3600000)  # 3600000 毫秒 = 1 小时
        elif interval == "每天":
            self.auto_check_timer = QTimer(self)
            self.auto_check_timer.timeout.connect(self.check_update)
            self.auto_check_timer.start(86400000)  # 86400000 毫秒 = 24 小时
        elif interval == "每周":
            self.auto_check_timer = QTimer(self)
            self.auto_check_timer.timeout.connect(self.check_update)
            self.auto_check_timer.start(604800000)  # 604800000 毫秒 = 7 天

    def check_update(self):
        self.status_label.setText("正在检查更新...")
        try:
            maa_directory = load_config()
            if maa_directory is None:
                self.status_label.setText("错误: 未设置MAA安装路径")
                return

            local_version_file = os.path.join(maa_directory, 'resource', 'version.json')
            remote_version_url = "https://raw.githubusercontent.com/MaaAssistantArknights/MaaResource/main/resource/version.json"

            if not os.path.exists(local_version_file):
                self.status_label.setText("本地版本文件不存在，需要更新")
                return

            local_file_size = os.path.getsize(local_version_file)

            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as temp_file:
                urllib.request.urlretrieve(remote_version_url, temp_file.name)
                remote_file_size = os.path.getsize(temp_file.name)

            if local_file_size != remote_file_size:
                self.status_label.setText("检测到新版本，可以更新")
            else:
                self.status_label.setText("已是最新版本")

        except Exception as e:
            self.status_label.setText(f"检查更新时出错: {str(e)}")

    def start_update(self):
        self.start_button.setEnabled(False)
        maa_directory = load_config()
        if maa_directory is None:
            maa_directory = QFileDialog.getExistingDirectory(self, "选择MAA安装路径")
            if not maa_directory:
                self.status_label.setText("错误: 未选择MAA安装路径，程序退出。")
                self.start_button.setEnabled(True)
                return
            save_config(maa_directory)

        self.update_thread = UpdateThread(maa_directory)
        self.update_thread.update_progress.connect(self.update_progress)
        self.update_thread.update_status.connect(self.update_status)
        self.update_thread.update_finished.connect(self.update_finished)
        self.update_thread.start()

    def update_progress(self, progress_type, current, total):
        progress = int((current / total) * 100)
        if progress_type == "download":
            self.download_progress.setValue(progress)
        elif progress_type == "copy":
            self.copy_progress.setValue(progress)

    def update_status(self, status):
        self.status_label.setText(status)

    def update_finished(self, success, message):
        self.status_label.setText(message)
        if success:
            self.download_progress.setValue(100)
            self.copy_progress.setValue(100)
            self.start_button.setText("完成")
            self.start_button.clicked.disconnect()
            self.start_button.clicked.connect(self.close)
        self.start_button.setEnabled(True)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon('maa.png'))
        
        tray_menu = QMenu()
        show_action = QAction("显示UI", self)
        quit_action = QAction("退出程序", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_app)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "MAA资源更新器",
            "程序已最小化到系统托盘，右键点击图标可以显示主界面或退出程序。",
            QSystemTrayIcon.Information,
            2000
        )

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpdateApp()
    window.show()
    sys.exit(app.exec())