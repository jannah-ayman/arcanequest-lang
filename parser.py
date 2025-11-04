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
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return make_token(TOKEN_EOF, "EOF", -1, -1)

    def peek(self, offset=1):
        j = self.i + offset
        if j < len(self.tokens):
            return self.tokens[j]
        return make_token(TOKEN_EOF, "EOF", -1, -1)

    def advance(self):
        tok = self.current()
        self.i += 1
        return tok

    def match(self, ttype=None, value=None):
        cur = self.current()
        if ttype is None:
            return True
        if cur["type"] != ttype:
            return False
        if value is not None and cur["value"] != value:
            return False
        return True

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

# PARSER IMPLEMENTATION
def parse(tokens):
    state = ParserState(tokens)
    root = Node("Program", lineno=1)
    try:
        sl = parse_statement_list(state, stop_on=(TOKEN_EOF,))
        for s in sl:
            if s:
                root.add(s)
    except Exception as e:
        state.error(f"Internal parser error: {e}", state.current().get("lineno", -1))
    return root, state.errors


def parse_statement_list(state, stop_on=(TOKEN_EOF, TOKEN_DEDENT)):
    stmts = []
    while state.match(TOKEN_NEWLINE):
        state.advance()
    while True:
        if state.match(TOKEN_EOF) or state.match(TOKEN_DEDENT) or state.current()["type"] in stop_on:
            break
        st = parse_statement(state)
        if st:
            stmts.append(st)
        while state.match(TOKEN_NEWLINE):
            state.advance()
        if state.match(TOKEN_EOF):
            break
    return stmts


def parse_statement(state):
    cur = state.current()
    if cur["type"] == TOKEN_COMMENT:
        tok = state.advance()
        return Node("Comment", tok["value"], [], tok["lineno"])

    if cur["type"] == TOKEN_KEYWORD:
        kw = cur["value"]
        if kw == "summon":
            return parse_import(state)
        elif kw == "spot":
            return parse_if(state)
        elif kw == "replay":
            return parse_while(state)
        elif kw == "farm":
            return parse_for(state)
        elif kw == "quest":
            return parse_function_def(state)
        elif kw == "guild":
            return parse_class_def(state)
        elif kw == "attack":
            return parse_output_stmt(state)
        elif kw == "scout":
            return parse_input_stmt(state)
        elif kw == "embark":
            return parse_try_except(state)
        elif kw == "skipEncounter":
            tok = state.advance()
            return Node("Continue", None, [], tok["lineno"])
        elif kw == "escapeDungeon":
            tok = state.advance()
            return Node("Break", None, [], tok["lineno"])
        elif kw == "reward":
            return parse_return(state)
        else:
            tok = state.advance()
            return Node("KeywordStmt", tok["value"], [], tok["lineno"])

    if cur["type"] == TOKEN_IDENTIFIER:
        # Look ahead to determine what kind of statement this is
        next_tok = state.peek(1)
        
        # Assignment: x = ...
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "=":
            return parse_assignment(state)
        
        # Compound assignment: x += ...
        elif next_tok["type"] == TOKEN_OPERATOR and next_tok["value"] in ("+=", "-=", "*=", "/=", "//=", "%=", "**="):
            return parse_compound_assignment(state)
        
        # Function call or attribute access: func() or obj.method()
        elif next_tok["type"] == TOKEN_PUNCT and (next_tok["value"] == "(" or next_tok["value"] == "."):
            expr = parse_expr(state)
            # Verify it's actually a call (not just an attribute access)
            if expr.type == "Call":
                return Node("ExprStmt", None, [expr], cur["lineno"])
            else:
                # Just an identifier or attribute without a call - error
                state.error(f"Invalid statement: '{cur['value']}' expression has no effect", cur["lineno"])
                return None
        
        else:
            # Bare identifier - this is an error!
            state.error(f"Invalid statement: bare identifier '{cur['value']}' cannot stand alone", cur["lineno"])
            state.advance()  # consume the invalid token
            return None

    if cur["type"] == TOKEN_NEWLINE:
        state.advance()
        return None

    if cur["type"] in (TOKEN_EOF, TOKEN_DEDENT):
        return None

    state.error(f"Unexpected token: {cur['type']} ({cur['value']})", cur["lineno"])
    while not state.match(TOKEN_NEWLINE) and not state.match(TOKEN_EOF) and not state.match(TOKEN_DEDENT):
        state.advance()
    return None


