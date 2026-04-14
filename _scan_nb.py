import json
nb = json.load(open(r'c:\Users\zhelunStation\WorkBuddy\Claw\URSA\ExpertsRS\ExpertsRS_notebook.ipynb', 'r', encoding='utf-8'))
for i, c in enumerate(nb['cells']):
    src = c['source']
    if src:
        print(f"Cell {i}: {c['cell_type']} | {src[0][:100].strip()}")
    else:
        print(f"Cell {i}: {c['cell_type']} | [empty]")
