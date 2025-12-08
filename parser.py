from scanner import *

class Node:
    """
    Attributes:
        type: Node type (e.g., "Assignment", "BinaryOp", "If")
        value: Optional value (e.g., operator symbol, identifier name)
        children: List of child nodes
        lineno: Source line number for error reporting
    """
    def __init__(self, ntype, value=None, children=None, lineno=None):
        self.type = ntype
        self.value = value
        self.children = children if children is not None else []
        self.lineno = lineno

    def add(self, node):
        """Add a child node."""
        self.children.append(node)

    def pretty(self, indent=0):
        """Generate indented string representation of the ST."""
        pad = "  " * indent
        val = f": {self.value}" if self.value is not None else ""
        lineinfo = f" (line {self.lineno})" if self.lineno else ""
        out = f"{pad}{self.type}{val}{lineinfo}\n"
        for c in self.children:
            out += c.pretty(indent + 1)
        return out

class ParserState:
    """
    Manages parser state including token stream position and errors.
    """
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0  # Current token index
        self.errors = []  # List of (line_number, error_message) tuples

    def current(self):
        """Get the current token without advancing."""
        return self.tokens[self.i] if self.i < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def peek(self, offset=1):
        """Look ahead at a token without advancing."""
        j = self.i + offset
        return self.tokens[j] if j < len(self.tokens) else make_token(TOKEN_EOF, "EOF", -1, -1)

    def advance(self):
        """Consume and return the current token."""
        tok = self.current()
        self.i += 1
        return tok

    def match(self, ttype=None, value=None):
        """
        Check if current token matches criteria without advancing.
        
        Args:
            ttype: Expected token type (or None for any)
            value: Expected token value (or None for any)
        
        Returns:
            True if token matches
        """
        cur = self.current()
        return (ttype is None or cur["type"] == ttype) and \
               (value is None or cur["value"] == value)

    def expect(self, expected_pairs, msg=None):
        """
        Consume a token if it matches expected type/value pairs.
        Reports error if no match found.
        
        Args:
            expected_pairs: List of (type, value) tuples to match
            msg: Custom error message
        
        Returns:
            The consumed token or None on error
        """
        cur = self.current()
        for (t, v) in expected_pairs:
            if cur["type"] == t and (v is None or cur["value"] == v):
                return self.advance()
        
        self.error(msg or f"Expected {expected_pairs}, got {cur['type']}({cur['value']})", cur["lineno"])
        return None

    def error(self, msg, lineno=None):
        """Record a parse error."""
        ln = lineno if lineno is not None else self.current().get("lineno", -1)
        self.errors.append((ln, msg))

def parse(tokens):
    """
    Parse a token stream into an ST.
    
    Grammar rule: Program → Statement* EOF
    
    Args:
        tokens: List of token dictionaries from scanner
    
    Returns:
        Tuple of (root_node, error_list)
    """
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
    """
    Parse a sequence of statements until a stopping token.
    
    Grammar rule: Statement* (until stop condition)
    
    Handles:
    - Skipping blank lines (NEWLINE tokens)
    - Stopping at EOF, DEDENT, or other specified tokens
    
    Args:
        state: Parser state
        stop_on: Tuple of token types that end the statement list
    
    Returns:
        List of statement nodes
    """
    stmts = []
    
    # Skip leading blank lines
    while state.match(TOKEN_NEWLINE):
        state.advance()
    
    # Parse statements until stopping condition
    while not (state.match(TOKEN_EOF) or 
               state.match(TOKEN_DEDENT) or 
               state.current()["type"] in stop_on):
        st = parse_statement(state)
        if st:
            stmts.append(st)
        
        # Skip trailing blank lines
        while state.match(TOKEN_NEWLINE):
            state.advance()
        
        if state.match(TOKEN_EOF):
            break
    
    return stmts

