import ast
def get_func(fname, target_func):
    with open(fname) as f:
        src = f.read()
    tree = ast.parse(src)
    lines = src.splitlines()
    for n in tree.body:
        if getattr(n, "name", None) == target_func:
            return "\n".join(lines[n.lineno-1:n.end_lineno])
print(get_func("src/tuipet/ui/components/statusbox.py", "title"))
