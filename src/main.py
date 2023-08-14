import ast
from pretty_printing import PrettyPrint
from type_visitors import TypeVisitor
from builtIns import builtInsScope
import sys
from scope import Scope

def Main(filename: str, debug: bool = True):
    with open(filename, 'r') as file:
        code = file.read()
    tree = ast.parse(code)

    errorMessage = ""
    visitor = TypeVisitor(builtInsScope)
    if not debug:
        try:
            visitor.InferTypes(tree)
        except Exception as e:
            errorMessage:str = str(e)
    else:
        visitor.InferTypes(tree)
    
    print("== AST =======================")
    print(ast.dump(tree, indent=2))
    print("== BuiltIns Types ============")
    PrettyPrint([x[1] for x in builtInsScope.mapping])
    print("== Input Program Types  ======")
    PrettyPrint(TypeVisitor.typedVariables)
    print(errorMessage)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise Exception("Requires arguments, use: main.py <filename>")
    Main(sys.argv[1], False)