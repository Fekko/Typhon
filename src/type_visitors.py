import ast
from ast import Add, Attribute, AugAssign, Dict, Div, Eq, FloorDiv, Gt, GtE, Lt, LtE, Mod, Mult, Name, Assign, Constant, AST, FunctionDef, If, Module, Call, Not, NotEq, Pow, Return, For, Set, Slice, Sub, Subscript, UnaryOp, While, Compare, BoolOp, And, Or, BinOp, List
import builtins
from exceptions import NotSupported, ToolError, TypeError
from automata import IterHead, State, BaseType, Biunify, Combine, Function, SetHead, DictHead, ListHead, Record
from pretty_printing import PrettyPrint
from scope import Scope, Variable
from types import NoneType
from copy import deepcopy

class TypeVisitor(ast.NodeVisitor):
    # Settings
    skipPrintAndInput : bool = False 

    # static variables
    inFunction: bool = False
    returnState : State | None
    typedVariables : list[Variable] = []

    def __init__(self, upperScope : Scope):
        self.upperScope : Scope = upperScope

        self.scope : Scope = Scope()
        self.stack : list[State] = []
        self.returnVisited : bool = False
    
    def InferTypes(self, tree : AST):
        self.visit(tree)

    #### Helper functions ####

    def Load(self, name : str) -> State:
        if self.scope.Contains(name):
            return self.scope.Get(name).state
        return self.upperScope.Get(name).state

    def Store(self, name : str, variable : Variable):
        TypeVisitor.typedVariables.append(variable)
        self.scope.Add(name, variable)

    def CallFunction(self, function : State, arguments: list[State])->State:
        tmpFunction = State(False)
        pResult = State(True)
        nResult = State(False)
        pResult.AddFlow(nResult)
        head = Function()
        tmpFunction.heads.add(head)
        head.result = nResult
        head.parameters = arguments

        Biunify(function, tmpFunction)
        return pResult

    def HandleSpecialCalls(self, node: Call, arguments: list[State])->bool:
        if type(node.func) == Name:
            name = node.func.id
        elif type(node.func) == Attribute:
            name = node.func.attr
        else:
            return False
        
        result = State(True)
        match name:
            case "print":
                if TypeVisitor.skipPrintAndInput:
                    result.heads.add(BaseType("none"))
                    self.stack.append(result)
                    return True
            case "input":
                if TypeVisitor.skipPrintAndInput:
                    result.heads.add(BaseType("str"))
                    self.stack.append(result)
                    return True
            case "range":
                intState = State(False)
                intState.heads.add(BaseType("int"))
                for arg in arguments:
                    try:
                        Biunify(arg, intState)
                    except Exception as e:
                        raise TypeError(node, str(e))
                iterState: State = State(True)
                iterHead : IterHead = IterHead()
                iterState.heads.add(iterHead)
                iterHead.fields["values"].heads.add(BaseType("int"))
                self.stack.append(iterState)
                return True
            case "extend":
                self.VisitExtend(node.func, arguments) #type: ignore
                return True
            case "append":
                self.VisitAppend(node.func, arguments)  #type: ignore
                return True
            case "add":
                self.VisitAdd(node.func, arguments)  #type: ignore
                return True
            case "update":
                self.VisitUpdate(node.func, arguments)  #type: ignore
                return True
        return False

    def VisitAppend(self, node: Attribute, arguments: list[State]):
        if type(node.value) != Name:
            return

        self.visit(node.value)
        listState:State = self.stack.pop()
        toAddState = arguments[0]
        newListState: State = State(True)
        newListState.AddAll(listState)

        for h in newListState.heads:
            if type(h) == ListHead:
                h.fields["values"].AddAll(toAddState)
                self.Store(node.value.id, Variable(node.value.id, node.value, newListState)) #type: ignore
                return
        raise TypeError(node, "Can only append to a list.")

    def VisitAdd(self, node: Attribute, arguments: list[State]):
        if type(node.value) != Name:
            return

        self.visit(node.value)
        setState:State = self.stack.pop()
        toAddState = arguments[0]
        newSetState: State = State(True)
        newSetState.AddAll(setState)

        for h in newSetState.heads:
            if type(h) == SetHead:
                h.fields["values"].AddAll(toAddState)
                self.Store(node.value.id, Variable(node.value.id, node.value, newSetState)) #type: ignore
                return
        raise TypeError(node, "Can only add to a set.")

    def VisitUpdate(self, node: Attribute, arguments: list[State]):
        if type(node.value) != Name:
            return

        self.visit(node.value)
        dictState:State = self.stack.pop()
        newDictState: State = State(True)
        newDictState.AddAll(dictState)
        toMergeState = arguments[0]

        for h1 in newDictState.heads:
            if type(h1) == DictHead:
                for h2 in toMergeState.heads:
                    if type(h2) == DictHead:
                        h1.fields["values"].AddAll(h2.fields["values"])
                        h1.fields["keys"].AddAll(h2.fields["keys"])
                        self.Store(node.value.id, Variable(node.value.id, node.value, newDictState)) #type: ignore
                        return
        raise TypeError(node, "Can only update a dictionairy.")

    ### Visitors ###

    def visit(self, node: AST):
        if not self.returnVisited:
            return super().visit(node)

    def generic_visit(self, node: AST):
        if not self.returnVisited:
            return super().generic_visit(node)

    #### Statements ####

    def visit_Assign(self, node: Assign):
        self.visit(node.value)
        rhsState : State = self.stack.pop()
        for target in node.targets:
            self.Store(target.id, Variable(target.id, target, rhsState)) #type: ignore

    def visit_If(self, node: If):
        self.visit(node.test)
        conditionType = self.stack.pop()
        booleanType : State = State(False) 
        booleanType.heads.add(BaseType("bool"))

        try:
            Biunify(conditionType, booleanType)
        except Exception as e:
            raise TypeError(node, e.args[0])

        thenVisitor = ThenElseVisitor(Scope.CombineScopes(self.upperScope, self.scope))
        thenVisitor.InferTypes(Module(node.body))
        thenScope = thenVisitor.scope

        elseVisitor = ThenElseVisitor(Scope.CombineScopes(self.upperScope, self.scope))
        elseVisitor.InferTypes(Module(node.orelse))
        elseScope = elseVisitor.scope

        names : set[str] = thenVisitor.scope.GetBoundNames() | elseVisitor.scope.GetBoundNames()
        for name in names:
            variable : Variable
            inThen = thenScope.Contains(name)
            inElse = elseScope.Contains(name)
            if inThen and inElse:
                thenVar = thenScope.Get(name)
                elseVar = elseScope.Get(name)
                variable = Variable(name, thenVar.node, Combine(thenVar.state, elseVar.state))
            elif inThen:
                variable = thenScope.Get(name)
            else:
                variable = elseScope.Get(name)
            self.scope.Add(name, variable)
        
        self.returnVisited = thenVisitor.returnVisited and elseVisitor.returnVisited
            

    def visit_FunctionDef(self, node: FunctionDef):
        functionVisitor  = FunctionVisitor(Scope.CombineScopes(self.upperScope, self.scope))
        functionVariable = Variable(node.name, node, State(True))
        TypeVisitor.typedVariables.append(functionVariable)
        functionHead     = Function()
        functionVariable.state.heads.add(functionHead)
        for arg in node.args.args:
            pState = State(True)  # Positive
            nState = State(False) # Negative
            pState.AddFlow(nState)# Negative --> Positive
            pState.IsParamState = True

            param = Variable(arg.arg, arg, pState)
            functionVisitor.scope.Add(arg.arg, param)
            functionHead.parameters.append(nState)
        
        pState = State(True)  # Positive
        nState = State(False) # Negative
        pState.AddFlow(nState)# Negative --> Positive
        functionHead.result     = pState
        TypeVisitor.returnState = nState
        functionVisitor.InferTypes(Module(node.body))
        TypeVisitor.returnState = None

        self.scope.Add(node.name, functionVariable)

    def visit_Return(self, node: Return):
        if not TypeVisitor.inFunction:
            raise TypeError(node, "Can only use return statement in a function definition")

        state : State
        if node.value:
            self.visit(node.value)
            state = self.stack.pop()
        else:
            state : State = State(True)
            state.heads.add(BaseType("none"))
            state = state

        assert(TypeVisitor.returnState)
        try:
            Biunify(state, TypeVisitor.returnState)
        except Exception as e:
            raise TypeError(node, e.args[0])

        self.returnVisited : bool = True

    def visit_While(self, node: While):
        self.visit(node.test)
        conditionType = self.stack.pop()
        booleanType : State = State(False) 
        booleanType.heads.add(BaseType("bool"))

        try:
            Biunify(conditionType, booleanType)
        except Exception as e:
            raise TypeError(node, e.args[0])

        whileVisitor = WhileLoopVisitor(Scope.CombineScopes(self.upperScope, self.scope))
        whileVisitor.InferTypes(Module(node.body))
        whileScope: Scope = whileVisitor.scope

        for name in whileScope.GetBoundNames():
            whileVar = whileScope.Get(name)
            nodeMarked = whileVar.node
            if self.scope.Contains(name):
                prevVar = self.scope.Get(name)
                nodeMarked = prevVar.node
                prevVarState = prevVar.state
            else:
                prevVarState = State(True)
                prevVarState.heads.add(BaseType("none"))
            variable = Variable(name, nodeMarked, Combine(prevVarState, whileVar.state))
            self.scope.Add(name, variable)

    def visit_For(self, node: For):
        self.visit(node.iter)
        iterState: State = self.stack.pop()
        tempIterState: State = State(False)
        iterHead: IterHead = IterHead(False)
        tempIterState.heads.add(iterHead)
        pState = State(True)
        pState.AddFlow(iterHead.fields["values"])

        try:
            Biunify(iterState, tempIterState)
        except Exception as e:
            raise TypeError(node, e.args[0])

        forVisitor = ForLoopVisitor(Scope.CombineScopes(self.upperScope, self.scope))
        target: Name = node.target #type: ignore
        forVisitor.Store(target.id, Variable(target.id, target, pState))
        
        forVisitor.InferTypes(Module(node.body))
        forScope: Scope = forVisitor.scope

        for name in forScope.GetBoundNames():
            forVar = forScope.Get(name)
            nodeMarked = forVar.node
            if self.scope.Contains(name):
                prevVar = self.scope.Get(name)
                nodeMarked = prevVar.node
                prevVarState = prevVar.state
            else:
                prevVarState = State(True)
                prevVarState.heads.add(BaseType("none"))
            variable = Variable(name, nodeMarked, Combine(prevVarState, forVar.state))
            self.scope.Add(name, variable)

    def visit_AugAssign(self, node: AugAssign):
        self.visit(node.target)
        lhs : State =self.stack.pop()
        self.visit(node.value)
        rhs : State = self.stack.pop()
        self.visit(node.op)
        function: State = self.stack.pop()
        result: State = self.CallFunction(function, [lhs, rhs])
        target = node.target
        self.Store(target.id, Variable(target.id, target, result)) #type: ignore

    #### Expressions ####

    def visit_Name(self, node: Name):
        state : State = self.Load(node.id)
        self.stack.append(state)

    def visit_Constant(self, node: Constant):
        t = type(node.value)
        state = State(True)
        if   t == int:
            state.heads.add(BaseType("int"))
        elif t == float:
            state.heads.add(BaseType("float"))
        elif t == bool:
            state.heads.add(BaseType("bool"))
        elif t == str:
            state.heads.add(BaseType("str"))
        elif t == NoneType:
            state.heads.add(BaseType("none"))
        else:
            raise TypeError(node, "Cannot handle type {} of value {}".format(t.__name__, node.value))
        self.stack.append(state)

    def visit_Call(self, node: Call):
        arguments : list[State] = []
        for arg in node.args:
            self.visit(arg)
            arguments.append(self.stack.pop())

        if self.HandleSpecialCalls(node, arguments):
            return

        self.visit(node.func)
        function: State = deepcopy(self.stack.pop())

        try:
            result = self.CallFunction(function, arguments)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    def visit_Attribute(self, node: Attribute):
        self.visit(node.value)
        RecState: State = self.stack.pop()
        attribute: str = node.attr

        tmpRecState = State(False)
        recordHead = Record()
        tmpRecState.heads.add(recordHead)
        nState: State = State(False)
        pState: State = State(True)
        pState.AddFlow(nState)
        recordHead.fields[attribute] = nState
        try:
            Biunify(RecState, tmpRecState)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(pState)

    def visit_Compare(self, node: Compare):
        self.visit(node.ops[0])
        function = self.stack.pop()
        arguments : list[State] = []

        self.visit(node.left) # lhs
        arguments.append(self.stack.pop())
        self.visit(node.comparators[0]) # rhs
        arguments.append(self.stack.pop())

        try:
            result = self.CallFunction(function, arguments)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    def visit_BoolOp(self, node: BoolOp):
        self.visit(node.op)
        function = self.stack.pop()
        arguments : list[State] = []

        self.visit(node.values[0]) # lhs
        arguments.append(self.stack.pop())
        self.visit(node.values[1]) # rhs
        arguments.append(self.stack.pop())

        try:
            result = self.CallFunction(function, arguments)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    def visit_UnaryOp(self, node: UnaryOp):
        self.visit(node.op)
        function = self.stack.pop()
        self.visit(node.operand)
        arguments : list[State] = [self.stack.pop()]

        try:
            result = self.CallFunction(function, arguments)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    def visit_BinOp(self, node : BinOp):
        self.visit(node.op)
        function = self.stack.pop()
        arguments : list[State] = []

        self.visit(node.left) # lhs
        arguments.append(self.stack.pop())
        self.visit(node.right) # rhs
        arguments.append(self.stack.pop())

        try:
            result = self.CallFunction(function, arguments)
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    def visit_Set(self, node: Set):
        setState: State = State(True)
        setHead = SetHead()
        setState.heads.add(setHead)
        valueState = State(True)
        for e in node.elts:
            self.visit(e)
            valueState = Combine(valueState, self.stack.pop())
        setHead.fields["values"].AddAll(valueState)
        self.stack.append(setState)

    def visit_List(self, node: List):
        listState: State = State(True)
        listHead = ListHead()
        listState.heads.add(listHead)
        valueState = State(True)
        for e in node.elts:
            self.visit(e)
            valueState = Combine(valueState, self.stack.pop())
        listHead.fields["values"].AddAll(valueState)
        self.stack.append(listState)

    def visit_Dict(self, node: Dict):
        dictState: State = State(True)
        dictHead = DictHead()
        dictState.heads.add(dictHead)
        valueState = State(True)
        for e in node.values:
            self.visit(e)
            valueState = Combine(valueState, self.stack.pop())
        dictHead.fields["values"].AddAll(valueState)

        keyState = State(True)
        for e in node.keys:
            self.visit(e) #type: ignore
            keyState = Combine(keyState, self.stack.pop())
        dictHead.fields["keys"].AddAll(keyState)
        
        self.stack.append(dictState)

    def visit_Subscript(self, node: Subscript):
        self.visit(node.value)
        dictState: State = self.stack.pop()
        attribute: str = "[]"

        tmpDictState = State(False)
        dictHead = DictHead(False)
        tmpDictState.heads.add(dictHead)
        pState: State = State(True)
        dictHead.fields["[]"].AddFlow(pState)
        try:
            Biunify(dictState, tmpDictState)
        except Exception as e:
            raise TypeError(node, str(e))

        function = pState
        try:
            result = self.CallFunction(function, [])
        except Exception as e:
            raise TypeError(node, str(e))
        self.stack.append(result)

    ### Operations ###

    def visit_Eq(self, node: Eq):
        self.stack.append(self.Load("=="))

    def visit_NotEq(self, node: NotEq):
        self.stack.append(self.Load("!="))

    def visit_Lt(self, node: Lt):
        self.stack.append(self.Load("<"))

    def visit_LtE(self, node: LtE):
        self.stack.append(self.Load("<="))

    def visit_Gt(self, node: Gt):
        self.stack.append(self.Load(">"))

    def visit_GtE(self, node: GtE):
        self.stack.append(self.Load(">="))

    def visit_And(self, node: And):
        self.stack.append(self.Load("and"))

    def visit_Or(self, node: Or):
        self.stack.append(self.Load("or"))

    def visit_Not(self, node: Not):
        self.stack.append(self.Load("not"))

    def visit_Add(self, node : Add):
        self.stack.append(self.Load("+"))
    
    def visit_Sub(self, node : Sub):
        self.stack.append(self.Load("-"))

    def visit_Mult(self, node : Mult):
        self.stack.append(self.Load("*"))

    def visit_Div(self, node : Div):
        self.stack.append(self.Load("/"))

    def visit_Mod(self, node : Mod):
        self.stack.append(self.Load("%"))

    def visit_Pow(self, node : Pow):
        self.stack.append(self.Load("**"))

    def visit_FloorDiv(self, node : FloorDiv):
        self.stack.append(self.Load("//"))

    ### Not supported ###

    def visit_ClassDef(self, node):
        raise NotSupported(node, "Class")
    
    def visit_Delete(self, node):
        raise NotSupported(node, "Delete")
    
    def visit_AsyncFunctionDef(self, node):
        raise NotSupported(node, "Async Function")
    
    def visit_AsyncFor(self, node):
        raise NotSupported(node, "Async For")
    
    def visit_With(self, node):
        raise NotSupported(node, "With")
    
    def visit_AsyncWith(self, node):
        raise NotSupported(node, "Async With")
    
    def visit_Match(self, node):
        raise NotSupported(node, "Match")
    
    def visit_Raise(self, node):
        raise NotSupported(node, "Raise")
    
    def visit_Try(self, node):
        raise NotSupported(node, "Try")
    
    def visit_TryStar(self, node):
        raise NotSupported(node, "TryStar")
    
    def visit_Assert(self, node):
        raise NotSupported(node, "Assert")
    
    def visit_Lambda(self, node):
        raise NotSupported(node, "Lambda")
    
    def visit_IfExpr(self, node):
        raise NotSupported(node, "IfExpr")
    
    def visit_ListComp(self, node):
        raise NotSupported(node, "ListComp")
    
    def visit_SetComp(self, node):
        raise NotSupported(node, "SetComp")
    
    def visit_DictComp(self, node):
        raise NotSupported(node, "DictComp")
    
    def visit_GeneratorExpr(self, node):
        raise NotSupported(node, "GeneratorExpr")
    
    def visit_Await(self, node):
        raise NotSupported(node, "Await")
    
    def visit_Yield(self, node):
        raise NotSupported(node, "Yield")
    
    def visit_YieldFrom(self, node):
        raise NotSupported(node, "YieldFrom")
    
    def visit_FormattedValue(self, node):
        raise NotSupported(node, "FormattedValue")
    
    def visit_JoinedStr(self, node):
        raise NotSupported(node, "JoinedStr")
    
    def visit_Starred(self, node):
        raise NotSupported(node, "Starred")
    
    def visit_Tuple(self, node):
        raise NotSupported(node, "Tuple")

