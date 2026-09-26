import os
import subprocess

def run_python_file(working_directory, file_path, args=None):
    try:
        abs_working_dir = os.path.abspath(working_directory)
        target_path = os.path.normpath(os.path.join(abs_working_dir, file_path)) 

        if (os.path.commonpath([abs_working_dir, target_path])) != abs_working_dir:
            return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'

        if not os.path.isfile(target_path):
            return f'Error: "{file_path}" does not exist or is not a regular file'

        if not file_path.endswith(".py"):
            return f'Error: "{file_path}" is not a Python file'

        command = ["python", target_path]
        if args:
            command.extend(args)

        completed_process = subprocess.run(
            command,
            cwd = abs_working_dir,
            capture_output= True,
            text=True,
            timeout=30,
        )

        output_parts = []
        if completed_process.returncode != 0:
            output_parts.append(
                f"Process exited with code {completed_process.returncode}"
            )

        stdout_text = completed_process.stdout.strip()
        stderr_text = completed_process.stderr.strip()

        if not stdout_text and not stderr_text:
            output_parts.append("No output produced")
        else:
            if stdout_text:
                output_parts.append(f"STDOUT:\n{stdout_text}")
            if stderr_text:
                output_parts.append(f"STDERR:\n{stderr_text}")

        return "\n".join(output_parts)

    except Exception as e:
        return f"Error: executing Python file: {e}"