# ---------------- specific constructs ----------------

def parse_import(state):
    tok = state.expect([(TOKEN_KEYWORD, "summon")], "Expected 'summon' for import")
    if tok is None:
        return None
    node = Node("Import", None, [], tok["lineno"])
    
    # Expect at least one module name
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
        
        # Must have comma to continue, otherwise break
        if state.match(TOKEN_PUNCT, ","):
            state.advance()
            # After comma, MUST have another identifier
            if not state.match(TOKEN_IDENTIFIER):
                state.error("Expected module name after ',' in import", state.current().get("lineno"))
                break
        else:
            # No comma means end of import list
            break
    
    return node


def parse_assignment(state):
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in assignment")
    if ident is None:
        return None
    assign_tok = state.expect([(TOKEN_PUNCT, "=")], "Expected '=' in assignment")
    if assign_tok is None:
        return Node("Assignment", ident["value"], [], ident["lineno"])
    
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
    # Extract base operator (e.g., "+" from "+=", "**" from "**=")
    base_op = op_tok["value"][:-1]  # Remove the "=" at the end
    var_node = Node("Identifier", ident["value"], [], ident["lineno"])
    binop = Node("BinaryOp", base_op, [var_node, expr], op_tok["lineno"])
    return Node("Assignment", ident["value"], [binop], ident["lineno"])


