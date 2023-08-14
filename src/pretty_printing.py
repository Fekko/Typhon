from typing import TypeVar
from scope import Variable
from automata import Function, Record, TypeVariable


def ReplaceFlowRecord(h : Record, name : str):
    for key in h.fields.keys():
        valName = "{}_{}".format(name, key)
        val = h.fields[key]
        tvarHead = TypeVariable(valName)
        if val.flows:
            val.heads.add(tvarHead)
            for f in val.flows:
                f.heads.add(tvarHead)

        for head in val.heads:
            if isinstance(head, Record):
                ReplaceFlowRecord(head, valName)
            elif isinstance(head, Function):
                ReplaceFlowFunction(head, valName)

def ReplaceFlowFunction(h : Function, name: str):
    for i in range(len(h.parameters)):
        argName: str = "{}_{}".format(name, i)
        p = h.parameters[i]
        tvarHead = TypeVariable(argName)
        p.heads.add(tvarHead)
        for f in p.flows:
            f.heads.add(tvarHead)
        
        for head in p.heads:
            if isinstance(head, Record):
                ReplaceFlowRecord(head, argName)
            elif isinstance(head, Function):
                ReplaceFlowFunction(head, argName)

def PrettyPrint(variables : list[Variable]):
    for var in variables:
        for h in var.state.heads:
            if type(h) == Function:
                ReplaceFlowFunction(h, "T")

    for v in variables:
        print(v)
    



 
