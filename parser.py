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
        self.panic_mode = False  # Error recovery mode

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
        self.panic_mode = False  # Exit panic mode when successfully consuming
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
        Reports error if no match found but continues parsing.
        
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
        """Record a parse error and enter panic mode."""
        ln = lineno if lineno is not None else self.current().get("lineno", -1)
        self.errors.append((ln, msg))
        self.panic_mode = True

    def synchronize(self):
        """
        Skip tokens until we find a safe synchronization point.
        Used for error recovery to continue parsing after errors.
        """
        if not self.panic_mode:
            return
        
        # Skip until we find a statement boundary
        while not self.match(TOKEN_EOF):
            # Stop at newlines (potential statement start)
            if self.match(TOKEN_NEWLINE):
                self.advance()
                self.panic_mode = False
                return
            
            # Stop at keywords that start statements
            if self.match(TOKEN_KEYWORD):
                if self.current()["value"] in ("summon", "spot", "replay", "farm", 
                                               "quest", "attack", "embark", "reward"):
                    self.panic_mode = False
                    return
            
            # Stop at dedent (end of block)
            if self.match(TOKEN_DEDENT):
                self.panic_mode = False
                return
            
            self.advance()
        
        self.panic_mode = False

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
    - Error recovery via synchronization
    
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
        
        # If we encountered an error, synchronize
        if state.panic_mode:
            state.synchronize()
        
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
    Statement → Comment | KeywordStmt | Assignment | CompoundAssignment 
                | ExprStmt | NEWLINE
    
    Dispatches to appropriate parser based on first token.
    """
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
        # Unknown keyword - create generic node
        tok = state.advance()
        return Node("KeywordStmt", tok["value"], [], tok["lineno"])

    # Data type casting functions (e.g., potion(x), scroll(y))
    if cur["type"] == TOKEN_DATATYPE:
        next_tok = state.peek(1)
        if next_tok["type"] == TOKEN_PUNCT and next_tok["value"] == "(":
            # Treat as function call
            expr = parse_expr(state)
            if expr.type == "Call":
                return Node("ExprStmt", None, [expr], cur["lineno"])
        
        # Invalid: datatype used alone
        state.error(f"Invalid statement: datatype '{cur['value']}' cannot stand alone", cur["lineno"])
        state.advance()
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

    # Unexpected token - report and skip
    state.error(f"Unexpected token: {cur['type']} ({cur['value']})", cur["lineno"])
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
        return Node("Import", None, [], state.current().get("lineno"))
    
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
        return Node("Assignment", None, [], state.current().get("lineno"))
    
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
    
    Example: x += 5  →  x = x + 5
    """
    ident = state.expect([(TOKEN_IDENTIFIER, None)], "Expected identifier in compound assignment")
    if ident is None:
        return Node("Assignment", None, [], state.current().get("lineno"))
    
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
        return Node("Input", None, [], state.current().get("lineno"))
    
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
        return Node("Output", None, [], state.current().get("lineno"))
    
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

def parse_condition(state):
    """
    Parse a condition expression (used by if, while, etc.)
    
    Grammar rule: '(' Expr ')'
    
    Returns:
        Expression node representing the condition
    """
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' before condition")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after condition")
    return cond

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
        return Node("If", None, [], state.current().get("lineno"))
    
    node = Node("If", None, [], start["lineno"])
    
    # Parse condition using shared function
    cond = parse_condition(state)
    state.expect([(TOKEN_PUNCT, ":")], "Expected ':' after if header")
    
    # Parse then block
    then_block = parse_statement_block(state)
    node.add(Node("Condition", None, [cond], cond.lineno if hasattr(cond, 'lineno') else start["lineno"]))
    node.add(Node("Then", None, then_block, start["lineno"]))

    # Parse elif clauses (counter)
    while state.match(TOKEN_KEYWORD, "counter"):
        state.advance()
        ccond = parse_condition(state)
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
        return Node("While", None, [], state.current().get("lineno"))
    
    node = Node("While", None, [], start["lineno"])
    
    # Parse condition using shared function
    cond = parse_condition(state)
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
        return Node("For", None, [], state.current().get("lineno"))
    
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
        return Node("FunctionDef", None, [], state.current().get("lineno"))
    
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
    if start is None:
        return Node("Return", None, [], state.current().get("lineno"))
    return Node("Return", None, [parse_expr(state)], start["lineno"])

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
        return Node("Try", None, [], state.current().get("lineno"))
    
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
    else:
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

# ==============================================================================
# EXPRESSION PARSING - Traditional Factor/Term Approach
# ==============================================================================

def parse_expr(state):
    """
    Parse expression - top level (logical OR).
    
    Grammar rule: Expr → LogicalOrExpr
    """
    return parse_logical_or(state)

def parse_logical_or(state):
    """
    Parse logical OR expression.
    
    Grammar rule: LogicalOrExpr → LogicalAndExpr ('or' LogicalAndExpr)*
    """
    left = parse_logical_and(state)
    
    while state.match(TOKEN_OPERATOR, "or"):
        op = state.advance()
        right = parse_logical_and(state)
        left = Node("BinaryOp", "or", [left, right], op["lineno"])
    
    return left

