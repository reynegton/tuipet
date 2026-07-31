with open("src/tuipet/core/petcare.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.startswith("    return ") and lines[i-1].startswith("    def "):
        lines[i] = "    " + line

with open("src/tuipet/core/petcare.py", "w") as f:
    f.writelines(lines)
