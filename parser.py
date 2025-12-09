from scanner import *

DATA_TYPE_INT = "potion"
DATA_TYPE_DOUBLE = "elixir"
DATA_TYPE_STRING = "scroll"
DATA_TYPE_BOOL = "fate"

class Node:
    """
    Attributes:
        type: Node type (e.g., "Assignment", "BinaryOp", "If")
        value: Optional value (e.g., operator symbol, identifier name)
        children: List of child nodes
        lineno: Source line number for error reporting
        dtype: Data type (added for semantic analysis)
    """
    def __init__(self, ntype, value=None, children=None, lineno=None):
        self.type = ntype
        self.value = value
        self.children = children if children is not None else []
        self.lineno = lineno
        self.dtype = None  # For type inference

    def add(self, node):
        """Add a child node."""
        self.children.append(node)

    def pretty(self, indent=0):
        """Generate indented string representation of the ST."""
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
        """Create a new scope (enter block)."""
        self.scopes.append({})
    
    def pop_scope(self):
        """Exit current scope."""
        if len(self.scopes) > 1:
            self.scopes.pop()
    
    def declare(self, name, dtype, line):
        current_scope = self.scopes[-1]
        current_scope[name] = IdentifierInfo(name, dtype, line)
        return current_scope[name]
    
    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

def datatype_check(t1, t2, operator):
    # Allow operations with unknown types (function parameters)
    if t1 == "unknown" or t2 == "unknown":
        if operator in ["+", "-", "*", "/", "//", "%", "**"]:
            return DATA_TYPE_DOUBLE
        elif operator in ["<", ">", "<=", ">=", "==", "!="]:
            return DATA_TYPE_BOOL
        elif operator in ["and", "or"]:
            return DATA_TYPE_BOOL
        return "unknown"

    # String concatenation
    if operator == "+" and t1 == DATA_TYPE_STRING and t2 == DATA_TYPE_STRING:
        return DATA_TYPE_STRING
    
    # String repetition: "hello" * 3 or 3 * "hello"
    if operator == "*":
        if (t1 == DATA_TYPE_STRING and t2 == DATA_TYPE_INT) or \
           (t1 == DATA_TYPE_INT and t2 == DATA_TYPE_STRING):
            return DATA_TYPE_STRING
    
    # Arithmetic operators: +, -, *, /, //, %, **
    if operator in ["+", "-", "*", "/", "//", "%", "**"]:
        if t1 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE) and t2 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
            # If either is double, result is double
            if t1 == DATA_TYPE_DOUBLE or t2 == DATA_TYPE_DOUBLE:
                return DATA_TYPE_DOUBLE
            return DATA_TYPE_INT
        return None  # Invalid
    
    # Comparison operators: <, >, <=, >=
    if operator in ["<", ">", "<=", ">="]:
        if t1 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE) and t2 in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
            return DATA_TYPE_BOOL
        return None  # Invalid
    
    # Equality operators: ==, !=
    if operator in ["==", "!="]:
        if t1 == t2:
            return DATA_TYPE_BOOL
        return None  # Invalid
    
    # Logical operators: and, or
    if operator in ["and", "or"]:
        if t1 == DATA_TYPE_BOOL and t2 == DATA_TYPE_BOOL:
            return DATA_TYPE_BOOL
        return None  # Invalid
    
    # Assignment operator
    if operator == "=":
        return t2  # Type of right side
    
    return None  # Unknown operator or invalid combination