def parse_input_stmt(state):
    start = state.expect([(TOKEN_KEYWORD, "scout")], "Expected 'scout' for input")
    if start is None:
        return None
    node = Node("Input", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'scout'")
    prompt_expr = parse_expr(state)
    node.add(prompt_expr)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after 'scout' argument")
    return node


def parse_output_stmt(state):
    start = state.expect([(TOKEN_KEYWORD, "attack")], "Expected 'attack' for output")
    if start is None:
        return None
    node = Node("Output", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'attack'")
    args = []
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            expr = parse_expr(state)
            args.append(expr)
            if state.match(TOKEN_PUNCT, ","):
                state.advance()
                continue
            break
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after attack arguments")
    node.children = args
    return node


def parse_case(state):
    start = state.expect([(TOKEN_KEYWORD, "case")], "Expected 'case' in match")
    if start is None:
        return None
    node = Node("Case", None, [], start["lineno"])
    
    if state.match(TOKEN_IDENTIFIER, "_"):
        underscore = state.advance()
        node.add(Node("Value", "_", [], underscore["lineno"]))
    elif state.match(TOKEN_STRING) or state.match(TOKEN_NUMBER) or state.match(TOKEN_LITERAL):
        val_tok = state.advance()
        node.add(Node("Value", val_tok["value"], [], val_tok["lineno"]))
    else:
        state.error("Expected literal/number/string/_ after 'case'", state.current().get("lineno"))
    
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after case value")
    
    if state.match(TOKEN_NEWLINE):
        block = parse_statement_block(state)
        node.add(Node("Body", None, block))
    else:
        stmt = parse_statement(state)
        node.add(Node("Body", None, [stmt] if stmt else []))
    
    return node


def parse_match(state):
    start = state.expect([(TOKEN_KEYWORD, "ambush")], "Expected 'ambush' for match")
    if start is None:
        return None
    node = Node("Match", None, [], start["lineno"])
    expr = parse_expr(state)
    node.add(Node("Expr", None, [expr]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after ambush expression")

    if state.match(TOKEN_NEWLINE):
        state.advance()
    else:
        state.error("Expected NEWLINE before match cases", state.current().get("lineno"))

    if state.match(TOKEN_INDENT):
        state.advance()
        while state.match(TOKEN_KEYWORD, "case"):
            case_node = parse_case(state)
            node.add(case_node)
        state.expect([(TOKEN_DEDENT, None)], "Expected DEDENT after match block")
    else:
        state.error("Expected indented block of cases", state.current().get("lineno"))
    return node


def parse_case(state):
    start = state.expect([(TOKEN_KEYWORD, "case")], "Expected 'case' in match")
    if start is None:
        return None
    node = Node("Case", None, [], start["lineno"])
    
    if state.match(TOKEN_IDENTIFIER, "_"):
        underscore = state.advance()
        node.add(Node("Value", "_", [], underscore["lineno"]))
    elif state.match(TOKEN_STRING) or state.match(TOKEN_NUMBER) or state.match(TOKEN_LITERAL):
        val_tok = state.advance()
        node.add(Node("Value", val_tok["value"], [], val_tok["lineno"]))
    else:
        state.error("Expected literal/number/string/_ after 'case'", state.current().get("lineno"))
    
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after case value")
    
    if state.match(TOKEN_NEWLINE):
        block = parse_statement_block(state)
        node.add(Node("Body", None, block))
    else:
        stmt = parse_statement(state)
        node.add(Node("Body", None, [stmt] if stmt else []))
    
    return node


def parse_match(state):
    start = state.expect([(TOKEN_KEYWORD, "ambush")], "Expected 'ambush' for match")
    if start is None:
        return None
    node = Node("Match", None, [], start["lineno"])
    expr = parse_expr(state)
    node.add(Node("Expr", None, [expr]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after ambush expression")

    if state.match(TOKEN_NEWLINE):
        state.advance()
    else:
        state.error("Expected NEWLINE before match cases", state.current().get("lineno"))

    if state.match(TOKEN_INDENT):
        state.advance()
        while state.match(TOKEN_KEYWORD, "case"):
            case_node = parse_case(state)
            node.add(case_node)
        state.expect([(TOKEN_DEDENT, None)], "Expected DEDENT after match block")
    else:
        state.error("Expected indented block of cases", state.current().get("lineno"))
    return node


def parse_if(state):
    start = state.expect([(TOKEN_KEYWORD, "spot")], "Expected 'spot' for if")
    if start is None:
        return None
    node = Node("If", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'spot'")
    cond = parse_condition(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after if condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after if header")
    then_block = parse_statement_block(state)
    node.add(Node("Condition", None, [cond], cond.lineno if hasattr(cond, 'lineno') else start["lineno"]))
    node.add(Node("Then", None, then_block, start["lineno"]))

    while state.match(TOKEN_KEYWORD, "counter"):
        state.advance()
        state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'counter'")
        ccond = parse_condition(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after counter condition")
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after counter header")
        cbody = parse_statement_block(state)
        node.add(Node("Elif", None, [Node("Condition", None, [ccond]), Node("Body", None, cbody)], state.current().get("lineno")))

    if state.match(TOKEN_KEYWORD, "dodge"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after 'dodge'")
        dblock = parse_statement_block(state)
        node.add(Node("Else", None, dblock, state.current().get("lineno")))
    return node


def parse_while(state):
    start = state.expect([(TOKEN_KEYWORD, "replay")], "Expected 'replay' for while")
    if start is None:
        return None
    node = Node("While", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'replay'")
    cond = parse_condition(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after while condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after while header")
    body = parse_statement_block(state)
    node.add(Node("Condition", None, [cond]))
    node.add(Node("Body", None, body))
    return node


def parse_for(state):
    start = state.expect([(TOKEN_KEYWORD, "farm")], "Expected 'farm' for for-loop")
    if start is None:
        return None
    node = Node("For", None, [], start["lineno"])
    var = state.expect([(TOKEN_IDENTIFIER, None)], "Expected loop variable")
    if var:
        node.add(Node("Var", var["value"], [], var["lineno"]))
    
    # "in" should be treated as an identifier, not a keyword
    in_tok = state.current()
    if in_tok["type"] == TOKEN_IDENTIFIER and in_tok["value"] == "in":
        state.advance()
    else:
        state.error("Expected 'in' in for loop", state.current().get("lineno"))
    
    expr = parse_expr(state)
    node.add(Node("Iter", None, [expr]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after for header")
    body = parse_statement_block(state)
    node.add(Node("Body", None, body))
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
            if state.match(TOKEN_PUNCT, ","):
                state.advance()
                continue
            break
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parameters")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after function header")
    body = parse_statement_block(state)
    node.add(Node("Params", None, [Node("Param", pname, [], None) for pname in params]))
    node.add(Node("Body", None, body))
    return node


def parse_class_def(state):
    start = state.expect([(TOKEN_KEYWORD, "guild")], "Expected 'guild' for class def")
    if start is None:
        return None
    name = state.expect([(TOKEN_IDENTIFIER, None)], "Expected class name")
    node = Node("ClassDef", name["value"] if name else None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after class header")
    body = parse_statement_block(state)
    node.add(Node("Body", None, body))
    return node


def parse_return(state):
    start = state.expect([(TOKEN_KEYWORD, "reward")], "Expected 'reward' for return")
    if start is None:
        return None
    expr = parse_expr(state)
    return Node("Return", None, [expr], start["lineno"])


def parse_try_except(state):
    start = state.expect([(TOKEN_KEYWORD, "embark")], "Expected 'embark' for try")
    if start is None:
        return None
    node = Node("Try", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after embark")
    try_block = parse_statement_block(state)
    node.add(Node("TryBlock", None, try_block))

    while state.match(TOKEN_KEYWORD, "gameOver"):
        state.advance()
        ex = None
        if state.match(TOKEN_IDENTIFIER):
            ex = state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after exception type")
        handler_block = parse_statement_block(state)
        node.add(Node("Except", ex["value"] if ex else None, handler_block))

    if state.match(TOKEN_KEYWORD, "savePoint"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after savePoint")
        finally_block = parse_statement_block(state)
        node.add(Node("Finally", None, finally_block))
    return node


def parse_statement_block(state):
    if state.match(TOKEN_NEWLINE):
        state.advance()
    else:
        state.error("Expected NEWLINE before block", state.current().get("lineno"))
    if not state.match(TOKEN_INDENT):
        state.error("Expected INDENT to start block", state.current().get("lineno"))
    if state.match(TOKEN_INDENT):
        state.advance()
    stmts = parse_statement_list(state, stop_on=(TOKEN_DEDENT, TOKEN_EOF))
    if state.match(TOKEN_DEDENT):
        state.advance()
    else:
        state.error("Expected DEDENT after block", state.current().get("lineno"))
    return stmts

_PRECEDENCE = {
    "or": 1,
    "and": 2,
    "not": 3,
    "==": 4, "!=": 4, "<": 4, ">": 4, "<=": 4, ">=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "//": 6, "%": 6,
    "**": 7,  
}

def get_precedence(tok):
    if tok is None:
        return -1
    if tok["type"] == TOKEN_OPERATOR:
        return _PRECEDENCE.get(tok["value"], -1)
    if tok["type"] == TOKEN_PUNCT and tok["value"] in ("+", "-", "*", "/", "<", ">", "%"):
        return _PRECEDENCE.get(tok["value"], -1)
    return -1


def parse_condition(state):
    return parse_expr(state)


def parse_expr(state):
    return parse_binop(state, 0)


def parse_binop(state, min_prec):
    left = parse_unary_or_primary(state)
    while True:
        cur = state.current()
        prec = get_precedence(cur)
        if prec < min_prec:
            break
        op = state.advance()
        right = parse_binop(state, prec + 1)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    return left


def parse_unary_or_primary(state):
    cur = state.current()
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-"):
        op = state.advance()
        operand = parse_unary_or_primary(state)
        return Node("UnaryOp", op["value"], [operand], op["lineno"])
    return parse_primary(state)


def parse_primary(state):
    cur = state.current()
    if cur["type"] == TOKEN_NUMBER:
        tok = state.advance()
        return Node("Number", tok["value"], [], tok["lineno"])
    if cur["type"] == TOKEN_STRING:
        tok = state.advance()
        return Node("String", tok["value"], [], tok["lineno"])
    if cur["type"] == TOKEN_LITERAL:
        tok = state.advance()
        return Node("Literal", tok["value"], [], tok["lineno"])
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
            arg = parse_expr(state)
            args.append(arg)
            if state.match(TOKEN_PUNCT, ","):
                state.advance()
                continue
            break
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after call arguments")
    callnode = Node("Call", None, [target_node] + args, lpar["lineno"] if lpar else target_node.lineno)
    return callnode