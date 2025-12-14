from scanner import *

DATA_TYPE_INT = "potion"
DATA_TYPE_DOUBLE = "elixir"
DATA_TYPE_STRING = "scroll"
DATA_TYPE_BOOL = "fate"

class Node:
    def __init__(self, ntype, value=None, 
                 children=None, lineno=None):
        self.type = ntype
        self.value = value
        self.children = children \
            if children is not None else []
        self.lineno = lineno
        self.dtype = None  # For type inference

    def add(self, node):
        self.children.append(node)

    def pretty(self, indent=0):
        pad = "  " * indent
        val = f": {self.value}" if self.value is not None else ""
        lineinfo = f" (line {self.lineno})" if self.lineno else ""
        dtype_info = f" [{self.dtype}]" if self.dtype else ""
        out = f"{pad}{self.type}{val}{lineinfo}{dtype_info}\n"
        for c in self.children:
            out += c.pretty(indent + 1)
        return out

class IdentifierInfo:
    def __init__(self, name, dtype, line):
        self.name = name
        self.dtype = dtype
        self.line = line
    
    def __repr__(self):
        return f"IdentifierInfo({self.name}, {self.dtype}, line {self.line})"

class SymbolTable:
    def __init__(self):
        self.scopes = [{}]  # Start with global scope
    
    def push_scope(self):
        self.scopes.append({})
    
    def pop_scope(self):
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def declare(self, name, dtype, line):
        current_scope = self.scopes[-1]
        current_scope[name] = IdentifierInfo(name, dtype, line)
        return current_scope[name]
    
    def update_type(self, name, dtype):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name].dtype = dtype
                return scope[name]
        return None
    
    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

def datatype_check(t1, t2, operator):
    if t1 == "unknown" or t2 == "unknown":
        return "unknown"

    if operator == "+" and t1 == DATA_TYPE_STRING and t2 == DATA_TYPE_STRING:
        return DATA_TYPE_STRING
    
    if operator == "*":
        if (t1 == DATA_TYPE_STRING and t2 == DATA_TYPE_INT) or \
           (t1 == DATA_TYPE_INT and t2 == DATA_TYPE_STRING):
            return DATA_TYPE_STRING
    
    if operator in ["+", "-", "*", "/", "//", "%", "**"]:
        if t1 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE) and t2 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
            if operator == "/":
                return DATA_TYPE_DOUBLE
            if t1 == DATA_TYPE_DOUBLE or t2 == DATA_TYPE_DOUBLE:
                return DATA_TYPE_DOUBLE
            return DATA_TYPE_INT
        return None
    
    if operator in ["<", ">", "<=", ">="]:
        if t1 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE) and t2 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
            return DATA_TYPE_BOOL
        return None 
    
    if operator in ["==", "!="]:
        if t1 == t2:
            return DATA_TYPE_BOOL
        return None 
    if operator in ["and", "or"]:
        if t1 == DATA_TYPE_BOOL and t2 == DATA_TYPE_BOOL:
            return DATA_TYPE_BOOL
        return None
    return None 

