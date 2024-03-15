import os
import os.path as path


def get_py_files(directory: str | None = None) -> list[str]:
  return [
    f for f in os.listdir(directory) if f.endswith(".py") and not f == "line_count.py"
  ]


def get_py_dirs(directory: str | None = None) -> list[str]:
  return [
    d
    for d in os.listdir(directory)
    if path.isdir(d) and not d.startswith(".") and not d.startswith("_")
  ]


line_count = 0


def recurse_dirs(dir: str | None = None):
  line_count = 0
  files = get_py_files(dir)
  for f in files:
    if dir:
      file_path = path.join(dir, f)
    else:
      file_path = f
    with open(file_path) as file:
      lines = len(file.readlines())
      print(f"File {file_path} has {lines} lines.")
      line_count += lines

  for d in get_py_dirs(dir):
    line_count += recurse_dirs(d)

  print(f"Dir {dir or '.'} has {line_count} lines")

  return line_count


print(f"Your Project has {recurse_dirs()} lines.")
