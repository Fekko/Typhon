from __future__ import annotations
from ast import stmt, expr, arg 
from automata import State

class Variable:
    def __init__(self, name : str, node : stmt | expr | arg, state : State):
        self.name    : str = name
        self.node    : stmt | expr | arg = node
        self.state   : State = state
        
    def __str__(self) -> str:
        return "(Ln{} Col{}) type({})={}".format(self.node.lineno, self.node.col_offset, self.name, self.state)

class Scope:
    def __init__(self):
        self.mapping : list[tuple[str, Variable]] = []

    def Add(self, name : str, var : Variable):
        self.mapping.append((name , var))

    def Get(self, name) -> Variable:
        for m in self.mapping[::-1]:
            if m[0] == name:
                return m[1]
        raise Exception("Name not bound in scope: " + name)

    def Contains(self, name):
        for m in self.mapping[::-1]:
            if m[0] == name:
                return True
        return False

    def GetBoundNames(self) -> set[str]:
        result : set[str] = set()
        for (name, var) in self.mapping:
            result.add(name)
        return result

    def __str__(self) -> str:
        result = ""
        for (name, var) in self.mapping:
            result += str(var) + "\n"
        return result

    @staticmethod
    def CombineScopes(scope1 : Scope, scope2 : Scope):
        combination = Scope()
        combination.mapping.extend(scope1.mapping)
        combination.mapping.extend(scope2.mapping)
        return combination