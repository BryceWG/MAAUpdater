import os, configparser, urllib.request, zipfile, shutil, tempfile
from tkinter import messagebox, filedialog, Tk

CONFIG_FILE = 'update_config.ini'

def load_config():
    config = configparser.ConfigParser()
    return config.get('Settings', 'maa_directory', fallback=None) if os.path.exists(CONFIG_FILE) and config.read(CONFIG_FILE) else None

def save_config(maa_directory):
    config = configparser.ConfigParser()
    config['Settings'] = {'maa_directory': maa_directory}
    with open(CONFIG_FILE, 'w') as f: config.write(f)

def update(maa_directory):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, 'download.zip')
            urllib.request.urlretrieve("https://github.com/MaaAssistantArknights/MaaResource/archive/refs/heads/main.zip", zip_path)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            for folder in ['resource', 'cache']:
                src = os.path.join(temp_dir, 'MaaResource-main', folder)
                dst = os.path.join(maa_directory, folder)
                if os.path.exists(src): shutil.copytree(src, dst, dirs_exist_ok=True)
        return True, "更新完成！"
    except Exception as e:
        return False, f"更新失败: {str(e)}"

def main():
    root = Tk()
    root.withdraw()
    maa_directory = load_config()
    if not maa_directory:
        messagebox.showinfo("首次启动", "欢迎使用MAA资源更新器！请选择MAA的安装路径。")
        maa_directory = filedialog.askdirectory(title="选择MAA安装路径")
        if not maa_directory:
            messagebox.showerror("错误", "未选择MAA安装路径，程序将退出。")
            return
        save_config(maa_directory)
    success, message = update(maa_directory)
    messagebox.showinfo("更新完成", message) if success else messagebox.showerror("更新失败", message)

if __name__ == "__main__":
    main()