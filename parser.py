from scanner import *

class Node:
    def __init__(self, ntype, value=None, children=None, lineno=None):
        self.type = ntype
        self.value = value
        self.children = children if children is not None else []
        self.lineno = lineno

    def add(self, node):
        self.children.append(node)

    def pretty(self, indent=0):
        pad = "  " * indent
        val = f": {self.value}" if self.value is not None else ""
        lineinfo = f" (line {self.lineno})" if self.lineno else ""
        out = f"{pad}{self.type}{val}{lineinfo}\n"
        for c in self.children:
            out += c.pretty(indent + 1)
        return out


class ParserState:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.errors = []

    def current(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def peek(self, offset=1):
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def advance(self):
        tok = self.current()
        self.i += 1
        return tok

    def match(self, ttype=None, value=None):
        cur = self.current()
        return (ttype is None or cur["type"] == ttype) and (value is None or cur["value"] == value)

    def expect(self, expected_pairs, msg=None):
        cur = self.current()
        for (t, v) in expected_pairs:
            if cur["type"] == t and (v is None or cur["value"] == v):
                return self.advance()
        self.error(msg or f"Expected {expected_pairs}, got {cur['type']}({cur['value']})", cur["lineno"])
        return None

    def error(self, msg, lineno=None):
        ln = lineno if lineno is not None else (self.current()["lineno"] if self.current() else -1)
        self.errors.append((ln, msg))


def parse(tokens):
    state = ParserState(tokens)
    root = Node("Program", lineno=1)
    try:
        for s in parse_statement_list(state, stop_on=(TOKEN_EOF,)):
            if s:
                root.add(s)
    except Exception as e:
        state.error(f"Internal parser error: {e}", state.current().get("lineno", -1))
    return root, state.errors


def parse_statement_list(state, stop_on=(TOKEN_EOF, TOKEN_DEDENT)):
    stmts = []
    while state.match(TOKEN_NEWLINE):
        state.advance()
    while not (state.match(TOKEN_EOF) or state.match(TOKEN_DEDENT) or state.current()["type"] in stop_on):
        st = parse_statement(state)
        if st:
            stmts.append(st)
        while state.match(TOKEN_NEWLINE):
            state.advance()
        if state.match(TOKEN_EOF):
            break
    return stmts


# Keyword statement parsers
KEYWORD_PARSERS = {
    "summon": lambda s: parse_import(s),
    "spot": lambda s: parse_if(s),
    "replay": lambda s: parse_while(s),
    "farm": lambda s: parse_for(s),
    "quest": lambda s: parse_function_def(s),
    "guild": lambda s: parse_class_def(s),
    "attack": lambda s: parse_output_stmt(s),
    "scout": lambda s: parse_input_stmt(s),
    "embark": lambda s: parse_try_except(s),
    "reward": lambda s: parse_return(s),
    "skipEncounter": lambda s: (lambda tok: Node("Continue", None, [], tok["lineno"]))(s.advance()),
    "escapeDungeon": lambda s: (lambda tok: Node("Break", None, [], tok["lineno"]))(s.advance()),
}

def parse_statement(state):
    cur = state.current()
    
    if cur["type"] == TOKEN_COMMENT:
        tok = state.advance()
        return Node("Comment", tok["value"], [], tok["lineno"])

    if cur["type"] == TOKEN_KEYWORD:
        parser = KEYWORD_PARSERS.get(cur["value"])
        if parser:
            return parser(state)
        tok = state.advance()
        return Node("KeywordStmt", tok["value"], [], tok["lineno"])

    if cur["type"] == TOKEN_IDENTIFIER:
        next_tok = state.peek(1)
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "=":
            return parse_assignment(state)
        elif next_tok["type"] == TOKEN_OPERATOR and next_tok["value"] in ("+=", "-=", "*=", "/=", "//=", "%=", "**="):
            return parse_compound_assignment(state)
        elif next_tok["type"] == TOKEN_PUNCT and next_tok["value"] in ("(", "."):
            expr = parse_expr(state)
            if expr.type == "Call":
                return Node("ExprStmt", None, [expr], cur["lineno"])
            state.error(f"Invalid statement: '{cur['value']}' expression has no effect", cur["lineno"])
            return None
        else:
            state.error(f"Invalid statement: bare identifier '{cur['value']}' cannot stand alone", cur["lineno"])
            state.advance()
            return None

    if cur["type"] in (TOKEN_NEWLINE, TOKEN_EOF, TOKEN_DEDENT):
        return None

    state.error(f"Unexpected token: {cur['type']} ({cur['value']})", cur["lineno"])
    while not state.match(TOKEN_NEWLINE) and not state.match(TOKEN_EOF) and not state.match(TOKEN_DEDENT):
        state.advance()
    return None


def parse_import(state):
    tok = state.expect([(TOKEN_KEYWORD, "summon")], "Expected 'summon' for import")
    if tok is None:
        return None
    node = Node("Import", None, [], tok["lineno"])
    
    if not state.match(TOKEN_IDENTIFIER):
        state.error("Expected module name after 'summon'", state.current().get("lineno"))
        return node
    
    while True:
        if state.match(TOKEN_IDENTIFIER):
            mid = state.advance()
            node.add(Node("Module", mid["value"], [], mid["lineno"]))
        else:
            state.error("Expected module name in import statement", state.current().get("lineno"))
            break
        
        if state.match(TOKEN_PUNCT, ","):
            state.advance()
            if not state.match(TOKEN_IDENTIFIER):
                state.error("Expected module name after ',' in import", state.current().get("lineno"))
                break
        else:
            break
    return node


def parse_assignment(state):
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in assignment")
    if ident is None:
        return None
    state.expect([(TOKEN_PUNCT, "=")], "Expected '=' in assignment")
    
    if state.match(TOKEN_KEYWORD, "scout"):
        input_node = parse_input_stmt(state)
        return Node("Assignment", ident["value"], [input_node], ident["lineno"])
    
    expr = parse_expr(state)
    return Node("Assignment", ident["value"], [expr], ident["lineno"])


def parse_compound_assignment(state):
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in compound assignment")
    if ident is None:
        return None
    op_tok = state.expect([(TOKEN_OPERATOR, None)], "Expected compound operator")
    if op_tok is None or op_tok["value"] not in ("+=", "-=", "*=", "/=", "//=", "%=", "**="):
        state.error("Expected +=, -=, *=, /=, //=, %=, or **=", state.current().get("lineno"))
        return Node("Assignment", ident["value"], [], ident["lineno"])
    
    expr = parse_expr(state)
    base_op = op_tok["value"][:-1]
    var_node = Node("Identifier", ident["value"], [], ident["lineno"])
    binop = Node("BinaryOp", base_op, [var_node, expr], op_tok["lineno"])
    return Node("Assignment", ident["value"], [binop], ident["lineno"])


def parse_input_stmt(state):
    start = state.expect([(TOKEN_KEYWORD, "scout")], "Expected 'scout' for input")
    if start is None:
        return None
    node = Node("Input", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'scout'")
    node.add(parse_expr(state))
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after 'scout' argument")
    return node


def parse_output_stmt(state):
    start = state.expect([(TOKEN_KEYWORD, "attack")], "Expected 'attack' for output")
    if start is None:
        return None
    node = Node("Output", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'attack'")
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            node.add(parse_expr(state))
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after attack arguments")
    return node


def parse_if(state):
    start = state.expect([(TOKEN_KEYWORD, "spot")], "Expected 'spot' for if")
    if start is None:
        return None
    node = Node("If", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'spot'")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after if condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after if header")
    then_block = parse_statement_block(state)
    node.add(Node("Condition", None, [cond], cond.lineno if hasattr(cond, 'lineno') else start["lineno"]))
    node.add(Node("Then", None, then_block, start["lineno"]))

    while state.match(TOKEN_KEYWORD, "counter"):
        state.advance()
        state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'counter'")
        ccond = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after counter condition")
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after counter header")
        cbody = parse_statement_block(state)
        node.add(Node("Elif", None, [Node("Condition", None, [ccond]), Node("Body", None, cbody)], state.current().get("lineno")))

    if state.match(TOKEN_KEYWORD, "dodge"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after 'dodge'")
        node.add(Node("Else", None, parse_statement_block(state), state.current().get("lineno")))
    return node


def parse_while(state):
    start = state.expect([(TOKEN_KEYWORD, "replay")], "Expected 'replay' for while")
    if start is None:
        return None
    node = Node("While", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'replay'")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after while condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after while header")
    node.add(Node("Condition", None, [cond]))
    node.add(Node("Body", None, parse_statement_block(state)))
    return node


def parse_for(state):
    start = state.expect([(TOKEN_KEYWORD, "farm")], "Expected 'farm' for for-loop")
    if start is None:
        return None
    node = Node("For", None, [], start["lineno"])
    var = state.expect([(TOKEN_IDENTIFIER, None)], "Expected loop variable")
    if var:
        node.add(Node("Var", var["value"], [], var["lineno"]))
    
    in_tok = state.current()
    if in_tok["type"] == TOKEN_IDENTIFIER and in_tok["value"] == "in":
        state.advance()
    else:
        state.error("Expected 'in' in for loop", state.current().get("lineno"))
    
    node.add(Node("Iter", None, [parse_expr(state)]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after for header")
    node.add(Node("Body", None, parse_statement_block(state)))
    return node


def parse_function_def(state):
    start = state.expect([(TOKEN_KEYWORD, "quest")], "Expected 'quest' for function def")
    if start is None:
        return None
    name = state.expect([(TOKEN_IDENTIFIER, None)], "Expected function name")
    node = Node("FunctionDef", name["value"] if name else None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' in function def")
    params = []
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            p = state.expect([(TOKEN_IDENTIFIER, None)], "Expected parameter name")
            if p:
                params.append(p["value"])
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parameters")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after function header")
    node.add(Node("Params", None, [Node("Param", pname, [], None) for pname in params]))
    node.add(Node("Body", None, parse_statement_block(state)))
    return node


def parse_class_def(state):
    start = state.expect([(TOKEN_KEYWORD, "guild")], "Expected 'guild' for class def")
    if start is None:
        return None
    name = state.expect([(TOKEN_IDENTIFIER, None)], "Expected class name")
    node = Node("ClassDef", name["value"] if name else None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after class header")
    node.add(Node("Body", None, parse_statement_block(state)))
    return node


def parse_return(state):
    start = state.expect([(TOKEN_KEYWORD, "reward")], "Expected 'reward' for return")
    return Node("Return", None, [parse_expr(state)], start["lineno"]) if start else None


def parse_try_except(state):
    start = state.expect([(TOKEN_KEYWORD, "embark")], "Expected 'embark' for try")
    if start is None:
        return None
    node = Node("Try", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after embark")
    node.add(Node("TryBlock", None, parse_statement_block(state)))

    while state.match(TOKEN_KEYWORD, "gameOver"):
        state.advance()
        ex = state.advance() if state.match(TOKEN_IDENTIFIER) else None
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after exception type")
        node.add(Node("Except", ex["value"] if ex else None, parse_statement_block(state)))

    if state.match(TOKEN_KEYWORD, "savePoint"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after savePoint")
        node.add(Node("Finally", None, parse_statement_block(state)))
    return node


def parse_statement_block(state):
    if not state.match(TOKEN_NEWLINE):
        state.error("Expected NEWLINE before block", state.current().get("lineno"))
    state.advance()
    if not state.match(TOKEN_INDENT):
        state.error("Expected INDENT to start block", state.current().get("lineno"))
    if state.match(TOKEN_INDENT):
        state.advance()
    stmts = parse_statement_list(state, stop_on=(TOKEN_DEDENT, TOKEN_EOF))
    if not state.match(TOKEN_DEDENT):
        state.error("Expected DEDENT after block", state.current().get("lineno"))
    else:
        state.advance()
    return stmts


_PRECEDENCE = {
    "or": 1, "and": 2, "not": 3,
    "==": 4, "!=": 4, "<": 4, ">": 4, "<=": 4, ">=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "//": 6, "%": 6,
    "**": 7,
}

get_precedence = lambda tok: _PRECEDENCE.get(tok["value"], -1) if tok and tok["type"] in (TOKEN_OPERATOR, TOKEN_PUNCT) else -1

parse_condition = parse_expr = lambda state: parse_binop(state, 0)

def parse_binop(state, min_prec):
    left = parse_unary_or_primary(state)
    while get_precedence(state.current()) >= min_prec:
        op = state.advance()
        right = parse_binop(state, get_precedence(op) + 1)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    return left


def parse_unary_or_primary(state):
    cur = state.current()
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-"):
        op = state.advance()
        return Node("UnaryOp", op["value"], [parse_unary_or_primary(state)], op["lineno"])
    return parse_primary(state)


def parse_primary(state):
    cur = state.current()
    
    if cur["type"] in (TOKEN_NUMBER, TOKEN_STRING, TOKEN_LITERAL):
        tok = state.advance()
        return Node({"NUMBER": "Number", "STRING": "String", "LITERAL": "Literal"}[tok["type"]], tok["value"], [], tok["lineno"])
    
    if cur["type"] == TOKEN_IDENTIFIER:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        state.advance()
        while state.match(TOKEN_PUNCT, "."):
            state.advance()
            if state.match(TOKEN_IDENTIFIER):
                attr = state.advance()
                node = Node("Attribute", attr["value"], [node], attr["lineno"])
            else:
                state.error("Expected identifier after '.'", state.current().get("lineno"))
                break
        if state.match(TOKEN_PUNCT, "("):
            return parse_call_with_target(state, node)
        return node
    
    if cur["type"] == TOKEN_PUNCT and cur["value"] == "(":
        state.advance()
        expr = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parenthesized expression")
        return expr

    state.error(f"Unexpected expression token: {cur['type']} ({cur['value']})", cur["lineno"])
    state.advance()
    return Node("Empty")


def parse_call_with_target(state, target_node):
    lpar = state.expect([(TOKEN_PUNCT, "(")], "Expected '(' for function call")
    args = []
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            args.append(parse_expr(state))
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after call arguments")
    return Node("Call", None, [target_node] + args, lpar["lineno"] if lpar else target_node.lineno)