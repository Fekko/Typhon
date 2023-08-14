from scope import Scope, Variable
from automata import DictHead, Head, IterHead, ListHead, SetHead, State, Function, BaseType, BaseType
from ast import stmt

def F(args : list[State] = [], argLink : list[int] = [], returnHeads : set[Head] = set())->State:
    functionState: State = State(True)
    functionHead: Function = Function()
    functionState.heads.add(functionHead)
    for arg in args:
        arg.polarity = False
    functionHead.parameters = args
    functionHead.result = State(True)
    functionHead.result.heads.update(returnHeads)
    for i in argLink:
        args[i].AddFlow(functionHead.result)
    return functionState

def S(heads: set[BaseType] = set())->State:
    state: State = State(True)
    state.heads.update(heads)
    return state

def H(typeName: str)->BaseType:
    return BaseType(typeName)

dummyNode = stmt()
dummyNode.lineno = 0
dummyNode.col_offset = 0
builtInsScope: Scope = Scope()
def BuiltIn(name : str, state: State):
    builtInsScope.Add(name, Variable(name, dummyNode, state))

### Built in functions and variables: ###
BuiltIn("print", F([S()], [], {H("none")}))
BuiltIn("input", F([S({H("str")})], [], {H("str")}))
BuiltIn("+", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("-", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("*", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("/", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("%", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("**", F([S({H("float")}), S({H("float")})], [], {H("float")}))
BuiltIn("//", F([S({H("float")}), S({H("float")})], [], {H("int")}))
BuiltIn("not", F([S({H("bool")})], [], {H("bool")}))
BuiltIn("and", F([S({H("bool")}), S({H("bool")})], [], {H("bool")}))
BuiltIn("or", F([S({H("bool")}), S({H("bool")})], [], {H("bool")}))
s = S()
BuiltIn("==", F([S(), S()], [], {H("bool")}))
s = S()
BuiltIn("!=", F([S(), S()], [], {H("bool")}))
BuiltIn("<", F([S({H("float")}), S({H("float")})], [], {H("bool")}))
BuiltIn("<=", F([S({H("float")}), S({H("float")})], [], {H("bool")}))
BuiltIn(">", F([S({H("float")}), S({H("float")})], [], {H("bool")}))
BuiltIn(">=", F([S({H("float")}), S({H("float")})], [], {H("bool")}))
s = S()
BuiltIn("int", F([s], [], {H("int")}))
s = S()
BuiltIn("str", F([s], [], {H("str")}))
s = S()
BuiltIn("float", F([s], [], {H("float")}))
h = ListHead(True)
BuiltIn("list", F([], [], {h}))
h = DictHead(False)
BuiltIn("dict", F([], [], {h}))
h = SetHead(False)
BuiltIn("set", F([], [], {h}))
s = S()
BuiltIn("bool", F([s], [], {H("bool")}))
BuiltIn("chr", F([S({H("int")})], [], {H("str")}))
BuiltIn("ord", F([S({H("string")})], [], {H("int")}))
BuiltIn("randint", F([S({H("int")}), S({H("int")})], [], {H("int")}))

s = S()
h = IterHead(False)
s.heads.add(h)
BuiltIn("len", F([s], [], {H("int")}))



