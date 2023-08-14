from ast import expr, stmt, arg 

class ToolError(Exception):
    def __init__(self, node : expr | stmt | arg, message : str):
        self.node = node
        self.message = message

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        return "(Ln{} Col{}) {}".format(self.node.lineno, self.node.col_offset, self.message)
    
class TypeError(ToolError):
    def __init__(self, node: expr | stmt | arg, message: str):
        super().__init__(node, message)

class NotSupported(ToolError):
    def __init__(self, node: expr | stmt | arg, what: str):
        super().__init__(node, "Error no support {}".format(what))