class FunctionVisitor(TypeVisitor):
    def __init__(self, upperScope: Scope):
        super().__init__(upperScope)

    def InferTypes(self, tree: AST):
        TypeVisitor.inFunction = True

        super().InferTypes(tree)
        if not self.returnVisited and TypeVisitor.returnState:
            state : State = State(True)
            state.heads.add(BaseType("none"))
            try:
                Biunify(state, TypeVisitor.returnState)
            except Exception as e:
                raise TypeError(tree, e.args[0]) #type: ignore
        
        TypeVisitor.inFunction = False

    def visit_FunctionDef(self, node: FunctionDef):
        raise TypeError(node, "Cannot define a function within a function definition")

class ThenElseVisitor(TypeVisitor):
    def __init__(self, upperScope: Scope):
        super().__init__(upperScope)

    def visit_FunctionDef(self, node: FunctionDef):
        raise TypeError(node, "Cannot define a function in an if then else")

class WhileLoopVisitor(TypeVisitor):
    def __init__(self, upperScope: Scope):
        super().__init__(upperScope)

    def visit_FunctionDef(self, node: FunctionDef):
        raise TypeError(node, "Cannot define a function in a while-loop")

class ForLoopVisitor(TypeVisitor):
    def __init__(self, upperScope: Scope):
        super().__init__(upperScope)

    def visit_FunctionDef(self, node: FunctionDef):
        raise TypeError(node, "Cannot define a function in a for-loop")
