import os

def concatenate_files(output_file, root_dir, target_files=None, exclude_dirs=None):
    """
    Concatenates specified Python files in the given directory recursively into a single file.

    :param output_file: Path to the output file where concatenated content will be written.
    :param root_dir: Root directory to start searching for files.
    :param target_files: List of target filenames to include.
    :param exclude_dirs: List of directories to exclude.
    """
    # Default list of target files if not provided
    if target_files is None:
        target_files = ['__init__.py', '__main__.py', 'server.py', 'Dockerfile', 'pyproject.toml']

    if exclude_dirs is None:
        exclude_dirs = ['__pycache__', '.git', '.venv', 'build', 'dist', '.idea', '.vscode']

    script_path = os.path.abspath(__file__)  # Get the absolute path of the current script

    with open(output_file, 'w', encoding='utf-8') as output:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Remove excluded directories from the traversal
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

            for filename in filenames:
                # Only process files that are in the target list
                if filename not in target_files:
                    continue

                file_path = os.path.join(dirpath, filename)

                # Skip the current script to prevent self-inclusion
                if os.path.abspath(file_path) == script_path or os.path.getsize(file_path) == 0:
                    continue

                output.write(f"# File: {file_path}\n")
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        output.write(content + '\n\n')
                except Exception as e:
                    output.write(f"# Error reading {file_path}: {e}\n\n")

if __name__ == "__main__":
    output_file = "concatenated_files.txt"
    root_dir = os.getcwd()  # Change this to the desired root directory if needed
    concatenate_files(output_file, root_dir)
    print(f"Selected files have been concatenated into {output_file}.")
