#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <shlobj.h>
#include <urlmon.h>
#include <direct.h>
#include <zip.h>

#define CONFIG_FILE "update_config.ini"
#define DOWNLOAD_URL "https://github.com/MaaAssistantArknights/MaaResource/archive/refs/heads/main.zip"
#define TEMP_ZIP_FILE "download.zip"

char maa_directory[MAX_PATH] = {0};

void load_config() {
    FILE* file = fopen(CONFIG_FILE, "r");
    if (file) {
        fgets(maa_directory, sizeof(maa_directory), file);
        maa_directory[strcspn(maa_directory, "\n")] = 0;
        fclose(file);
    }
}

void save_config() {
    FILE* file = fopen(CONFIG_FILE, "w");
    if (file) {
        fprintf(file, "%s", maa_directory);
        fclose(file);
    }
}

int select_directory() {
    BROWSEINFO bi = { 0 };
    bi.lpszTitle = "选择MAA安装路径";
    LPITEMIDLIST pidl = SHBrowseForFolder(&bi);
    if (pidl != 0) {
        SHGetPathFromIDList(pidl, maa_directory);
        IMalloc* imalloc = 0;
        if (SUCCEEDED(SHGetMalloc(&imalloc))) {
            imalloc->lpVtbl->Free(imalloc, pidl);
            imalloc->lpVtbl->Release(imalloc);
        }
        return 1;
    }
    return 0;
}

void copy_folder(const char* src, const char* dst) {
    char cmd[MAX_PATH * 2];
    snprintf(cmd, sizeof(cmd), "xcopy /E /I /Y \"%s\" \"%s\"", src, dst);
    system(cmd);
}

int update() {
    char temp_dir[MAX_PATH];
    GetTempPath(MAX_PATH, temp_dir);
    strcat(temp_dir, "maa_update\\");
    _mkdir(temp_dir);

    char zip_path[MAX_PATH];
    strcpy(zip_path, temp_dir);
    strcat(zip_path, TEMP_ZIP_FILE);

    if (S_OK != URLDownloadToFile(NULL, DOWNLOAD_URL, zip_path, 0, NULL)) {
        printf("下载失败\n");
        return 0;
    }

    int err = 0;
    zip_t* zip = zip_open(zip_path, 0, &err);
    if (zip == NULL) {
        printf("解压失败\n");
        return 0;
    }

    zip_extract(zip, temp_dir, 0, NULL, NULL);
    zip_close(zip);

    char src_path[MAX_PATH], dst_path[MAX_PATH];
    const char* folders[] = {"resource", "cache"};
    for (int i = 0; i < 2; i++) {
        snprintf(src_path, sizeof(src_path), "%sMaaResource-main\\%s", temp_dir, folders[i]);
        snprintf(dst_path, sizeof(dst_path), "%s\\%s", maa_directory, folders[i]);
        copy_folder(src_path, dst_path);
    }

    return 1;
}

int main() {
    load_config();
    if (strlen(maa_directory) == 0) {
        MessageBox(NULL, "欢迎使用MAA资源更新器！请选择MAA的安装路径。", "首次启动", MB_OK | MB_ICONINFORMATION);
        if (!select_directory()) {
            MessageBox(NULL, "未选择MAA安装路径，程序将退出。", "错误", MB_OK | MB_ICONERROR);
            return 1;
        }
        save_config();
    }

    if (update()) {
        MessageBox(NULL, "更新完成！", "更新完成", MB_OK | MB_ICONINFORMATION);
    } else {
        MessageBox(NULL, "更新失败", "更新失败", MB_OK | MB_ICONERROR);
    }

    return 0;
}