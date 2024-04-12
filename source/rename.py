import os
import sys
import glob

def replace_in_file(file_path, cur_name, new_name):
    with open(file_path, 'r') as file:
        file_data = file.read()

    file_data = file_data.replace(cur_name, new_name)

    with open(file_path, 'w') as file:
        file.write(file_data)

def rename_files_in_directory(cur_name, new_name):
    for filename in os.listdir('.'):
        if cur_name in filename and not filename.endswith('.bat'):
            new_filename = filename.replace(cur_name, new_name)
            os.rename(filename, new_filename)

def main():
    cur_name = sys.argv[1]
    new_name = sys.argv[2]

    for extension in ['.cpp', '.cu', '.h', '.vcxproj', '.sln']:
        for filename in glob.glob(f'*{extension}'):
            replace_in_file(filename, cur_name, new_name)

    rename_files_in_directory(cur_name, new_name)

if __name__ == '__main__':
    main()