class ParserState:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0
        self.errors = []
        self.panic_mode = False
        self.function_bodies = {} 
        self.function_params = {}  
        self.function_return_types = {}
        self.symbol_table = SymbolTable()

    def current(self):
        #Get the current token without advancing.
        return self.tokens[self.i] if self.i < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def peek(self, offset=1):
        #Look ahead at a token without advancing
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def advance(self):
        #Consume and return the current token.
        tok = self.current()
        self.i += 1
        self.panic_mode = False
        return tok

    def match(self, ttype=None, value=None):
        #Check if current token matches criteria.
        cur = self.current()
        return (ttype is None or cur["type"] == ttype) and \
               (value is None or cur["value"] == value)

    def expect(self, expected_pairs, msg=None):
        #Consume a token if it matches expected type/value pairs
        cur = self.current()
        for (t, v) in expected_pairs:
            if cur["type"] == t and (v is None or cur["value"] == v):
                return self.advance()
        
        self.error(msg or f"Expected {expected_pairs}, got {cur['type']}({cur['value']})", cur["lineno"])
        return None

    def error(self, msg, lineno=None):
        #Record a parse error
        ln = lineno if lineno is not None else self.current().get("lineno", -1)
        self.errors.append((ln, msg))
        self.panic_mode = True

    def semantic_error(self, msg, lineno=None):
        #Record a semantic error without entering panic mode
        ln = lineno if lineno is not None else self.current().get("lineno", -1)
        self.errors.append((ln, f"Semantic: {msg}"))

    def synchronize(self):
        #Skip tokens until we find a safe synchronization point
        if not self.panic_mode:
            return
        
        while not self.match(TOKEN_EOF):
            if self.match(TOKEN_NEWLINE):
                self.advance()
                self.panic_mode = False
                return
            
            if self.match(TOKEN_KEYWORD):
                if self.current()["value"] in ("summon", "spot", "replay", "farm", 
                                               "quest", "attack", "embark", "reward"):
                    self.panic_mode = False
                    return
            
            if self.match(TOKEN_DEDENT):
                self.panic_mode = False
                return
            
            self.advance()
        
        self.panic_mode = False

def parse(tokens):
    # returns ST root and list of errors.
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
    #Parse a sequence of statements until a stopping token
    stmts = []
    
    # Skip leading blank lines
    while state.match(TOKEN_NEWLINE):
        state.advance()
    
    while not (state.match(TOKEN_EOF) or 
               state.match(TOKEN_DEDENT) or 
               state.current()["type"] in stop_on):
        
        st = parse_statement(state)
        if st:
            stmts.append(st)
        
        if state.panic_mode:
            state.synchronize()
        
        while state.match(TOKEN_NEWLINE):
            state.advance()
        
        if state.match(TOKEN_EOF):
            break
    
    return stmts

KEYWORD_PARSERS = {
    "summon": lambda s: parse_import(s),
    "spot": lambda s: parse_if(s),
    "replay": lambda s: parse_while(s),
    "farm": lambda s: parse_for(s),
    "quest": lambda s: parse_function_def(s),
    "attack": lambda s: parse_output_stmt(s),
    "scout": lambda s: parse_input_stmt(s),
    "embark": lambda s: parse_try_except(s),
    "reward": lambda s: parse_return(s),
    "skipEncounter": lambda s: Node("Continue", None, [], s.advance()["lineno"]),
    "escapeDungeon": lambda s: Node("Break", None, [], s.advance()["lineno"]),
}

def parse_statement(state):
    #Parse a single statement
    cur = state.current()
    
    # Comment
    if cur["type"] == TOKEN_COMMENT:
        tok = state.advance()
        return Node("Comment", tok["value"], [], tok["lineno"])

    # Keyword statements
    if cur["type"] == TOKEN_KEYWORD:
        parser = KEYWORD_PARSERS.get(cur["value"])
        if parser:
            return parser(state)
        tok = state.advance()
        return Node("KeywordStmt", tok["value"], [], tok["lineno"])

    # Data type casting
    if cur["type"] == TOKEN_DATATYPE:
        next_tok = state.peek(1)
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "(":
            expr = parse_expr(state)
            if expr.type == "Call":
                return Node("ExprStmt", None, [expr], cur["lineno"])
        
        state.error(f"Invalid statement: datatype '{cur['value']}' cannot stand alone", cur["lineno"])
        state.advance()
        return None

    # Identifier statements
    if cur["type"] == TOKEN_IDENTIFIER:
        next_tok = state.peek(1)
        
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "=":
            return parse_assignment(state)
        elif next_tok["type"] == TOKEN_OPERATOR and next_tok["value"] in ("+=", "-=", "*=", "/=", "%=", "**="):
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
    state.advance()
    return None

