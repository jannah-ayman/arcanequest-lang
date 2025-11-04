import re

ARCANE_KEYWORDS = {
    "summon", "quest", "reward", "attack", "scout", "spot", "dodge", "counter",
    "farm", "replay", "guild", "spawn", "embark", "gameOver",
    "savePoint", "skipEncounter", "escapeDungeon",
}
ARCANE_DATATYPES = {"potion", "elixir", "fate"}
ARCANE_BUILTIN_FUNCTIONS = {"scroll"}
ARCANE_BUILTIN_LITERALS = {"true", "false"}
ARCANE_OPERATORS = {"and", "or", "not"}
MULTI_CHAR_OPS = {"**", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/=", "//", "%="}
SINGLE_CHAR_PUNCT = {"(", ")", "{", "}", ":", ",", "+", "-", "*", "/", "<", ">", "=", ".", "[", "]", "%"}

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

_RE_NUMBER = re.compile(r"^\d+(\.\d+)?")
_RE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*")
_RE_STRING = re.compile(r"^\"([^\"\\]|\\.)*\"")
_RE_WS = re.compile(r"^[ \t]+")

make_token = lambda t, v, ln, c: {"type": t, "value": v, "lineno": ln, "col": c}

def scan_source(source_text):
    lines = source_text.splitlines()
    tokens = []
    indent_stack = [0]
    indent_unit = None
    line_no = 0

    for raw_line in lines:
        line_no += 1
        line = raw_line.rstrip("\n\r")

        if line.strip() == "":
            tokens.append(make_token(TOKEN_NEWLINE, "\\n", line_no, 0))
            continue

        ws_match = _RE_WS.match(line)
        leading_ws = ws_match.group(0) if ws_match else ""
        indent_len = len(leading_ws.replace("\t", "    "))
        stripped = line[len(leading_ws):]

        # Handle indentation
        if indent_len > indent_stack[-1]:
            indent_increase = indent_len - indent_stack[-1]
            if indent_unit is None:
                indent_unit = indent_increase
            if indent_increase != indent_unit:
                tokens.append(make_token(TOKEN_UNKNOWN, f"IndentationError: inconsistent indent (expected {indent_unit} spaces)", line_no, 0))
            indent_stack.append(indent_len)
            tokens.append(make_token(TOKEN_INDENT, indent_len, line_no, 0))
        else:
            while indent_len < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(make_token(TOKEN_DEDENT, "DEDENT", line_no, 0))
            if indent_len != indent_stack[-1]:
                tokens.append(make_token(TOKEN_UNKNOWN, f"IndentationError: unindent does not match any outer indentation level", line_no, 0))

        # Check for comment
        col = len(leading_ws)
        comment_idx = stripped.find("-->")
        content = stripped[:comment_idx] if comment_idx != -1 else stripped
        comment_text = stripped[comment_idx + 3:].strip() if comment_idx != -1 else None

        # Tokenize content
        s = content
        while s:
            if s[0].isspace():
                ws_m = _RE_WS.match(s)
                span = len(ws_m.group(0)) if ws_m else 1
                col += span
                s = s[span:]
                continue

            # Multi-char operators
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

            # Single-char punctuation
            if s[0] in SINGLE_CHAR_PUNCT:
                tokens.append(make_token(TOKEN_PUNCT, s[0], line_no, col))
                col += 1
                s = s[1:]
                continue

            # String, number, identifier
            for pattern, token_type in [(r"^\"([^\"\\]|\\.)*\"", TOKEN_STRING), 
                                        (r"^\d+(\.\d+)?", TOKEN_NUMBER), 
                                        (r"^[A-Za-z_][A-Za-z0-9_]*", None)]:
                m = re.match(pattern, s)
                if m:
                    lit = m.group(0)
                    if token_type is None:  # Identifier
                        if lit in ARCANE_KEYWORDS:
                            token_type = TOKEN_KEYWORD
                        elif lit in ARCANE_DATATYPES or lit in ARCANE_BUILTIN_FUNCTIONS:
                            token_type = TOKEN_IDENTIFIER
                        elif lit in ARCANE_BUILTIN_LITERALS:
                            token_type = TOKEN_LITERAL
                        elif lit in ARCANE_OPERATORS:
                            token_type = TOKEN_OPERATOR
                        else:
                            token_type = TOKEN_IDENTIFIER
                    tokens.append(make_token(token_type, lit, line_no, col))
                    col += len(lit)
                    s = s[len(lit):]
                    matched = True
                    break
            if matched:
                matched = False
                continue

            # Unknown character
            tokens.append(make_token(TOKEN_UNKNOWN, s[0], line_no, col))
            s = s[1:]
            col += 1

        if comment_text:
            tokens.append(make_token(TOKEN_COMMENT, comment_text, line_no, col))
        tokens.append(make_token(TOKEN_NEWLINE, "\\n", line_no, len(raw_line)))

    # Unwind dedents
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(make_token(TOKEN_DEDENT, "DEDENT", line_no + 1, 0))

    tokens.append(make_token(TOKEN_EOF, "EOF", line_no + 1, 0))
    return tokens


def tokens_to_pretty_lines(tokens):
    lines = []
    punct_map = {",": "comma", ":": "colon", "=": "assign", ".": "dot",
                 "(": "lparen", ")": "rparen", "{": "lbrace", "}": "rbrace",
                 "+": "plus", "-": "minus", "*": "star", "/": "slash",
                 "<": "lt", ">": "gt", "<=": "lte", ">=": "gte", "==": "eq", "!=": "neq"}
    
    for tok in tokens:
        if tok["type"] in (TOKEN_NEWLINE, TOKEN_EOF):
            continue
        if tok["type"] in (TOKEN_INDENT, TOKEN_DEDENT):
            lines.append((tok["type"], str(tok["value"]), tok["lineno"]))
            continue
        
        desc = {"KEYWORD": "keyword", "LITERAL": "literal", "NUMBER": "number", 
                "STRING": "string", "OPERATOR": "operator", "COMMENT": "comment", 
                "UNKNOWN": "unknown"}.get(tok["type"])
        
        if tok["type"] == TOKEN_IDENTIFIER:
            val = tok["value"]
            desc = "datatype/builtin" if val in ARCANE_DATATYPES else "builtin" if val in ARCANE_BUILTIN_FUNCTIONS else "identifier"
        elif tok["type"] == TOKEN_PUNCT:
            desc = punct_map.get(tok["value"], "punct")
        elif not desc:
            desc = tok["type"].lower()
        
        lines.append((tok["value"], desc, tok["lineno"]))
    
    maxlen = max((len(str(v)) for v, _, _ in lines), default=0)
    return "\n".join(f"{str(v).ljust(maxlen)}    → {d}    (line {ln})" for v, d, ln in lines)