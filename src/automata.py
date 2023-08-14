from __future__ import annotations
from copy import deepcopy, copy

class Head:
    def  __repr__(self) -> str:
        return str(self)

    def IsSubtypeOf(self, other: Head):
        pass

class TypeVariable(Head):
    def __init__(self, paramName: str):
        self.paramName: str = paramName

    def __str__(self) -> str:
        return self.paramName
        
    def IsSubtypeOf(self, other: Head):
        assert(False)

class Function(Head):
    def __init__(self):
        self.parameters: list[State] = []
        self.result    : State

    def IsSubtypeOf(self, other: Head):
        if Function != type(other):
            return False
        return len(self.parameters) == len(other.parameters) #type: ignore

    def __deepcopy__(self, memo):
        copy = Function()
        memo[id(self)] = copy
        copy.parameters = deepcopy(self.parameters, memo)
        copy.result = deepcopy(self.result, memo)
        return copy

    def __str__(self) -> str:
        paramString = ",".join(map(str, self.parameters))
        return "({}->{})".format(paramString, self.result)

class Record(Head):
    def __init__(self):
        self.fields: dict[str, State] = {}
    
    def IsSubtypeOf(self, other: Head):
        if not isinstance(other, Record):
            return False
        return self.fields.keys() >= other.fields.keys() #type: ignore

    def __deepcopy__(self, memo):
        cls = self.__class__
        copy = cls.__new__(cls)
        memo[id(self)] = copy
        copy.fields = deepcopy(self.fields, memo)
        return copy

    def __str__(self) -> str:
        fieldsStrings = []
        for (key, value) in self.fields.items():
            fieldsStrings.append("{}:{}".format(key, value))
        return "rec[{}]".format(",".join(fieldsStrings))

class IterHead(Record):
    def __init__(self, polarity = True):
        super().__init__()
        self.fields["type"] = State(polarity)
        self.fields["type"].heads = {BaseType("iter")}
        self.fields["values"] = State(polarity)

    def __str__(self) -> str:
        return "{}[{}]".format(self.fields["type"], self.fields["values"])

class DictHead(IterHead):
    def __init__(self, polarity = True):
        super().__init__(polarity)
        self.fields["type"].heads = {BaseType("dict")}
        self.fields["keys"] = State(polarity)
        # Pop function
        popState: State = State(polarity)
        popHead = Function()
        popState.heads.add(popHead)
        popHead.result = self.fields["values"]
        self.fields["pop"] = popState
        # subscript function
        subState: State = State(polarity)
        subHead = Function()
        subState.heads.add(subHead)
        subHead.result = self.fields["values"]
        self.fields["[]"] = subState

    def __str__(self) -> str:
        return "{}[{},{}]".format(self.fields["type"], self.fields["keys"], self.fields["values"])

class ListHead(DictHead):
    def __init__(self, polarity = True):
        super().__init__(polarity)
        self.fields["type"].heads = {BaseType("list")}
        self.fields["keys"].heads = {BaseType("int")}

    def __str__(self) -> str:
        return "{}[{}]".format(self.fields["type"], self.fields["values"])


class SetHead(IterHead):
    def __init__(self, polarity = True):
        super().__init__(polarity)
        self.fields["type"].heads = {BaseType("set")}
        # Pop function
        popState: State = State(polarity)
        functionHead = Function()
        popState.heads.add(functionHead)
        functionHead.result = self.fields["values"]
        self.fields["pop"] = popState

class BaseType(Head):
    def __init__(self, name: str):
        self.name: str = name

    def __str__(self)->str:
        return self.name

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other) -> bool:
        return type(other) == type(self) and self.name == other.name

    def IsSubtypeOf(self, other: Head)->bool:
        if type(other) != BaseType:
            return False
        return BaseTypeHierarchy.IsSubtypeOf(self.name, other.name)

class BaseTypeHierarchy:
    supertypes: dict[str, set[str]] = {
        "none" : set(),
        "float": set(),
        "str"  : set(),
        "bool" : set(),
        "int"  : {"float"},
        "iter" : set(),
        "dict" : {"iter"},
        "list": {"dict"},
        "set" : {"iter"}
    }

    @staticmethod
    def IsSubtypeOf(sub: str, sup: str)->bool:
        if sub == sup:
            return True
        if sup in BaseTypeHierarchy.supertypes[sub]:
            return True
        for parent in BaseTypeHierarchy.supertypes[sub]:
            if BaseTypeHierarchy.IsSubtypeOf(parent, sup):
                return True
        return False

class State:
    def __init__(self, polarity : bool):
        self.polarity : bool = polarity
        self.flows    : set[State] = set()
        self.heads    : set[Head]  = set()
        self.IsParamState: bool = False
    
    def AddFlow(self, other : State):
        assert(self.polarity != other.polarity)
        self.flows.add(other) 
        other.flows.add(self)

    def AddAll(self, other: State):
        assert(other.polarity == self.polarity)
        for f in other.flows:
            self.AddFlow(f)
        self.heads.update(other.heads)

    def __deepcopy__(self, memo):
        copy = State(self.polarity)
        memo[id(self)] = copy
        copy.flows = deepcopy(self.flows, memo)
        copy.heads = deepcopy(self.heads, memo)
        return copy

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        #return "(id:{} p:{} heads{})".format(id(self), self.polarity, self.heads)
        return "|".join(map(str, self.heads))

cache : set[tuple[State, State]] = set()
def Biunify(pQ : State, nQ : State):
    assert(pQ.polarity)
    assert(not nQ.polarity)
    if (pQ, nQ) in cache:
        return
    cache.add((pQ, nQ))

    for pHead in pQ.heads:
        for nHead in nQ.heads:
            if not pHead.IsSubtypeOf(nHead):
                raise Exception("{} is not a subtype of {}".format(pHead, nHead))

    for pQ2 in nQ.flows:
        Merge(pQ2, pQ) 

    for nQ2 in pQ.flows:
        Merge(nQ2, nQ) 

    # Parameters
    for pHead in pQ.heads:
        if type(pHead) == Function:
            for nHead in nQ.heads:
                if type(nHead) == Function:
                    for (dn, dp) in zip(pHead.parameters, nHead.parameters):
                        Biunify(dp, dn)

    # Result
    for pHead in pQ.heads:
        if type(pHead) == Function:
            for nHead in nQ.heads:
                if type(nHead) == Function:
                        Biunify(pHead.result, nHead.result)

    # Fields
    for pHead in pQ.heads:
        if isinstance(pHead, Record):
            for nHead in nQ.heads:
                if isinstance(nHead, Record):
                    for key in nHead.fields.keys():
                        Biunify(pHead.fields[key], nHead.fields[key])

def Merge(q1: State, q2: State):
    assert(q1.polarity == q2.polarity)
    q1.flows.update(q2.flows)
    for h2 in q2.heads:
            q1.heads.add(copy(h2))

def Combine(q1 : State, q2 : State) -> State:
    assert(q1.polarity == q2.polarity)
    state = State(q1.polarity)
    for f in q1.flows | q2.flows:
        state.AddFlow(f)
    state.heads.update(q1.heads)
    state.heads.update(q2.heads)
    return state