def parse_import(state):
    #Parse import statement: summon module1, module2, ...
    tok = state.expect([(TOKEN_KEYWORD, "summon")], "Expected 'summon' for import")
    if tok is None:
        return Node("Import", None, [], state.current().get("lineno"))
    
    node = Node("Import", None, [], tok["lineno"])
    
    if not state.match(TOKEN_IDENTIFIER):
        state.error("Expected module name after 'summon'", state.current().get("lineno"))
        return node
    
    while True:
        if state.match(TOKEN_IDENTIFIER):
            mid = state.advance()
            # SEMANTIC: Register module in symbol table
            state.symbol_table.declare(mid["value"], "module", mid["lineno"])
            node.add(Node("Module", mid["value"], [], mid["lineno"]))
        else:
            state.error("Expected module name in import statement", state.current().get("lineno"))
            break
        
        if state.match(TOKEN_PUNCT, ","):
            state.advance()
            if not state.match(TOKEN_IDENTIFIER):
                state.error("Expected module name after ','", state.current().get("lineno"))
                break
        else:
            break
    
    return node

def parse_assignment(state):
    #Parse assignment: identifier = expr
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in assignment")
    if ident is None:
        return Node("Assignment", None, [], state.current().get("lineno"))
    
    state.expect([(TOKEN_PUNCT, "=")], "Expected '=' in assignment")
    
    # Special case: assignment from input
    if state.match(TOKEN_KEYWORD, "scout"):
        input_node = parse_input_stmt(state)
        node = Node("Assignment", ident["value"], [input_node], ident["lineno"])
        
        # SEMANTIC: scout returns string
        node.dtype = DATA_TYPE_STRING
        var_info = state.symbol_table.lookup(ident["value"])
        if var_info:
            state.symbol_table.update_type(ident["value"], DATA_TYPE_STRING)
        else:
            state.symbol_table.declare(ident["value"], DATA_TYPE_STRING, ident["lineno"])
        return node
    
    # Regular expression assignment
    expr = parse_expr(state)
    node = Node("Assignment", ident["value"], [expr], ident["lineno"])
    
    # SEMANTIC: Infer type from expression
    if expr.dtype:
        node.dtype = expr.dtype
        var_info = state.symbol_table.lookup(ident["value"])
        if var_info:
            # Update existing variable type
            state.symbol_table.update_type(ident["value"], expr.dtype)
        else:
            # Declare new variable
            state.symbol_table.declare(ident["value"], expr.dtype, ident["lineno"])
    else:
        state.semantic_error(f"Cannot determine type for assignment to '{ident['value']}'", ident["lineno"])
    
    return node

def parse_compound_assignment(state):
    #Parse compound assignment: identifier += expr
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier")
    if ident is None:
        return Node("Assignment", None, [], state.current().get("lineno"))
    
    # SEMANTIC: Check if variable exists
    var_info = state.symbol_table.lookup(ident["value"])
    if var_info is None:
        state.semantic_error(f"Undeclared variable '{ident['value']}'", ident["lineno"])
    
    op_tok = state.expect([(TOKEN_OPERATOR, None)], "Expected compound operator")
    if op_tok is None or op_tok["value"] not in ("+=", "-=", "*=", "/=", "%=", "**="):
        state.error("Expected +=, -=, *=, /=, %=, or **=", state.current().get("lineno"))
        return Node("Assignment", ident["value"], [], ident["lineno"])
    
    expr = parse_expr(state)
    
    # Desugar: x += y becomes x = x + y
    base_op = op_tok["value"][:-1]
    var_node = Node("Identifier", ident["value"], [], ident["lineno"])
    var_node.dtype = var_info.dtype if var_info else None
    
    binop = Node("BinaryOp", base_op, [var_node, expr], op_tok["lineno"])
    
    # SEMANTIC: Type check the operation
    if var_node.dtype and expr.dtype:
        result_type = datatype_check(var_node.dtype, expr.dtype, base_op)
        if result_type is None:
            state.semantic_error(
                f"Type mismatch: cannot apply '{base_op}' to {var_node.dtype} and {expr.dtype}",
                op_tok["lineno"]
            )
        else:
            binop.dtype = result_type
            if var_info:
                state.symbol_table.update_type(ident["value"], result_type)
    
    node = Node("Assignment", ident["value"], [binop], ident["lineno"])
    node.dtype = binop.dtype
    return node