# Keyword → Parser function mapping
KEYWORD_PARSERS = {
    "summon": lambda s: parse_import(s),           # import
    "spot": lambda s: parse_if(s),                 # if
    "replay": lambda s: parse_while(s),            # while
    "farm": lambda s: parse_for(s),                # for
    "quest": lambda s: parse_function_def(s),      # function def
    "attack": lambda s: parse_output_stmt(s),      # print/output
    "scout": lambda s: parse_input_stmt(s),        # input
    "embark": lambda s: parse_try_except(s),       # try-except
    "reward": lambda s: parse_return(s),           # return
    "skipEncounter": lambda s: Node("Continue", None, [], s.advance()["lineno"]),
    "escapeDungeon": lambda s: Node("Break", None, [], s.advance()["lineno"]),
}

def parse_statement(state):
    """
    Parse a single statement.
    
    Grammar rule:
    Statement → Comment | String | KeywordStmt | Assignment | CompoundAssignment 
                | ExprStmt | NEWLINE
    
    Dispatches to appropriate parser based on first token.
    """
    cur = state.current()
    
    # Comment
    if cur["type"] == TOKEN_COMMENT:
        tok = state.advance()
        return Node("Comment", tok["value"], [], tok["lineno"])
    
    # String literal as statement (docstring/multi-line comment)
    if cur["type"] == TOKEN_STRING:
        tok = state.advance()
        return Node("Docstring", tok["value"], [], tok["lineno"])

    # Keyword statements
    if cur["type"] == TOKEN_KEYWORD:
        parser = KEYWORD_PARSERS.get(cur["value"])
        if parser:
            return parser(state)
        # Unknown keyword - create generic node
        tok = state.advance()
        return Node("KeywordStmt", tok["value"], [], tok["lineno"])

    # Data type casting calls as statements (e.g., potion("123"))
    if cur["type"] == TOKEN_DATATYPE:
        expr = parse_expr(state)
        if expr.type == "Cast":
            return Node("ExprStmt", None, [expr], cur["lineno"])
        state.error(f"Invalid casting statement", cur["lineno"])
        return None

    # Identifier-based statements (assignment, compound assignment, or expression)
    if cur["type"] == TOKEN_IDENTIFIER:
        next_tok = state.peek(1)
        
        # Simple assignment: x = ...
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "=":
            return parse_assignment(state)
        
        # Compound assignment: x += ...
        elif next_tok["type"] == TOKEN_OPERATOR and \
             next_tok["value"] in ("+=", "-=", "*=", "/=", "%=", "**="):
            return parse_compound_assignment(state)
        
        # Expression statement (function call or method call)
        elif next_tok["type"] == TOKEN_PUNCT and next_tok["value"] in ("(", "."):
            expr = parse_expr(state)
            if expr.type == "Call":
                return Node("ExprStmt", None, [expr], cur["lineno"])
            # Bare expressions (not calls) are not valid statements
            state.error(f"Invalid statement: '{cur['value']}' expression has no effect", cur["lineno"])
            return None
        
        else:
            # Bare identifier with no operation
            state.error(f"Invalid statement: bare identifier '{cur['value']}' cannot stand alone", cur["lineno"])
            state.advance()
            return None

    # Empty statement (just newline)
    if cur["type"] in (TOKEN_NEWLINE, TOKEN_EOF, TOKEN_DEDENT):
        return None

    # Unexpected token - skip to next line
    state.error(f"Unexpected token: {cur['type']} ({cur['value']})", cur["lineno"])
    while not state.match(TOKEN_NEWLINE) and \
          not state.match(TOKEN_EOF) and \
          not state.match(TOKEN_DEDENT):
        state.advance()
    return None

