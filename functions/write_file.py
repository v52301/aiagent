import os

def write_file(working_directory, file_path, content):
    try:
        norm_working_dir = os.path.abspath(os.path.normpath(working_directory))
        target_path = os.path.abspath(os.path.normpath(os.path.join(working_directory, file_path)))
        
        if os.path.commonpath([norm_working_dir, target_path]) != norm_working_dir:
            return f'Error: Cannot write to "{file_path}" as it is outside the permitted working directory'

        if os.path.isdir(target_path):
            return f'Error: Cannot write to "{file_path}" as it is a directory'

        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f'Successfully wrote to "{file_path}" ({len(content)} characters written)'

    except Exception as e:
        return f"Error: {e}"
    