def parse_input_stmt(state):
    #Parse input statement: scout(prompt
    start = state.expect([(TOKEN_KEYWORD, "scout")], "Expected 'scout'")
    if start is None:
        return Node("Input", None, [], state.current().get("lineno"))
    
    node = Node("Input", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'scout'")
    node.add(parse_expr(state))
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after 'scout' argument")
    
    # SEMANTIC: scout always returns string
    node.dtype = DATA_TYPE_STRING
    return node

def parse_output_stmt(state):
    #Parse output statement: attack(expr, expr, ...)
    start = state.expect([(TOKEN_KEYWORD, "attack")], "Expected 'attack'")
    if start is None:
        return Node("Output", None, [], state.current().get("lineno"))
    
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

def parse_condition(state):
    #Parse a condition in parentheses
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' before condition")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after condition")
    
    # SEMANTIC: Condition must be boolean
    if cond.dtype and cond.dtype != DATA_TYPE_BOOL:
        state.semantic_error(f"Condition must be boolean, got {cond.dtype}", cond.lineno)
    
    return cond

def parse_if(state):
    #Parse if statement: spot (cond): ... counter (cond): ... dodge: ...
    start = state.expect([(TOKEN_KEYWORD, "spot")], "Expected 'spot'")
    if start is None:
        return Node("If", None, [], state.current().get("lineno"))
    
    node = Node("If", None, [], start["lineno"])
    
    cond = parse_condition(state)
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after if header")
    
    # SEMANTIC: Enter new scope for then block
    state.symbol_table.push_scope()
    then_block = parse_statement_block(state)
    state.symbol_table.pop_scope()
    
    node.add(Node("Condition", None, [cond], cond.lineno 
                  if hasattr(cond, 'lineno') else start["lineno"]))
    node.add(Node("Then", None, then_block, start["lineno"]))

    # Parse elif clauses
    while state.match(TOKEN_KEYWORD, "counter"):
        state.advance()
        ccond = parse_condition(state)
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after counter header")
        
        state.symbol_table.push_scope()
        cbody = parse_statement_block(state)
        state.symbol_table.pop_scope()
        
        node.add(Node("Elif", None, [
            Node("Condition", None, [ccond]),
            Node("Body", None, cbody)
        ], state.current().get("lineno")))

    # Parse else clause
    if state.match(TOKEN_KEYWORD, "dodge"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after 'dodge'")
        
        state.symbol_table.push_scope()
        else_body = parse_statement_block(state)
        state.symbol_table.pop_scope()
        
        node.add(Node("Else", None, else_body, state.current().get("lineno")))
    
    return node

def parse_while(state):
    #Parse while loop: replay (cond): ...
    start = state.expect([(TOKEN_KEYWORD, "replay")], "Expected 'replay'")
    if start is None:
        return Node("While", None, [], state.current().get("lineno"))
    
    node = Node("While", None, [], start["lineno"])
    
    cond = parse_condition(state)
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after while header")
    
    # SEMANTIC: Enter new scope
    state.symbol_table.push_scope()
    body = parse_statement_block(state)
    state.symbol_table.pop_scope()
    
    node.add(Node("Condition", None, [cond]))
    node.add(Node("Body", None, body))
    
    return node

def parse_for(state):
    #Parse for loop: farm var in iterable: ...
    start = state.expect([(TOKEN_KEYWORD, "farm")], "Expected 'farm'")
    if start is None:
        return Node("For", None, [], state.current().get("lineno"))
    
    node = Node("For", None, [], start["lineno"])
    
    var = state.expect([(TOKEN_IDENTIFIER, None)], "Expected loop variable")
    if var:
        node.add(Node("Var", var["value"], [], var["lineno"]))
    
    in_tok = state.current()
    if in_tok["type"] == TOKEN_IDENTIFIER and in_tok["value"] == "in":
        state.advance()
    else:
        state.error("Expected 'in' in for loop", state.current().get("lineno"))
    
    iter_expr = parse_expr(state)
    node.add(Node("Iter", None, [iter_expr]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after for header")
    
    # SEMANTIC: Enter new scope and declare loop variable
    state.symbol_table.push_scope()
    if var:
        state.symbol_table.declare(var["value"], DATA_TYPE_INT, var["lineno"])
    
    body = parse_statement_block(state)
    state.symbol_table.pop_scope()
    
    node.add(Node("Body", None, body))
    
    return node

def collect_return_type(body_statements):
    """Collect the return type from a function body by finding return statements."""
    for stmt in body_statements:
        if stmt and stmt.type == "Return" and stmt.dtype:
            return stmt.dtype
        # Also check in nested structures (if/while/for/try blocks)
        if stmt and stmt.children:
            nested_return = collect_return_type(stmt.children)
            if nested_return:
                return nested_return
    return None

def infer_function_return_type(state, func_name, arg_types):
    """Infer return type by re-analyzing function body with concrete argument types."""
    if func_name not in state.function_bodies:
        return "unknown"
    params = state.function_params.get(func_name, [])
    body = state.function_bodies[func_name]
    if len(arg_types) != len(params):
        return "unknown"
    
    # Save and create temporary symbol table
    saved_scopes = state.symbol_table.scopes
    state.symbol_table.scopes = [{}]
    
    # Declare parameters with concrete types
    for param_name, arg_type in zip(params, arg_types):
        state.symbol_table.declare(param_name, arg_type, -1)
    
    # Re-infer types in function body
    inferred_return = infer_types_in_statements(state, body)
    
    # Restore original symbol table
    state.symbol_table.scopes = saved_scopes
    return inferred_return if inferred_return else "unknown"

def infer_types_in_statements(state, statements):
    """Recursively infer types, looking for return statements."""
    for stmt in statements:
        if not stmt:
            continue
        
        # Handle assignments to update variable types
        if stmt.type == "Assignment" and stmt.children:
            expr = stmt.children[0]
            infer_expr_type(state, expr)
            if expr.dtype and expr.dtype != "unknown":
                var_info = state.symbol_table.lookup(stmt.value)
                if var_info:
                    # If variable already exists, update only if new type is "better" (elixir > potion)
                    if var_info.dtype == DATA_TYPE_INT and expr.dtype == DATA_TYPE_DOUBLE:
                        state.symbol_table.update_type(stmt.value, expr.dtype)
                    elif var_info.dtype != DATA_TYPE_DOUBLE:
                        state.symbol_table.update_type(stmt.value, expr.dtype)
                else:
                    state.symbol_table.declare(stmt.value, expr.dtype, stmt.lineno)
        
        if stmt.type == "Return" and stmt.children:
            return_expr = stmt.children[0]
            infer_expr_type(state, return_expr)
            if return_expr.dtype and return_expr.dtype != "unknown":
                return return_expr.dtype
        elif stmt.type in ("If", "While", "For", "Try"):
            for child in stmt.children:
                if child and child.children:
                    result = infer_types_in_statements(state, child.children)
                    if result and result != "unknown":
                        return result
    return None

def infer_expr_type(state, expr):
    """Re-infer expression type with current symbol table."""
    if not expr:
        return
    if expr.type == "Identifier":
        var_info = state.symbol_table.lookup(expr.value)
        if var_info:
            expr.dtype = var_info.dtype
    elif expr.type == "BinaryOp":
        if len(expr.children) >= 2:
            infer_expr_type(state, expr.children[0])
            infer_expr_type(state, expr.children[1])
            left_type = expr.children[0].dtype
            right_type = expr.children[1].dtype
            if left_type and right_type:
                result_type = datatype_check(left_type, right_type, expr.value)
                if result_type:
                    expr.dtype = result_type
    elif expr.type == "UnaryOp":
        if expr.children:
            infer_expr_type(state, expr.children[0])
            operand_type = expr.children[0].dtype
            if operand_type:
                if expr.value == "not" and operand_type == DATA_TYPE_BOOL:
                    expr.dtype = DATA_TYPE_BOOL
                elif expr.value in ("+", "-") and operand_type in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
                    expr.dtype = operand_type

def parse_function_def(state):
    """Parse function definition: quest name(params): ..."""
    start = state.expect([(TOKEN_KEYWORD, "quest")], "Expected 'quest'")
    if start is None:
        return Node("FunctionDef", None, [], state.current().get("lineno"))
    
    name = state.expect([(TOKEN_IDENTIFIER, None)], "Expected function name")
    node = Node("FunctionDef", name["value"] if name else None, [], start["lineno"])
    
    # SEMANTIC: Declare function in current scope
    if name:
        state.symbol_table.declare(name["value"], "function", name["lineno"])
    
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
    
    # SEMANTIC: Enter new scope and declare parameters
    state.symbol_table.push_scope()
    for param_name in params:
        state.symbol_table.declare(param_name, "unknown", start["lineno"])
    
    body = parse_statement_block(state)
    
    if name:
        state.function_params[name["value"]] = params
        state.function_bodies[name["value"]] = body

    # SEMANTIC: Infer types in function body first
    for stmt in body:
        if stmt and stmt.type == "Assignment" and stmt.children:
            expr = stmt.children[0]
            infer_expr_type(state, expr)
            if expr.dtype and expr.dtype != "unknown":
                state.symbol_table.update_type(stmt.value, expr.dtype)
        elif stmt and stmt.type == "Return" and stmt.children:
            # Also infer type for return expressions
            infer_expr_type(state, stmt.children[0])

    # SEMANTIC: Track return type by recursively searching all statements
    return_type = collect_return_type(body)

    if name and return_type:
        state.function_return_types[name["value"]] = return_type
    state.symbol_table.pop_scope()
    
    node.add(Node("Params", None, [Node("Param", pname, [], None) for pname in params]))
    node.add(Node("Body", None, body))
    
    return node

def parse_return(state):
    """Parse return statement: reward expr"""
    start = state.expect([(TOKEN_KEYWORD, "reward")], "Expected 'reward'")
    if start is None:
        return Node("Return", None, [], state.current().get("lineno"))
    
    expr = parse_expr(state)
    node = Node("Return", None, [expr], start["lineno"])
    
    # SEMANTIC: Set return type
    if expr.dtype:
        node.dtype = expr.dtype
    
    return node

def parse_try_except(state):
    """Parse try-except: embark: ... gameOver: ... savePoint: ..."""
    start = state.expect([(TOKEN_KEYWORD, "embark")], "Expected 'embark'")
    if start is None:
        return Node("Try", None, [], state.current().get("lineno"))
    
    node = Node("Try", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after embark")
    
    state.symbol_table.push_scope()
    try_body = parse_statement_block(state)
    state.symbol_table.pop_scope()
    
    node.add(Node("TryBlock", None, try_body))

    # Parse except blocks
    while state.match(TOKEN_KEYWORD, "gameOver"):
        state.advance()
        ex = state.advance() if state.match(TOKEN_IDENTIFIER) else None
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after exception type")
        
        state.symbol_table.push_scope()
        except_body = parse_statement_block(state)
        state.symbol_table.pop_scope()
        
        node.add(Node("Except", ex["value"] if ex else None, except_body))

    # Parse finally block
    if state.match(TOKEN_KEYWORD, "savePoint"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after savePoint")
        
        state.symbol_table.push_scope()
        finally_body = parse_statement_block(state)
        state.symbol_table.pop_scope()
        
        node.add(Node("Finally", None, finally_body))
    
    return node

def parse_statement_block(state):
    """Parse an indented block of statements."""
    if not state.match(TOKEN_NEWLINE):
        state.error("Expected NEWLINE before block", state.current().get("lineno"))
    else:
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

def parse_expr(state):
    """Parse expression - top level (logical OR)."""
    return parse_logical_or(state)

def parse_logical_or(state):
    """Parse logical OR expression."""
    left = parse_logical_and(state)
    
    while state.match(TOKEN_OPERATOR, "or"):
        op = state.advance()
        right = parse_logical_and(state)
        
        node = Node("BinaryOp", "or", [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, "or")
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply 'or' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        left = node
    
    return left

def parse_logical_and(state):
    """Parse logical AND expression."""
    left = parse_comparison(state)
    
    while state.match(TOKEN_OPERATOR, "and"):
        op = state.advance()
        right = parse_comparison(state)
        
        node = Node("BinaryOp", "and", [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, "and")
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply 'and' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        left = node
    
    return left

def parse_comparison(state):
    """Parse comparison expression."""
    left = parse_add_expr(state)
    
    while state.current()["type"] in (TOKEN_OPERATOR, TOKEN_PUNCT) and \
          state.current()["value"] in ("==", "!=", "<", ">", "<=", ">="):
        op = state.advance()
        right = parse_add_expr(state)
        
        node = Node("BinaryOp", op["value"], [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, op["value"])
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply '{op['value']}' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        left = node
    
    return left

def parse_add_expr(state):
    """Parse addition/subtraction expression."""
    left = parse_term(state)
    
    while state.match(TOKEN_PUNCT) and state.current()["value"] in ("+", "-"):
        op = state.advance()
        right = parse_term(state)
        
        node = Node("BinaryOp", op["value"], [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, op["value"])
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply '{op['value']}' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        left = node
    
    return left

def parse_term(state):
    #Parse multiplication/division/modulo expression
    left = parse_exponent(state)
    
    while (state.match(TOKEN_PUNCT) and state.current()["value"] in ("*", "/", "%")) or \
          (state.match(TOKEN_OPERATOR) and state.current()["value"] == "//"):
        op = state.advance()
        right = parse_exponent(state)
        
        node = Node("BinaryOp", op["value"], [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, op["value"])
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply '{op['value']}' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        left = node
    
    return left

def parse_exponent(state):
    """Parse exponentiation expression (right-associative)."""
    left = parse_unary(state)
    
    if state.match(TOKEN_OPERATOR, "**"):
        op = state.advance()
        right = parse_exponent(state)
        
        node = Node("BinaryOp", "**", [left, right], op["lineno"])
        
        # SEMANTIC: Type check
        if left.dtype and right.dtype:
            result_type = datatype_check(left.dtype, right.dtype, "**")
            if result_type is None:
                state.semantic_error(
                    f"Type mismatch: cannot apply '**' to {left.dtype} and {right.dtype}",
                    op["lineno"]
                )
            else:
                node.dtype = result_type
        
        return node
    
    return left

def parse_unary(state):
    """Parse unary expression."""
    cur = state.current()
    
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-"):
        op = state.advance()
        operand = parse_unary(state)
        
        node = Node("UnaryOp", op["value"], [operand], op["lineno"])
        
        # SEMANTIC: Type check unary operations
        if operand.dtype:
            if op["value"] == "not":
                if operand.dtype != DATA_TYPE_BOOL:
                    state.semantic_error(
                        f"'not' operator requires boolean, got {operand.dtype}",
                        op["lineno"]
                    )
                else:
                    node.dtype = DATA_TYPE_BOOL
            elif op["value"] in ("+", "-"):
                if operand.dtype not in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
                    state.semantic_error(
                        f"Unary '{op['value']}' requires numeric type, got {operand.dtype}",
                        op["lineno"]
                    )
                else:
                    node.dtype = operand.dtype
        
        return node
    
    return parse_factor(state)

def parse_factor(state):
    #Parse primary expressions: literals, identifiers, calls, attributes
    cur = state.current()
    
    # Literals: numbers, strings, booleans
    if cur["type"] in (TOKEN_NUMBER, TOKEN_STRING, TOKEN_LITERAL):
        tok = state.advance()
        node_type = {
            "NUMBER": "Number",
            "STRING": "String",
            "LITERAL": "Literal"
        }[tok["type"]]
        node = Node(node_type, tok["value"], [], tok["lineno"])
        
        # SEMANTIC: Infer literal type
        if node_type == "Number":
            node.dtype = DATA_TYPE_DOUBLE if '.' in str(tok["value"]) else DATA_TYPE_INT
        elif node_type == "String":
            node.dtype = DATA_TYPE_STRING
        elif node_type == "Literal":
            node.dtype = DATA_TYPE_BOOL
        
        return node
    
    # Data type casting functions
    if cur["type"] == TOKEN_DATATYPE:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        node.dtype = cur["value"]
        state.advance()
        return parse_postfix_ops(state, node)
    
    # Identifiers
    if cur["type"] == TOKEN_IDENTIFIER:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        
        # SEMANTIC: Check if type casting function or variable
        if cur["value"] in (DATA_TYPE_INT, DATA_TYPE_DOUBLE, DATA_TYPE_STRING, DATA_TYPE_BOOL):
            node.dtype = cur["value"]
        else:
            var_info = state.symbol_table.lookup(cur["value"])
            if var_info is None:
                state.semantic_error(f"Undeclared variable '{cur['value']}'", cur["lineno"])
            else:
                node.dtype = var_info.dtype
        
        state.advance()
        return parse_postfix_ops(state, node)
    
    # Parenthesized expression
    if cur["type"] == TOKEN_PUNCT and cur["value"] == "(":
        state.advance()
        expr = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parenthesized expression")
        return expr

    # Unexpected token
    state.error(f"Unexpected expression token: {cur['type']} ({cur['value']})", cur["lineno"])
    state.advance()
    return Node("Empty", None, [], cur.get("lineno", -1))

def parse_postfix_ops(state, node):
    """Parse postfix operations: attribute access and function calls."""
    while True:
        # Attribute access
        if state.match(TOKEN_PUNCT, "."):
            state.advance()
            if state.match(TOKEN_IDENTIFIER):
                attr = state.advance()
                node = Node("Attribute", attr["value"], [node], attr["lineno"])
                node.dtype = None  # Don't track attribute types
            else:
                state.error("Expected identifier after '.'", state.current().get("lineno"))
                break
        
        # Function call
        elif state.match(TOKEN_PUNCT, "("):
            node = parse_call_with_target(state, node)
        
        else:
            break
    
    return node

def parse_call_with_target(state, target_node):
    #Parse function call with target
    lpar = state.expect([(TOKEN_PUNCT, "(")], "Expected '(' for function call")
    args = []
    
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            args.append(parse_expr(state))
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after call arguments")
    
    call_node = Node("Call", None, [target_node] + args, lpar["lineno"] if lpar else target_node.lineno)
    
    # SEMANTIC: Type inference for function calls
    if target_node.type == "Identifier":
        func_name = target_node.value
        
        # Type casting functions
        if func_name in (DATA_TYPE_INT, DATA_TYPE_DOUBLE, DATA_TYPE_STRING, DATA_TYPE_BOOL):
            call_node.dtype = func_name
        # User-defined functions - infer type based on actual arguments
        elif func_name in state.function_bodies:
            arg_types = [arg.dtype for arg in args]
            # Only infer if all argument types are known
            if all(t and t != "unknown" for t in arg_types):
                inferred_type = infer_function_return_type(state, func_name, arg_types)
                call_node.dtype = inferred_type
            else:
                # If we can't infer, check if we have a cached return type
                call_node.dtype = state.function_return_types.get(func_name, "unknown")
        # Known function with cached return type
        elif func_name in state.function_return_types:
            call_node.dtype = state.function_return_types[func_name]
        else:
            # Unknown function
            call_node.dtype = "unknown"
    else:
        call_node.dtype = None
    
    return call_node