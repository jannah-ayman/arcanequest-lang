import re

# Keywords: Core language commands
KEYWORDS = {
    "summon",          # import statement
    "quest",           # function definition
    "reward",          # return statement
    "attack",          # output/print
    "scout",           # input
    "spot",            # if statement
    "dodge",           # else
    "counter",         # elif
    "replay",          # while loop
    "farm",            # for loop
    "guild",           # class definition
    "embark",          # try block
    "gameOver",        # except block
    "savePoint",       # finally block
    "skipEncounter",   # continue
    "escapeDungeon",   # break
}

# Single-character punctuation and operators
SINGLE_CHAR_PUNCT = {
    "(", ")", "{", "}", "[", "]",  # delimiters
    ":", ",", ".",                  # separators
    "+", "-", "*", "/", "%",        # arithmetic
    "<", ">", "=",                  # comparison/assignment
}

# Data types (can also be used as casting functions)
DATATYPES = {"potion", "elixir", "fate", "scroll"}

# Built-in boolean literals
BUILTIN_LITERALS = {"true", "false"}

# Word-based operators
OPERATORS = {"and", "or", "not"}

# Multi-character operators (order matters for longest-match)
MULTI_CHAR_OPS = {
    "**",   # exponentiation
    "<=", ">=", "==", "!=",  # comparison
    "+=", "-=", "*=", "/=", "%=",  # compound assignment
    "//",   # floor division (comment in tokenizer)
}

# Token type constants
TOKEN_EOF = "EOF"
TOKEN_NEWLINE = "NEWLINE"
TOKEN_INDENT = "INDENT"
TOKEN_DEDENT = "DEDENT"
TOKEN_COMMENT = "COMMENT"
TOKEN_KEYWORD = "KEYWORD"
TOKEN_DATATYPE = "DATATYPE"
TOKEN_LITERAL = "LITERAL"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_NUMBER = "NUMBER"
TOKEN_STRING = "STRING"
TOKEN_OPERATOR = "OPERATOR"
TOKEN_PUNCT = "PUNCT"
TOKEN_UNKNOWN = "UNKNOWN"

# REGEX PATTERNS
_RE_NUMBER = re.compile(r"^\d+(?:\.\d+)?")  
_RE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*") 
_RE_STRING_DOUBLE = re.compile(r'^"(?:[^"\\]|\\.)*"') 
_RE_STRING_SINGLE = re.compile(r"^'(?:[^'\\]|\\.)*'") 
_RE_WS = re.compile(r"^[ \t]+") 


# HELPER FUNCTIONS
def make_token(token_type, value, line_number, column):
    return {
        "type": token_type,
        "value": value,
        "lineno": line_number,
        "col": column
    }

