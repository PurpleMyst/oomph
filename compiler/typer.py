import itertools
from typing import Dict, List, Tuple, Union

from compiler import typed_ast as tast
from compiler import untyped_ast as uast
from compiler.types import BOOL, FLOAT, INT, STRING, ClassType, FunctionType, Type

_ref_names = (f"ref{n}" for n in itertools.count())


class _FunctionOrMethodTyper:
    def __init__(self, variables: Dict[str, Type], types: Dict[str, Type]):
        self.variables = variables
        self.types = types
        self.reflist: List[Tuple[str, Type]] = []
        self.loop_stack: List[str] = []
        self.loop_counter = 0

    def do_call(
        self, ast: uast.Call
    ) -> Union[tast.VoidCall, tast.ReturningCall, tast.SetRef]:
        func = self.do_expression(ast.func)
        assert isinstance(func.type, FunctionType)
        args = [self.do_expression(arg) for arg in ast.args]
        assert len(args) == len(func.type.argtypes)
        for arg, argtype in zip(args, func.type.argtypes):
            assert arg.type == argtype, (arg.type, argtype)

        if func.type.returntype is None:
            return tast.VoidCall(func, args)

        result = tast.ReturningCall(func.type.returntype, func, args)
        if result.type.refcounted:  # TODO: what else needs ref holding?
            refname = next(_ref_names)
            self.reflist.append((refname, result.type))
            return tast.SetRef(result.type, refname, result)
        return result

    def do_binary_op(self, ast: uast.BinaryOperator) -> tast.Expression:
        if ast.op == "!=":
            return tast.BoolNot(
                self.do_binary_op(uast.BinaryOperator(ast.lhs, "==", ast.rhs))
            )

        lhs = self.do_expression(ast.lhs)
        rhs = self.do_expression(ast.rhs)

        if lhs.type is INT and ast.op == "+" and rhs.type is INT:
            return tast.NumberAdd(INT, lhs, rhs)
        if lhs.type is INT and ast.op == "-" and rhs.type is INT:
            return tast.NumberSub(INT, lhs, rhs)
        if lhs.type is INT and ast.op == "*" and rhs.type is INT:
            return tast.NumberMul(INT, lhs, rhs)

        if lhs.type is INT and ast.op == "/" and rhs.type is INT:
            lhs = tast.IntToFloat(lhs)
            rhs = tast.IntToFloat(rhs)
        if lhs.type is INT and rhs.type is FLOAT:
            lhs = tast.IntToFloat(lhs)
        if lhs.type is FLOAT and rhs.type is INT:
            rhs = tast.IntToFloat(rhs)

        if lhs.type is FLOAT and ast.op == "+" and rhs.type is FLOAT:
            return tast.NumberAdd(FLOAT, lhs, rhs)
        if lhs.type is FLOAT and ast.op == "-" and rhs.type is FLOAT:
            return tast.NumberSub(FLOAT, lhs, rhs)
        if lhs.type is FLOAT and ast.op == "*" and rhs.type is FLOAT:
            return tast.NumberMul(FLOAT, lhs, rhs)
        if lhs.type is FLOAT and ast.op == "/" and rhs.type is FLOAT:
            return tast.FloatDiv(lhs, rhs)

        if lhs.type is BOOL and ast.op == "and" and rhs.type is BOOL:
            return tast.BoolAnd(lhs, rhs)
        if lhs.type is BOOL and ast.op == "or" and rhs.type is BOOL:
            return tast.BoolOr(lhs, rhs)

        if lhs.type is BOOL and ast.op == "==" and rhs.type is BOOL:
            return tast.BoolOr(
                tast.BoolAnd(lhs, rhs),
                tast.BoolAnd(tast.BoolNot(lhs), tast.BoolNot(rhs)),
            )
        if lhs.type is INT and ast.op == "==" and rhs.type is INT:
            return tast.NumberEqual(lhs, rhs)
        if lhs.type is FLOAT and ast.op == "==" and rhs.type is FLOAT:
            # Float equality sucks, but maybe it can be useful for something
            return tast.NumberEqual(lhs, rhs)

        raise NotImplementedError(f"{lhs.type} {ast.op} {rhs.type}")

    def do_expression(self, ast: uast.Expression) -> tast.Expression:
        if isinstance(ast, uast.StringConstant):
            return tast.StringConstant(STRING, ast.value)
        if isinstance(ast, uast.IntConstant):
            assert -(2 ** 63) <= ast.value < 2 ** 63
            return tast.IntConstant(ast.value)
        if isinstance(ast, uast.FloatConstant):
            return tast.FloatConstant(ast.value)
        if isinstance(ast, uast.Call):
            call = self.do_call(ast)
            assert not isinstance(call, tast.VoidCall)
            return call
        if isinstance(ast, uast.GetVar):
            if ast.varname == "true":
                return tast.BoolConstant(True)
            if ast.varname == "false":
                return tast.BoolConstant(False)
            return tast.GetVar(self.variables[ast.varname], ast.varname)
        if isinstance(ast, uast.UnaryOperator):
            obj = self.do_expression(ast.obj)
            if obj.type is BOOL and ast.op == "not":
                return tast.BoolNot(obj)
            if obj.type in [INT, FLOAT] and ast.op == "-":
                return tast.NumberNegation(obj.type, obj)
            raise NotImplementedError(f"{ast.op} {obj.type}")
        if isinstance(ast, uast.BinaryOperator):
            return self.do_binary_op(ast)
        if isinstance(ast, uast.Constructor):
            klass = self.types[ast.type]
            assert isinstance(klass, ClassType)
            return tast.Constructor(klass.get_constructor_type(), klass)
        if isinstance(ast, uast.GetAttribute):
            obj = self.do_expression(ast.obj)
            try:
                return tast.GetMethod(obj, ast.attribute)
            except KeyError:
                return tast.GetAttribute(obj, ast.attribute)
        raise NotImplementedError(ast)

    def do_statement(self, ast: uast.Statement) -> List[tast.Statement]:
        if isinstance(ast, uast.Call):
            result = self.do_call(ast)
            if isinstance(result, tast.SetRef):
                return [tast.DecRef(result.value)]
            return [result]

        if isinstance(ast, uast.Let):
            assert ast.varname not in self.variables, (ast.varname, self.variables)
            value = self.do_expression(ast.value)
            self.variables[ast.varname] = value.type
            return [tast.CreateLocalVar(ast.varname, value)]

        if isinstance(ast, uast.Assign):
            # TODO: this assumes local variable without assert
            vartype = self.variables[ast.varname]
            value = self.do_expression(ast.value)
            assert value.type is vartype
            return [tast.SetLocalVar(ast.varname, value)]

        if isinstance(ast, uast.Pass):
            return []

        if isinstance(ast, uast.Continue):
            return [tast.Continue(self.loop_stack[-1])]

        if isinstance(ast, uast.Break):
            return [tast.Break(self.loop_stack[-1])]

        if isinstance(ast, uast.Return):
            if ast.value is None:
                return [tast.Return(None)]
            return [tast.Return(self.do_expression(ast.value))]

        if isinstance(ast, uast.If):
            untyped_condition, untyped_body = ast.ifs_and_elifs[0]
            condition = self.do_expression(untyped_condition)
            assert condition.type is BOOL
            body = self.do_block(untyped_body)

            if len(ast.ifs_and_elifs) >= 2:
                otherwise = self.do_statement(
                    uast.If(ast.ifs_and_elifs[1:], ast.else_block)
                )
            else:
                otherwise = self.do_block(ast.else_block)
            return [tast.If(condition, body, otherwise)]

        if isinstance(ast, uast.Loop):
            init = [] if ast.init is None else self.do_statement(ast.init)
            cond = (
                tast.BoolConstant(True)
                if ast.cond is None
                else self.do_expression(ast.cond)
            )
            incr = [] if ast.incr is None else self.do_statement(ast.incr)

            loop_id = f"loop{self.loop_counter}"
            self.loop_counter += 1

            self.loop_stack.append(loop_id)
            body = self.do_block(ast.body)
            popped = self.loop_stack.pop()
            assert popped == loop_id

            return [tast.Loop(loop_id, init, cond, incr, body)]

        raise NotImplementedError(ast)

    def do_block(self, block: List[uast.Statement]) -> List[tast.Statement]:
        result = []
        for statement in block:
            result.extend(self.do_statement(statement))
        return result


