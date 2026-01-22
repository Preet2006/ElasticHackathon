import tree_sitter_python
from tree_sitter import Parser, Language

p = Parser(Language(tree_sitter_python.language()))
tree = p.parse(b'from app.utils import db\nimport helper')

def show(n, depth=0):
    text = n.text[:40] if len(n.text) < 40 else n.text[:37] + b'...'
    print(' ' * depth, n.type, text)
    for c in n.children:
        show(c, depth + 2)

show(tree.root_node)
