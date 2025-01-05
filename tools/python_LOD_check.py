import os

def count_lines_of_code(directory, extensions, exclude_dirs=None):
    """
    Recursively counts lines of code in files with the specified extensions, 
    while ignoring blank lines and comments, and excluding certain directories.

    :param directory: The root directory to start counting lines of code.
    :param extensions: A list of file extensions to filter (e.g., [".py", ".html"]).
    :param exclude_dirs: A list of directories to exclude (e.g., ["node_modules", "venv"]).
    :return: A dictionary with LOC, file count, and total file size for each extension, and totals.
    """
    results = {ext: {"loc": 0, "files": 0, "size": 0} for ext in extensions}
    results["total"] = {"loc": 0, "files": 0, "size": 0}

    for root, dirs, files in os.walk(directory):
        # Exclude unwanted directories
        dirs[:] = [d for d in dirs if d not in (exclude_dirs or [])]

        for file in files:
            file_ext = os.path.splitext(file)[-1]
            if file_ext in extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                        # Filter out blank lines and comments
                        filtered_lines = [
                            line for line in lines 
                            if line.strip() 
                            and not line.strip().startswith(("#", "//", "/*", "*", "*/"))
                        ]

                        # Count lines and file size
                        line_count = len(filtered_lines)
                        file_size = os.path.getsize(file_path)

                        # Update results
                        results[file_ext]["loc"] += line_count
                        results[file_ext]["files"] += 1
                        results[file_ext]["size"] += file_size
                        results["total"]["loc"] += line_count
                        results["total"]["files"] += 1
                        results["total"]["size"] += file_size

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

    return results


# Example usage
directory_to_check = "./Backend"  # Replace with your target directory
file_extensions = [".py", ".html", ".css", ".js"]  # File types to analyze
excluded_directories = ["node_modules", "venv", ".git"]  # Directories to exclude

result = count_lines_of_code(directory_to_check, file_extensions, excluded_directories)

# Display results
for ext, data in result.items():
    if ext == "total":
        print("\nOverall Total:")
    else:
        print(f"\nFile Type: {ext.upper()}")
    print(f"  Total Lines of Code: {data['loc']}")
    print(f"  Total Files: {data['files']}")
    print(f"  Total File Size: {data['size']} bytes")

