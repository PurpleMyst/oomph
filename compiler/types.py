from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Type:
    name: str
    refcounted: bool
    methods: Dict[str, FunctionType]
    members: List[Tuple[Type, str]]
    constructor_argtypes: Optional[List[Type]]
    source_generic: Optional["Generic"]

    def __init__(self, name: str, refcounted: bool):
        self.name = name
        self.refcounted = refcounted
        self.methods = {}
        self.members = []
        self.constructor_argtypes = None
        self.source_generic = None

    def __repr__(self) -> str:
        return f"<{type(self).__name__}: {self.name}>"

    def get_constructor_type(self) -> FunctionType:
        assert self.constructor_argtypes is not None
        return FunctionType(self.constructor_argtypes, self)


# does NOT inherit from type, Optional isn't a type even though Optional[str] is
@dataclass
class Generic:
    # TODO: make other generics than just Optional work too
    def get_type(self, generic_arg: Type) -> Type:
        result = Type(f"Optional[{generic_arg.name}]", False)
        result.constructor_argtypes = [generic_arg]
        result.methods["get"] = FunctionType([result], generic_arg)
        result.source_generic = self
        return result


@dataclass
class FunctionType(Type):
    argtypes: List[Type]
    returntype: Optional[Type]

    def __init__(self, argtypes: List[Type], returntype: Optional[Type]):
        super().__init__("<function>", False)
        self.argtypes = argtypes
        self.returntype = returntype


INT = Type("int", False)
BOOL = Type("bool", False)
FLOAT = Type("float", False)
STRING = Type("Str", True)

BOOL.methods["to_string"] = FunctionType([BOOL], STRING)

FLOAT.methods["ceil"] = FunctionType([FLOAT], INT)
FLOAT.methods["floor"] = FunctionType([FLOAT], INT)
FLOAT.methods["round"] = FunctionType([FLOAT], INT)
FLOAT.methods["to_string"] = FunctionType([FLOAT], STRING)
FLOAT.methods["truncate"] = FunctionType([FLOAT], INT)

INT.methods["to_string"] = FunctionType([INT], STRING)

STRING.methods["center_pad"] = FunctionType([STRING, INT, STRING], STRING)
STRING.methods["count"] = FunctionType([STRING, STRING], INT)
STRING.methods["ends_with"] = FunctionType([STRING, STRING], BOOL)
STRING.methods["find_first"] = FunctionType([STRING, STRING], INT)
STRING.methods["left_pad"] = FunctionType([STRING, INT, STRING], STRING)
STRING.methods["left_trim"] = FunctionType([STRING], STRING)
STRING.methods["length"] = FunctionType([STRING], INT)
STRING.methods["repeat"] = FunctionType([STRING, INT], STRING)
STRING.methods["replace"] = FunctionType([STRING, STRING, STRING], STRING)
STRING.methods["right_pad"] = FunctionType([STRING, INT, STRING], STRING)
STRING.methods["right_trim"] = FunctionType([STRING], STRING)
STRING.methods["slice"] = FunctionType([STRING, INT, INT], STRING)
STRING.methods["starts_with"] = FunctionType([STRING, STRING], BOOL)
STRING.methods["to_float"] = FunctionType([STRING], FLOAT)
STRING.methods["to_int"] = FunctionType([STRING], INT)
STRING.methods["trim"] = FunctionType([STRING], STRING)
STRING.methods["unicode_length"] = FunctionType([STRING], INT)

builtin_types = {typ.name: typ for typ in [INT, FLOAT, BOOL, STRING]}
builtin_generic_types = {"Optional": Generic()}
builtin_variables: Dict[str, Type] = {
    "print": FunctionType([STRING], None),
}