# MAIN SCANNER FUNCTION
def scan_source(source_text):
    lines = source_text.splitlines()
    tokens = []
    indent_stack = [0]  # Track indentation levels
    indent_unit = None  # First indent determines the standard (e.g., 4 spaces)
    line_no = 0

    for raw_line in lines:
        line_no += 1
        line = raw_line.rstrip("\n\r")

        # Empty lines produce NEWLINE token only
        if line.strip() == "":
            tokens.append(make_token(TOKEN_NEWLINE, "", line_no, 0))
            continue

        # Calculate leading whitespace (tabs = 4 spaces)
        ws_match = _RE_WS.match(line)
        leading_ws = ws_match.group(0) if ws_match else ""
        indent_len = len(leading_ws.replace("\t", "    "))
        stripped = line[len(leading_ws):]

        # INDENTATION TRACKING
        current_indent = indent_stack[-1]
        
        if indent_len > current_indent:
            # Increase in indentation
            indent_increase = indent_len - current_indent
            
            # Set indent unit on first indent
            if indent_unit is None:
                indent_unit = indent_increase
            
            # Check for consistent indentation
            if indent_increase % indent_unit != 0:
                tokens.append(make_token(
                    TOKEN_UNKNOWN,
                    f"IndentationError: inconsistent indent (expected multiple of {indent_unit} spaces)",
                    line_no,
                    0
                ))
            
            indent_stack.append(indent_len)
            tokens.append(make_token(TOKEN_INDENT, indent_len, line_no, 0))
        
        elif indent_len < current_indent:
            # Decrease in indentation - may require multiple DEDENTs
            while indent_len < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(make_token(TOKEN_DEDENT, "", line_no, 0))
            
            # Check if dedent matches a previous level
            if indent_len != indent_stack[-1]:
                tokens.append(make_token(
                    TOKEN_UNKNOWN,
                    f"IndentationError: unindent does not match any outer indentation level",
                    line_no,
                    0
                ))

        # COMMENT DETECTION
        col = len(leading_ws)
        comment_idx = stripped.find("-->")
        content = stripped[:comment_idx] if comment_idx != -1 else stripped
        comment_text = stripped[comment_idx + 3:].strip() if comment_idx != -1 else None

        # TOKENIZE LINE CONTENT
        s = content
        while s:
            # Skip whitespace
            if s[0].isspace():
                ws_m = _RE_WS.match(s)
                span = len(ws_m.group(0)) if ws_m else 1
                col += span
                s = s[span:]
                continue

            # Try multi-character operators (longest match first)
            matched = False
            for op in sorted(MULTI_CHAR_OPS, key=lambda x: -len(x)):
                if s.startswith(op):
                    tokens.append(make_token(TOKEN_OPERATOR, op, line_no, col))
                    col += len(op)
                    s = s[len(op):]
                    matched = True
                    break
            if matched:
                continue

            # Single-character punctuation
            if s[0] in SINGLE_CHAR_PUNCT:
                tokens.append(make_token(TOKEN_PUNCT, s[0], line_no, col))
                col += 1
                s = s[1:]
                continue

            # String literals - try both double and single quotes
            m = _RE_STRING_DOUBLE.match(s) or _RE_STRING_SINGLE.match(s)
            if m:
                lit = m.group(0)
                tokens.append(make_token(TOKEN_STRING, lit, line_no, col))
                col += len(lit)
                s = s[len(lit):]
                continue

            # Number literals
            m = _RE_NUMBER.match(s)
            if m:
                lit = m.group(0)
                tokens.append(make_token(TOKEN_NUMBER, lit, line_no, col))
                col += len(lit)
                s = s[len(lit):]
                continue

            # Identifiers, keywords, datatypes, operators (word-based)
            m = _RE_IDENTIFIER.match(s)
            if m:
                lit = m.group(0)
                
                # Classify the identifier
                if lit in KEYWORDS:
                    token_type = TOKEN_KEYWORD
                elif lit in DATATYPES:
                    token_type = TOKEN_DATATYPE
                elif lit in BUILTIN_LITERALS:
                    token_type = TOKEN_LITERAL
                elif lit in OPERATORS:
                    token_type = TOKEN_OPERATOR
                else:
                    token_type = TOKEN_IDENTIFIER
                
                tokens.append(make_token(token_type, lit, line_no, col))
                col += len(lit)
                s = s[len(lit):]
                continue

            # Unknown character - report as error
            tokens.append(make_token(TOKEN_UNKNOWN, s[0], line_no, col))
            s = s[1:]
            col += 1

        # Add comment token if present
        if comment_text:
            tokens.append(make_token(TOKEN_COMMENT, comment_text, line_no, col))
        
        # End of line
        tokens.append(make_token(TOKEN_NEWLINE, "", line_no, len(raw_line)))

    # FINALIZATION: Unwind remaining indentation
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(make_token(TOKEN_DEDENT, "", line_no + 1, 0))

    tokens.append(make_token(TOKEN_EOF, "", line_no + 1, 0))
    return tokens

# PRETTY PRINTER
def tokens_to_pretty_lines(tokens):
    lines = []
    
    # Map punctuation to readable names
    punct_names = {
        ",": "comma", ":": "colon", "=": "assign", ".": "dot",
        "(": "lparen", ")": "rparen", "{": "lbrace", "}": "rbrace",
        "[": "lbracket", "]": "rbracket",
        "+": "plus", "-": "minus", "*": "star", "/": "slash", "%": "mod",
        "<": "lt", ">": "gt",
    }
    
    # Map operator symbols to readable names
    operator_names = {
        "<=": "lte", ">=": "gte", "==": "eq", "!=": "neq",
        "+=": "plus_assign", "-=": "minus_assign",
        "*=": "mult_assign", "/=": "div_assign", "%=": "mod_assign",
        "**": "power", "//": "floor_div",
    }
    
    for tok in tokens:
        # Skip formatting-only tokens
        if tok["type"] in (TOKEN_NEWLINE, TOKEN_EOF):
            continue
        
        # Handle indentation tokens specially
        if tok["type"] in (TOKEN_INDENT, TOKEN_DEDENT):
            value = str(tok["value"]) if tok["value"] else tok["type"]
            lines.append((value, tok["type"], tok["lineno"]))
            continue
        
        # Determine description
        if tok["type"] == TOKEN_IDENTIFIER:
            desc = "identifier"
        elif tok["type"] == TOKEN_PUNCT:
            desc = punct_names.get(tok["value"], "punct")
        elif tok["type"] == TOKEN_OPERATOR:
            desc = operator_names.get(tok["value"], "operator")
        elif tok["type"] == TOKEN_KEYWORD:
            desc = "keyword"
        elif tok["type"] == TOKEN_DATATYPE:
            desc = "datatype"
        elif tok["type"] == TOKEN_LITERAL:
            desc = "literal"
        elif tok["type"] == TOKEN_NUMBER:
            desc = "number"
        elif tok["type"] == TOKEN_STRING:
            desc = "string"
        elif tok["type"] == TOKEN_COMMENT:
            desc = "comment"
        elif tok["type"] == TOKEN_UNKNOWN:
            desc = "unknown"
        else:
            desc = tok["type"].lower()
        
        lines.append((tok["value"], desc, tok["lineno"]))
    
    # Format with aligned columns
    if not lines:
        return ""
    
    maxlen = max(len(str(v)) for v, _, _ in lines)
    return "\n".join(
        f"{str(v).ljust(maxlen)}    → {d}    (line {ln})"
        for v, d, ln in lines
    )