def semantic_analysis(ast_root):
    symbol_table = SymbolTable()
    errors = []
    function_return_types = {}  # Store function return types

    
    def analyze_node(node):
        """Recursively analyze AST nodes and infer types."""
        if node is None:
            return None
        
        node_type = node.type
        
        # Program node
        if node_type == "Program":
            for child in node.children:
                analyze_node(child)
            return None
        
        # Comment
        if node_type == "Comment":
            return None
        
        # Import
        if node_type == "Import":
            # Register imported module names in symbol table
            for child in node.children:
                if child.type == "Module":
                    module_name = child.value
                    symbol_table.declare(module_name, "module", node.lineno)
            return None

        # Assignment: x = expr
        if node_type == "Assignment":
            var_name = node.value
            if not var_name or not node.children:
                return None
            
            # Analyze right-hand side
            rhs_type = analyze_node(node.children[0])
            
            if rhs_type is None:
                errors.append((node.lineno, f"Cannot determine type for assignment to '{var_name}'"))
                return None
            
            # Declare/update variable
            symbol_table.declare(var_name, rhs_type, node.lineno)
            node.dtype = rhs_type
            return rhs_type
        
        # Input: scout("prompt")
        if node_type == "Input":
            node.dtype = DATA_TYPE_STRING
            return DATA_TYPE_STRING
        
        # Output: attack(...)
        if node_type == "Output":
            for child in node.children:
                analyze_node(child)
            return None
        
        # If statement
        if node_type == "If":
            for child in node.children:
                if child.type == "Condition":
                    # Check condition is boolean
                    if child.children:
                        cond_type = analyze_node(child.children[0])
                        if cond_type and cond_type != DATA_TYPE_BOOL:
                            errors.append((node.lineno, f"Condition must be boolean, got {cond_type}"))
                
                elif child.type == "Then":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
                
                elif child.type == "Elif":
                    # Check elif condition
                    for subchild in child.children:
                        if subchild.type == "Condition" and subchild.children:
                            cond_type = analyze_node(subchild.children[0])
                            if cond_type and cond_type != DATA_TYPE_BOOL:
                                errors.append((node.lineno, f"Elif condition must be boolean, got {cond_type}"))
                        elif subchild.type == "Body":
                            symbol_table.push_scope()
                            for stmt in subchild.children:
                                analyze_node(stmt)
                            symbol_table.pop_scope()
                
                elif child.type == "Else":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
            
            return None
        
        # While loop
        if node_type == "While":
            for child in node.children:
                if child.type == "Condition":
                    if child.children:
                        cond_type = analyze_node(child.children[0])
                        if cond_type and cond_type != DATA_TYPE_BOOL:
                            errors.append((node.lineno, f"While condition must be boolean, got {cond_type}"))
                
                elif child.type == "Body":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
            
            return None
        
        # For loop
        if node_type == "For":
            var_name = None
            iter_type = None
            body_stmts = []
            
            for child in node.children:
                if child.type == "Var":
                    var_name = child.value
                elif child.type == "Iter":
                    if child.children:
                        iter_type = analyze_node(child.children[0])
                elif child.type == "Body":
                    body_stmts = child.children
            
            # Create new scope for loop
            symbol_table.push_scope()
            
            # Declare loop variable (type inferred from iterable, default to string)
            if var_name:
                symbol_table.declare(var_name, DATA_TYPE_STRING, node.lineno)
            
            # Analyze body
            for stmt in body_stmts:
                analyze_node(stmt)
            
            symbol_table.pop_scope()
            return None
        
        # Function definition
        # Function definition
        if node_type == "FunctionDef":
            func_name = node.value
            params = []
            body_stmts = []
            return_type = None
            
            for child in node.children:
                if child.type == "Params":
                    for param in child.children:
                        if param.type == "Param":
                            params.append(param.value)
                elif child.type == "Body":
                    body_stmts = child.children
            
            # Declare the function name in the current scope
            if func_name:
                symbol_table.declare(func_name, "function", node.lineno)
            
            # Create new scope for function body
            symbol_table.push_scope()
            
            # Register parameters with unknown type
            for param_name in params:
                symbol_table.declare(param_name, "unknown", node.lineno)
            
            # Analyze body and track return type
            for stmt in body_stmts:
                analyze_node(stmt)
                if stmt.type == "Return" and stmt.dtype:
                    return_type = stmt.dtype
            
            symbol_table.pop_scope()
            
            # Store the function's return type
            if func_name and return_type:
                function_return_types[func_name] = return_type
            
            return None
        
        # Return statement
        if node_type == "Return":
            if node.children:
                return_type = analyze_node(node.children[0])
                node.dtype = return_type
                return return_type
            return None
        
        # Try-except
        if node_type == "Try":
            for child in node.children:
                if child.type == "TryBlock":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
                
                elif child.type == "Except":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
                
                elif child.type == "Finally":
                    symbol_table.push_scope()
                    for stmt in child.children:
                        analyze_node(stmt)
                    symbol_table.pop_scope()
            
            return None
        
        # Continue/Break
        if node_type in ("Continue", "Break"):
            return None
        
        # Expression statement
        if node_type == "ExprStmt":
            if node.children:
                return analyze_node(node.children[0])
            return None
        
        # Binary operation
        if node_type == "BinaryOp":
            if len(node.children) < 2:
                return None
            
            left_type = analyze_node(node.children[0])
            right_type = analyze_node(node.children[1])
            operator = node.value
            
            if left_type is None or right_type is None:
                return None
            
            result_type = datatype_check(left_type, right_type, operator)
            
            if result_type is None:
                errors.append((node.lineno, f"Type mismatch: cannot apply '{operator}' to {left_type} and {right_type}"))
                return None
            
            node.dtype = result_type
            return result_type
        
        # Unary operation
        if node_type == "UnaryOp":
            if not node.children:
                return None
            
            operand_type = analyze_node(node.children[0])
            operator = node.value
            
            if operator == "not":
                if operand_type != DATA_TYPE_BOOL:
                    errors.append((node.lineno, f"'not' operator requires boolean, got {operand_type}"))
                    return None
                node.dtype = DATA_TYPE_BOOL
                return DATA_TYPE_BOOL
            
            elif operator in ("+", "-"):
                if operand_type not in (DATA_TYPE_INT, DATA_TYPE_DOUBLE):
                    errors.append((node.lineno, f"Unary '{operator}' requires numeric type, got {operand_type}"))
                    return None
                node.dtype = operand_type
                return operand_type
            
            return None
        
        # Identifier (variable reference)
        if node_type == "Identifier":
            var_name = node.value
            
            # Check for type casting functions
            if var_name in (DATA_TYPE_INT, DATA_TYPE_DOUBLE, DATA_TYPE_STRING, DATA_TYPE_BOOL):
                # This is a datatype name used as casting function
                node.dtype = var_name
                return var_name
            
            # Look up variable
            info = symbol_table.lookup(var_name)
            if info is None:
                errors.append((node.lineno, f"Undeclared variable '{var_name}'"))
                return None
            
            node.dtype = info.dtype
            return info.dtype
        
        # Literals
        if node_type == "Number":
            # Check if it's a float or int
            if '.' in str(node.value):
                node.dtype = DATA_TYPE_DOUBLE
                return DATA_TYPE_DOUBLE
            else:
                node.dtype = DATA_TYPE_INT
                return DATA_TYPE_INT
        
        if node_type == "String":
            node.dtype = DATA_TYPE_STRING
            return DATA_TYPE_STRING
        
        if node_type == "Literal":
            # true/false
            node.dtype = DATA_TYPE_BOOL
            return DATA_TYPE_BOOL
        
        # Function call
        if node_type == "Call":
            if not node.children:
                return None
            
            # First child is the function/method being called
            func_node = node.children[0]
            func_type = analyze_node(func_node)
            
            # Check if it's a type casting function
            if func_node.type == "Identifier" and func_node.value in (DATA_TYPE_INT, DATA_TYPE_DOUBLE, DATA_TYPE_STRING, DATA_TYPE_BOOL):
                # Type cast: potion("5"), scroll(42), etc.
                cast_type = func_node.value
                
                # Analyze arguments
                for arg in node.children[1:]:
                    analyze_node(arg)
                
                node.dtype = cast_type
                return cast_type
            
            # Regular function call - analyze arguments
            for arg in node.children[1:]:
                analyze_node(arg)
            
            # For user-defined functions, return their tracked return type
            if func_node.type == "Identifier" and func_type == "function":
                func_name = func_node.value
                if func_name in function_return_types:
                    node.dtype = function_return_types[func_name]
                    return function_return_types[func_name]
                else:
                    node.dtype = "unknown"
                    return "unknown"
            
            return None
        
        # Attribute access
        if node_type == "Attribute":
            if node.children:
                analyze_node(node.children[0])
            # We don't track object attributes, return None
            return None
        
        return None
    
    # Start analysis
    analyze_node(ast_root)
    return errors

