import ast
import os

with open("src/tuipet/core/shop.py", "r") as f:
    tree = ast.parse(f.read())

funcs = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        funcs.append(node.name)
print("ALL FUNCS:", funcs)
