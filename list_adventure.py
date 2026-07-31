import ast

with open("src/tuipet/ui/screens/adventurescreen.py", "r") as f:
    tree = ast.parse(f.read())

for node in tree.body:
    if isinstance(node, ast.ClassDef):
        print(f"Class {node.name}:")
        for subnode in node.body:
            if isinstance(subnode, ast.FunctionDef):
                print(f"  def {subnode.name}")