class ParserState:
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
    state = ParserState(tokens)
    root = Node("Program", lineno=1)
    
    try:
        for s in parse_statement_list(state, stop_on=(TOKEN_EOF,)):
            if s:
                root.add(s)
    except Exception as e:
        state.error(f"Internal parser error: {e}", state.current().get("lineno", -1))
    
    # Perform semantic analysis
    semantic_errors = semantic_analysis(root)
    
    # Combine parse errors and semantic errors
    all_errors = state.errors + semantic_errors
    
    return root, all_errors

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
    start = state.expect([(TOKEN_KEYWORD, "scout")], "Expected 'scout' for input")
    if start is None:
        return Node("Input", None, [], state.current().get("lineno"))
    
    node = Node("Input", None, [], start["lineno"])
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' after 'scout'")
    node.add(parse_expr(state))  # Prompt expression
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after 'scout' argument")
    
    return node


def parse_output_stmt(state):
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
    state.expect([(TOKEN_PUNCT, "(")], "Expected '(' before condition")
    cond = parse_expr(state)
    state.expect([(TOKEN_PUNCT, ")")], "Expected ')' after condition")
    return cond

def parse_if(state):
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
    start = state.expect([(TOKEN_KEYWORD, "reward")], "Expected 'reward' for return")
    if start is None:
        return Node("Return", None, [], state.current().get("lineno"))
    return Node("Return", None, [parse_expr(state)], start["lineno"])