def parse_logical_and(state):
    """
    Parse logical AND expression.
    
    Grammar rule: LogicalAndExpr → ComparisonExpr ('and' ComparisonExpr)*
    """
    left = parse_comparison(state)
    
    while state.match(TOKEN_OPERATOR, "and"):
        op = state.advance()
        right = parse_comparison(state)
        left = Node("BinaryOp", "and", [left, right], op["lineno"])
    
    return left

def parse_comparison(state):
    """
    Parse comparison expression.
    
    Grammar rule: ComparisonExpr → AddExpr (CompOp AddExpr)*
    CompOp → '==' | '!=' | '<' | '>' | '<=' | '>='
    """
    left = parse_add_expr(state)
    
    while state.current()["type"] in (TOKEN_OPERATOR, TOKEN_PUNCT) and \
          state.current()["value"] in ("==", "!=", "<", ">", "<=", ">="):
        op = state.advance()
        right = parse_add_expr(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_add_expr(state):
    """
    Parse addition/subtraction expression (traditional "expression" level).
    
    Grammar rule: AddExpr → Term (('+' | '-') Term)*
    """
    left = parse_term(state)
    
    while state.match(TOKEN_PUNCT) and state.current()["value"] in ("+", "-"):
        op = state.advance()
        right = parse_term(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_term(state):
    """
    Parse multiplication/division/modulo expression (traditional "term" level).
    
    Grammar rule: Term → Exponent (('*' | '/' | '//' | '%') Exponent)*
    """
    left = parse_exponent(state)
    
    while (state.match(TOKEN_PUNCT) and state.current()["value"] in ("*", "/", "%")) or \
          (state.match(TOKEN_OPERATOR) and state.current()["value"] == "//"):
        op = state.advance()
        right = parse_exponent(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_exponent(state):
    """
    Parse exponentiation expression.
    
    Grammar rule: Exponent → Unary ('**' Unary)*
    
    Note: Exponentiation is right-associative
    """
    left = parse_unary(state)
    
    if state.match(TOKEN_OPERATOR, "**"):
        op = state.advance()
        # Right-associative: parse the rest as another exponent
        right = parse_exponent(state)
        return Node("BinaryOp", "**", [left, right], op["lineno"])
    
    return left

def parse_unary(state):
    """
    Parse unary expression.
    
    Grammar rule: Unary → UnaryOp Unary | Factor
    UnaryOp → 'not' | '+' | '-'
    """
    cur = state.current()
    
    # Unary operators
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-"):
        op = state.advance()
        return Node("UnaryOp", op["value"], [parse_unary(state)], op["lineno"])
    
    return parse_factor(state)

def parse_factor(state):
    """
    Parse factor (primary expressions with postfix operations).
    
    Grammar rule: Factor → Primary (('.' Identifier) | ('(' ArgList? ')'))*
    
    Handles:
    - Literals: 123, 3.14, "hello", true, false
    - Identifiers: variable names
    - Attribute access: obj.attr.subattr
    - Function calls: func(arg1, arg2)
    - Casting functions: potion(x), scroll(y)
    - Parenthesized expressions: (x + y)
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
        node = Node(node_type, tok["value"], [], tok["lineno"])
        return node
    
    # Data type casting functions: potion(x), elixir(y), fate(z), scroll(w)
    if cur["type"] == TOKEN_DATATYPE:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        state.advance()
        
        # Handle attribute access and function calls
        return parse_postfix_ops(state, node)
    
    # Identifiers (with possible attribute access or function calls)
    if cur["type"] == TOKEN_IDENTIFIER:
        node = Node("Identifier", cur["value"], [], cur["lineno"])
        state.advance()
        
        # Handle attribute access and function calls
        return parse_postfix_ops(state, node)
    
    # Parenthesized expression: (expr)
    if cur["type"] == TOKEN_PUNCT and cur["value"] == "(":
        state.advance()
        expr = parse_expr(state)
        state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after parenthesized expression")
        return expr

    # Unexpected token in expression
    state.error(f"Unexpected expression token: {cur['type']} ({cur['value']})", cur["lineno"])
    state.advance()
    return Node("Empty", None, [], cur.get("lineno", -1))


def parse_postfix_ops(state, node):
    """
    Parse postfix operations (attribute access and function calls).
    
    Grammar: ('.' Identifier | '(' ArgList? ')')*
    
    Args:
        state: Parser state
        node: Base node to apply operations to
    
    Returns:
        Node with postfix operations applied
    """
    while True:
        # Attribute access: obj.attr
        if state.match(TOKEN_PUNCT, "."):
            state.advance()
            if state.match(TOKEN_IDENTIFIER):
                attr = state.advance()
                node = Node("Attribute", attr["value"], [node], attr["lineno"])
            else:
                state.error("Expected identifier after '.'", state.current().get("lineno"))
                break
        
        # Function call: func(args)
        elif state.match(TOKEN_PUNCT, "("):
            node = parse_call_with_target(state, node)
        
        else:
            break
    
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
        potion(42)
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