def _do_funcdef(
    variables: Dict[str, Type],
    types: Dict[str, Type],
    funcdef: uast.FuncDef,
    create_variable: bool,
) -> tast.FuncDef:
    functype = FunctionType(
        [types[typename] for typename, argname in funcdef.args],
        None if funcdef.returntype is None else types[funcdef.returntype],
    )
    if create_variable:
        assert funcdef.name not in variables
        variables[funcdef.name] = functype

    local_vars = variables.copy()
    for (typename, argname), the_type in zip(funcdef.args, functype.argtypes):
        assert argname not in local_vars
        local_vars[argname] = the_type

    typer = _FunctionOrMethodTyper(local_vars, types)
    body = typer.do_block(funcdef.body)
    return tast.FuncDef(
        funcdef.name,
        functype,
        [argname for typename, argname in funcdef.args],
        body,
        typer.reflist,
    )


def _do_toplevel_statement(
    variables: Dict[str, Type],
    types: Dict[str, Type],
    top_statement: uast.ToplevelStatement,
) -> tast.ToplevelStatement:
    if isinstance(top_statement, uast.FuncDef):
        return _do_funcdef(variables, types, top_statement, create_variable=True)

    if isinstance(top_statement, uast.ClassDef):
        classtype = ClassType(top_statement.name, True, {}, [])
        assert top_statement.name not in types
        types[top_statement.name] = classtype
        classtype.members.extend(
            (types[typename], membername)
            for typename, membername in top_statement.members
        )

        typed_method_defs = []
        for method_def in top_statement.body:
            method_def.args.insert(0, (top_statement.name, "self"))
            typed_def = _do_funcdef(variables, types, method_def, create_variable=False)
            classtype.methods[method_def.name] = typed_def.type
            typed_method_defs.append(typed_def)

        return tast.ClassDef(classtype, typed_method_defs)

    raise NotImplementedError(top_statement)


def convert_program(
    program: List[uast.ToplevelStatement],
) -> List[tast.ToplevelStatement]:
    types: Dict[str, Type] = {"int": INT}
    variables: Dict[str, Type] = {
        "print": FunctionType([STRING], None),
        "print_int": FunctionType([INT], None),
        "print_bool": FunctionType([BOOL], None),
        "print_float": FunctionType([FLOAT], None),
    }
    return [
        _do_toplevel_statement(variables, types, toplevel_statement)
        for toplevel_statement in program
    ]
