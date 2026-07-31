import os
import re

if __name__ == "__main__":
    tests_dir = "tests"
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                content = content.replace("import tuipet.data.loaders.data as data.loaders.data as data", "import tuipet.data.loaders.data as data")
                
                with open(path, "w") as f:
                    f.write(content)
    print("Fixed syntax error in tests/")
