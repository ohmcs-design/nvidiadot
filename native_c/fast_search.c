/**
 * DOT AI Native C Core - Fast Codebase Grep & Search CLI
 * Compiled with GCC into fast_search.exe
 * Can be called seamlessly from Python subprocess or as a standalone CLI tool.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

#define MAX_PATH_LEN 1024
#define MAX_LINE_LEN 2048

static const char* IGNORED_DIRS[] = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", 
    ".idea", ".vscode", "build", "dist", "target", NULL
};

static int should_ignore(const char* name) {
    for (int i = 0; IGNORED_DIRS[i] != NULL; i++) {
        if (_stricmp(name, IGNORED_DIRS[i]) == 0) return 1;
    }
    return 0;
}

static void search_file(const char* filepath, const char* query, int* match_count) {
    FILE* f = fopen(filepath, "r");
    if (!f) return;

    char line[MAX_LINE_LEN];
    int line_num = 1;

    while (fgets(line, sizeof(line), f)) {
        if (strstr(line, query)) {
            line[strcspn(line, "\r\n")] = 0;
            printf("%s:%d:%s\n", filepath, line_num, line);
            (*match_count)++;
            if (*match_count >= 200) break;
        }
        line_num++;
    }
    fclose(f);
}

static void traverse_directory(const char* dir_path, const char* query, int* match_count) {
    char search_pattern[MAX_PATH_LEN];
    snprintf(search_pattern, sizeof(search_pattern), "%s\\*", dir_path);

    WIN32_FIND_DATAA find_data;
    HANDLE hFind = FindFirstFileA(search_pattern, &find_data);
    if (hFind == INVALID_HANDLE_VALUE) return;

    do {
        if (strcmp(find_data.cFileName, ".") == 0 || strcmp(find_data.cFileName, "..") == 0) {
            continue;
        }

        char full_path[MAX_PATH_LEN];
        snprintf(full_path, sizeof(full_path), "%s\\%s", dir_path, find_data.cFileName);

        if (find_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (!should_ignore(find_data.cFileName)) {
                traverse_directory(full_path, query, match_count);
            }
        } else {
            search_file(full_path, query, match_count);
        }

        if (*match_count >= 200) break;
    } while (FindNextFileA(hFind, &find_data));

    FindClose(hFind);
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: fast_search <root_dir> <query>\n");
        return 1;
    }

    const char* root_dir = argv[1];
    const char* query = argv[2];
    int match_count = 0;

    traverse_directory(root_dir, query, &match_count);
    return 0;
}