def parse_try_except(state):
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

def parse_expr(state):
    """
    Parse expression - top level (logical OR).
    """
    return parse_logical_or(state)

def parse_logical_or(state):
    """
    Parse logical OR expression.
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
    """
    left = parse_add_expr(state)
    
    while state.current()["type"] in (TOKEN_OPERATOR, TOKEN_PUNCT) and \
          state.current()["value"] in ("==", "!=", "<", ">", "<=", ">="):
        op = state.advance()
        right = parse_add_expr(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_add_expr(state):
    left = parse_term(state)
    
    while state.match(TOKEN_PUNCT) and state.current()["value"] in ("+", "-"):
        op = state.advance()
        right = parse_term(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_term(state):
    left = parse_exponent(state)
    
    while (state.match(TOKEN_PUNCT) and state.current()["value"] in ("*", "/", "%")) or \
          (state.match(TOKEN_OPERATOR) and state.current()["value"] == "//"):
        op = state.advance()
        right = parse_exponent(state)
        left = Node("BinaryOp", op["value"], [left, right], op["lineno"])
    
    return left

def parse_exponent(state):
    left = parse_unary(state)
    
    if state.match(TOKEN_OPERATOR, "**"):
        op = state.advance()
        # Right-associative: parse the rest as another exponent
        right = parse_exponent(state)
        return Node("BinaryOp", "**", [left, right], op["lineno"])
    
    return left

def parse_unary(state):
    cur = state.current()
    
    # Unary operators
    if cur["type"] == TOKEN_OPERATOR and cur["value"] in ("not", "+", "-"):
        op = state.advance()
        return Node("UnaryOp", op["value"], [parse_unary(state)], op["lineno"])
    
    return parse_factor(state)

def parse_factor(state):
    """
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