def parse_import(state):
    """
    Parse import statement.
    
    Grammar rule: ImportStmt → 'summon' Identifier (',' Identifier)*
    
    Example: summon math, random, sys
    """
    tok = state.expect([(TOKEN_KEYWORD, "summon")], "Expected 'summon' for import")
    if tok is None:
        return None
    
    node = Node("Import", None, [], tok["lineno"])
    
    if not state.match(TOKEN_IDENTIFIER):
        state.error("Expected module name after 'summon'", state.current().get("lineno"))
        return node
    
    # Parse comma-separated list of module names
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
    """
    Parse simple assignment.
    
    Grammar rule: Assignment → Identifier '=' (InputStmt | Expr)
    
    Examples:
        x = 5
        name = scout("Enter name: ")
    """
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in assignment")
    if ident is None:
        return None
    
    state.expect([(TOKEN_PUNCT, "=")], "Expected '=' in assignment")
    
    # Special case: assignment from input
    if state.match(TOKEN_KEYWORD, "scout"):
        input_node = parse_input_stmt(state)
        return Node("Assignment", ident["value"], [input_node], ident["lineno"])
    
    # Regular expression assignment
    expr = parse_expr(state)
    return Node("Assignment", ident["value"], [expr], ident["lineno"])


def parse_compound_assignment(state):
    """
    Parse compound assignment (sugar for x = x op y).
    
    Grammar rule: CompoundAssignment → Identifier CompoundOp Expr
    CompoundOp → '+=' | '-=' | '*=' | '/=' | '%=' | '**='
    
    Note: '//' is floor division, but '//=' is not defined as compound operator
    
    Example: x += 5  →  x = x + 5
    """
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in compound assignment")
    if ident is None:
        return None
    
    op_tok = state.expect([(TOKEN_OPERATOR, None)], "Expected compound operator")
    if op_tok is None or op_tok["value"] not in ("+=", "-=", "*=", "/=", "%=", "**="):
        state.error("Expected +=, -=, *=, /=, %=, or **=", state.current().get("lineno"))
        return Node("Assignment", ident["value"], [], ident["lineno"])
    
    # Parse right-hand side
    expr = parse_expr(state)
    
    # Desugar: x += y becomes x = x + y
    base_op = op_tok["value"][:-1]  # Strip '=' to get base operator
    var_node = Node("Identifier", ident["value"], [], ident["lineno"])
    binop = Node("BinaryOp", base_op, [var_node, expr], op_tok["lineno"])
    
    return Node("Assignment", ident["value"], [binop], ident["lineno"])

def parse_input_stmt(state):
    """
    Parse input statement.
    
    Grammar rule: InputStmt → 'scout' '(' Expr ')'
    
    Example: scout("Enter your name: ")
    """
    start = state.expect([(TOKEN_KEYWORD, "scout")], "Expected 'scout' for input")
    if start is None:
        return None
    
    node = Node("Input", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'scout'")
    node.add(parse_expr(state))  # Prompt expression
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after 'scout' argument")
    
    return node


def parse_output_stmt(state):
    """
    Parse output/print statement.
    
    Grammar rule: OutputStmt → 'attack' '(' (Expr (',' Expr)*)? ')'
    
    Example: attack("Hello", name, "!")
    """
    start = state.expect([(TOKEN_KEYWORD, "attack")], "Expected 'attack' for output")
    if start is None:
        return None
    
    node = Node("Output", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'attack'")
    
    # Parse comma-separated arguments
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            node.add(parse_expr(state))
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after attack arguments")
    return node

def parse_if(state):
    """
    Parse if-elif-else statement.
    
    Grammar rule:
    IfStmt → 'spot' '(' Expr ')' ':' Block
             ('counter' '(' Expr ')' ':' Block)*
             ('dodge' ':' Block)?
    
    Example:
        spot (x > 0):
            attack("positive")
        counter (x < 0):
            attack("negative")
        dodge:
            attack("zero")
    """
    start = state.expect([(TOKEN_KEYWORD, "spot")], "Expected 'spot' for if")
    if start is None:
        return None
    
    node = Node("If", None, [], start["lineno"])
    
    # Parse condition
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'spot'")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after if condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after if header")
    
    # Parse then block
    then_block = parse_statement_block(state)
    node.add(Node("Condition", None, [cond], cond.lineno if hasattr(cond, 'lineno') else start["lineno"]))
    node.add(Node("Then", None, then_block, start["lineno"]))

    # Parse elif clauses (counter)
    while state.match(TOKEN_KEYWORD, "counter"):
        state.advance()
        state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'counter'")
        ccond = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after counter condition")
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after counter header")
        cbody = parse_statement_block(state)
        
        node.add(Node("Elif", None, [
            Node("Condition", None, [ccond]),
            Node("Body", None, cbody)
        ], state.current().get("lineno")))

    # Parse else clause (dodge)
    if state.match(TOKEN_KEYWORD, "dodge"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after 'dodge'")
        node.add(Node("Else", None, parse_statement_block(state), state.current().get("lineno")))
    
    return node

def parse_while(state):
    """
    Parse while loop.
    
    Grammar rule: WhileStmt → 'replay' '(' Expr ')' ':' Block
    
    Example:
        replay (x > 0):
            x -= 1
    """
    start = state.expect([(TOKEN_KEYWORD, "replay")], "Expected 'replay' for while")
    if start is None:
        return None
    
    node = Node("While", None, [], start["lineno"])
    
    # Parse condition
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'replay'")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after while condition")
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after while header")
    
    # Parse body
    node.add(Node("Condition", None, [cond]))
    node.add(Node("Body", None, parse_statement_block(state)))
    
    return node


def parse_for(state):
    """
    Parse for loop.
    
    Grammar rule: ForStmt → 'farm' Identifier 'in' Expr ':' Block
    
    Example:
        farm item in items:
            attack(item)
    """
    start = state.expect([(TOKEN_KEYWORD, "farm")], "Expected 'farm' for for-loop")
    if start is None:
        return None
    
    node = Node("For", None, [], start["lineno"])
    
    # Parse loop variable
    var = state.expect([(TOKEN_IDENTIFIER, None)], "Expected loop variable")
    if var:
        node.add(Node("Var", var["value"], [], var["lineno"]))
    
    # Parse 'in' keyword (treated as identifier)
    in_tok = state.current()
    if in_tok["type"] == TOKEN_IDENTIFIER and in_tok["value"] == "in":
        state.advance()
    else:
        state.error("Expected 'in' in for loop", state.current().get("lineno"))
    
    # Parse iterable expression
    node.add(Node("Iter", None, [parse_expr(state)]))
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after for header")
    
    # Parse body
    node.add(Node("Body", None, parse_statement_block(state)))
    
    return node


def parse_function_def(state):
    """
    Parse function definition.
    
    Grammar rule: FunctionDef → 'quest' Identifier '(' ParamList? ')' ':' Block
    ParamList → Identifier (',' Identifier)*
    
    Example:
        quest greet(name, age):
            attack("Hello", name)
    """
    start = state.expect([(TOKEN_KEYWORD, "quest")], "Expected 'quest' for function def")
    if start is None:
        return None
    
    # Function name
    name = state.expect([(TOKEN_IDENTIFIER, None)], "Expected function name")
    node = Node("FunctionDef", name["value"] if name else None, [], start["lineno"])
    
    # Parse parameters
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
    
    # Add params and body to ST
    node.add(Node("Params", None, [Node("Param", pname, [], None) for pname in params]))
    node.add(Node("Body", None, parse_statement_block(state)))
    
    return node

def parse_return(state):
    """
    Parse return statement.
    
    Grammar rule: Return → 'reward' Expr
    
    Example: reward x + 5
    """
    start = state.expect([(TOKEN_KEYWORD, "reward")], "Expected 'reward' for return")
    return Node("Return", None, [parse_expr(state)], start["lineno"]) if start else None

def parse_try_except(state):
    """
    Parse try-except-finally statement.
    
    Grammar rule:
    TryExcept → 'embark' ':' Block
                ('gameOver' Identifier? ':' Block)*
                ('savePoint' ':' Block)?
    
    Example:
        embark:
            risky_operation()
        gameOver ValueError:
            attack("Invalid value")
        savePoint:
            cleanup()
    """
    start = state.expect([(TOKEN_KEYWORD, "embark")], "Expected 'embark' for try")
    if start is None:
        return None
    
    node = Node("Try", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after embark")
    node.add(Node("TryBlock", None, parse_statement_block(state)))

    # Parse except blocks (gameOver)
    while state.match(TOKEN_KEYWORD, "gameOver"):
        state.advance()
        # Optional exception type
        ex = state.advance() if state.match(TOKEN_IDENTIFIER) else None
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after exception type")
        node.add(Node("Except", ex["value"] if ex else None, parse_statement_block(state)))

    # Parse finally block (savePoint)
    if state.match(TOKEN_KEYWORD, "savePoint"):
        state.advance()
        state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after savePoint")
        node.add(Node("Finally", None, parse_statement_block(state)))
    
    return node

def parse_statement_block(state):
    """
    Parse an indented block of statements.
    
    Grammar rule: Block → NEWLINE INDENT Statement+ DEDENT
    
    Used for function bodies, loop bodies, if-blocks, etc.
    """
    # Expect newline before indent
    if not state.match(TOKEN_NEWLINE):
        state.error("Expected NEWLINE before block", state.current().get("lineno"))
    state.advance()
    
    # Expect indent
    if not state.match(TOKEN_INDENT):
        state.error("Expected INDENT to start block", state.current().get("lineno"))
    if state.match(TOKEN_INDENT):
        state.advance()
    
    # Parse statements in block
    stmts = parse_statement_list(state, stop_on=(TOKEN_DEDENT, TOKEN_EOF))
    
    # Expect dedent to close block
    if not state.match(TOKEN_DEDENT):
        state.error("Expected DEDENT after block", state.current().get("lineno"))
    else:
        state.advance()
    
    return stmts

# Operator precedence table (lower number = lower precedence)
_PRECEDENCE = {
    "or": 1,      # logical OR
    "and": 2,     # logical AND
    "not": 3,     # logical NOT (unary)
    "==": 4, "!=": 4, "<": 4, ">": 4, "<=": 4, ">=": 4,  # comparison
    "+": 5, "-": 5,                                       # addition/subtraction
    "*": 6, "/": 6, "//": 6, "%": 6,                     # multiplication/division/modulo
    "**": 7,                                              # exponentiation
}

def get_precedence(tok):
    """
    Get operator precedence from token.
    
    Returns:
        Integer precedence level, or -1 if not an operator
    """
    if tok and tok["type"] in (TOKEN_OPERATOR, TOKEN_PUNCT):
        return _PRECEDENCE.get(tok["value"], -1)
    return -1


def parse_expr(state):
    """
    Parse an expression using precedence climbing.
    
    Grammar rule: Expr → BinaryExpr
    
    Entry point for all expression parsing.
    """
    return parse_binop(state, 0)


def parse_binop(state, min_prec):
    """
    Parse binary operations with precedence climbing algorithm.
    
    Grammar rule: BinaryExpr → UnaryExpr (BinOp UnaryExpr)*
    
    This implements operator precedence without recursion per precedence level.
    
    Args:
        state: Parser state
        min_prec: Minimum precedence to parse at this level
    
    Returns:
        Expression ST node
    """
    left = parse_unary_or_primary(state)
    
    # Climb precedence levels
    while get_precedence(state.current()) >= min_prec:
        op = state.advance()
        # Parse right side with higher precedence
        right = parse_binop(state, get_precedence(op) + 1)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left


def parse_unary_or_primary(state):
    """
    Parse unary expressions or primary expressions.
    
    Grammar rule: UnaryExpr → UnaryOp UnaryExpr | PrimaryExpr
    UnaryOp → 'not' | '+' | '-' | '!' | '~'
    
    Returns:
        Expression ST node
    """
    cur = state.current()
    
    # Unary operators
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-", "!", "~"):
        op = state.advance()
        return Node("UnaryOp", op["value"], [parse_unary_or_primary(state)], op["lineno"])
    
    return parse_primary(state)

def parse_primary(state):
    """
    Parse primary expressions (literals, identifiers, calls, attributes, grouping, casting).
    
    Grammar rule:
    PrimaryExpr → Number | String | Literal | Identifier | CastingCall | Call | Attribute | '(' Expr ')'
    
    Handles:
    - Literals: 123, 3.14, "hello", 'hello', '''multi-line''', true, false
    - Identifiers: variable names
    - Attribute access: obj.attr.subattr
    - Function calls: func(arg1, arg2)
    - Casting calls: potion(x), elixir(y), scroll(z), fate(w)
    - Parenthesized expressions: (x + y)
    
    Returns:
        Expression ST node
    """
    cur = state.current()
    
    # Literals: numbers, strings, booleans
    if cur["type"] in (TOKEN_NUMBER, TOKEN_STRING, TOKEN_LITERAL):
        tok = state.advance()
        node_type = {
            "NUMBER": "Number",
            "STRING": "String",
            "LITERAL": "Literal"
        }[tok["type"]]
        return Node(node_type, tok["value"], [], tok["lineno"])
    
    # Data type casting: potion(), elixir(), scroll(), fate()
    if cur["type"] == TOKEN_DATATYPE:
        return parse_casting_call(state)
    
    # Identifiers (with possible attribute access or function calls)
    if cur["type"] == TOKEN_IDENTIFIER:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        state.advance()
        
        # Handle attribute access: obj.attr.subattr...
        while state.match(TOKEN_PUNCT, "."):
            state.advance()
            if state.match(TOKEN_IDENTIFIER):
                attr = state.advance()
                node = Node("Attribute", attr["value"], [node], attr["lineno"])
            else:
                state.error("Expected identifier after '.'", state.current().get("lineno"))
                break
        
        # Handle function call: func(args)
        if state.match(TOKEN_PUNCT, "("):
            return parse_call_with_target(state, node)
        
        return node
    
    # Parenthesized expression: (expr)
    if cur["type"] == TOKEN_PUNCT and cur["value"] == "(":
        state.advance()
        expr = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parenthesized expression")
        return expr

    # Unexpected token in expression
    state.error(f"Unexpected expression token: {cur['type']} ({cur['value']})", cur["lineno"])
    state.advance()
    return Node("Empty")


def parse_casting_call(state):
    """
    Parse casting function call using data types.
    
    Grammar rule: CastingCall → DataType '(' Expr ')'
    DataType → 'potion' | 'elixir' | 'scroll' | 'fate'
    
    Equivalence:
        potion(x)  → int(x)    - converts to integer
        elixir(x)  → float(x)  - converts to floating point
        scroll(x)  → str(x)    - converts to string
        fate(x)    → bool(x)   - converts to boolean
    
    Examples:
        potion("123")     → int("123")     = 123
        elixir("3.14")    → float("3.14")  = 3.14
        scroll(42)        → str(42)        = "42"
        fate(1)           → bool(1)        = true
    
    Args:
        state: Parser state
    
    Returns:
        Cast ST node with data type and argument
    """
    cast_tok = state.expect([(TOKEN_DATATYPE, None)], "Expected data type for casting")
    if cast_tok is None:
        return None
    
    node = Node("Cast", cast_tok["value"], [], cast_tok["lineno"])
    
    # Parse argument
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after data type")
    node.add(parse_expr(state))
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after casting argument")
    
    return node


def parse_call_with_target(state, target_node):
    """
    Parse function call with a known target expression.
    
    Grammar rule: Call → PrimaryExpr '(' ArgList? ')'
    ArgList → Expr (',' Expr)*
    
    Args:
        state: Parser state
        target_node: ST node for the function being called
    
    Returns:
        Call ST node with target and arguments as children
    
    Example:
        func(1, 2, 3)
        obj.method(x, y)
    """
    lpar = state.expect([(TOKEN_PUNCT, "(")], "Expected '(' for function call")
    args = []
    
    # Parse comma-separated arguments
    if not state.match(TOKEN_PUNCT, ")"):
        while True:
            args.append(parse_expr(state))
            if not state.match(TOKEN_PUNCT, ","):
                break
            state.advance()
    
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after call arguments")
    
    # Return Call node with target as first child, followed by arguments
    return Node("Call", None, [target_node] + args, lpar["lineno"] if lpar else target_node.lineno)