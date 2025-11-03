import re

ARCANE_KEYWORDS = {
    "summon", "quest", "reward", "attack", "scout", "spot", "dodge", "counter",
    "ambush", "farm", "replay", "guild", "spawn", "embark", "gameOver",
    "savePoint", "skipEncounter", "escapeDungeon", "case",
}
ARCANE_DATATYPES = {"potion", "elixir", "fate"}
ARCANE_BUILTIN_FUNCTIONS = {"scroll"}
ARCANE_BUILTIN_LITERALS = {"true", "false"}
ARCANE_OPERATORS = {"and", "or", "not"}
MULTI_CHAR_OPS = {"<=", ">=", "==", "!=", "+=", "-=", "*=", "/="}
SINGLE_CHAR_PUNCT = {
    "(", ")", "{", "}", ":", ",", "+", "-", "*", "/", "<", ">", "=", ".", "[", "]"
}

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
_RE_COMMENT = re.compile(r"^-->(.*)")


def make_token(t_type, value, lineno, col):
    return {"type": t_type, "value": value, "lineno": lineno, "col": col}

def scan_source(source_text):
    lines = source_text.splitlines()
    tokens = []
    indent_stack = [0]
    indent_unit = None  # Will be set on first indent (e.g., 4 spaces or 1 tab)
    line_no = 0

    for raw_line in lines:
        line_no += 1
        line = raw_line.rstrip("\n\r")

        # blank lines: emit NEWLINE only
        if line.strip() == "":
            tokens.append(make_token(TOKEN_NEWLINE, "\\n", line_no, 0))
            continue

        ws_match = _RE_WS.match(line)
        leading_ws = ws_match.group(0) if ws_match else ""
        leading_spaces = leading_ws.replace("\t", "    ")  # Convert tabs to 4 spaces
        indent_len = len(leading_spaces)
        stripped = line[len(leading_ws):]

        # INDENT / DEDENT handling
        if indent_len > indent_stack[-1]:
            # Increasing indentation
            indent_increase = indent_len - indent_stack[-1]
            
            # Set the indent unit on first indent
            if indent_unit is None:
                indent_unit = indent_increase
            
            # Check if the indent is a valid multiple of the indent unit
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

        # tokenize the content of the line
        col = len(leading_ws)
        content = stripped
        comment_search = re.search(r"-->", content)
        comment_text = None
        if comment_search:
            idx = comment_search.start()
            comment_text = content[idx + 3 :]
            content_to_tokenize = content[:idx]
        else:
            content_to_tokenize = content

        s = content_to_tokenize
        while s:
            # skip whitespace inside line
            if s[0].isspace():
                ws_m = _RE_WS.match(s)
                span = len(ws_m.group(0)) if ws_m else 1
                col += span
                s = s[span:]
                continue

            # multi-char operators
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

            # single-character punctuation
            ch = s[0]
            if ch in SINGLE_CHAR_PUNCT:
                tokens.append(make_token(TOKEN_PUNCT, ch, line_no, col))
                col += 1
                s = s[1:]
                continue

            # string literal
            m = _RE_STRING.match(s)
            if m:
                lit = m.group(0)
                tokens.append(make_token(TOKEN_STRING, lit, line_no, col))
                col += len(lit)
                s = s[len(lit):]
                continue

            # number
            m = _RE_NUMBER.match(s)
            if m:
                num = m.group(0)
                tokens.append(make_token(TOKEN_NUMBER, num, line_no, col))
                col += len(num)
                s = s[len(num):]
                continue

            # identifier / keyword / datatype / literal / operator words
            m = _RE_IDENTIFIER.match(s)
            if m:
                ident = m.group(0)
                lower_ident = ident
                if lower_ident in ARCANE_KEYWORDS:
                    tokens.append(make_token(TOKEN_KEYWORD, lower_ident, line_no, col))
                elif lower_ident in ARCANE_DATATYPES:
                    tokens.append(make_token(TOKEN_DATATYPE, lower_ident, line_no, col))
                elif lower_ident in ARCANE_BUILTIN_FUNCTIONS:
                    tokens.append(make_token(TOKEN_IDENTIFIER, lower_ident, line_no, col))
                elif lower_ident in ARCANE_BUILTIN_LITERALS:
                    tokens.append(make_token(TOKEN_LITERAL, lower_ident, line_no, col))
                elif lower_ident in ARCANE_OPERATORS:
                    tokens.append(make_token(TOKEN_OPERATOR, lower_ident, line_no, col))
                else:
                    tokens.append(make_token(TOKEN_IDENTIFIER, ident, line_no, col))
                col += len(ident)
                s = s[len(ident):]
                continue

            # unknown single char
            tokens.append(make_token(TOKEN_UNKNOWN, s[0], line_no, col))
            s = s[1:]
            col += 1

        # append comment token if present
        if comment_text is not None:
            tokens.append(make_token(TOKEN_COMMENT, comment_text.strip(), line_no, col))
        # end of logical line
        tokens.append(make_token(TOKEN_NEWLINE, "\\n", line_no, len(raw_line)))

    # unwind dedents to 0
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(make_token(TOKEN_DEDENT, "DEDENT", line_no + 1, 0))

    tokens.append(make_token(TOKEN_EOF, "EOF", line_no + 1, 0))
    return tokens


# ==========================================================
# Utility: pretty print tokens for scanner UI
# ==========================================================
def tokens_to_pretty_lines(tokens):
    lines = []
    for tok in tokens:
        ttype = tok["type"]
        val = tok["value"]
        lineno = tok.get("lineno", "?")
        if ttype == TOKEN_NEWLINE:
            continue
        if ttype == TOKEN_INDENT:
            lines.append(("INDENT", str(val), lineno))
            continue
        if ttype == TOKEN_DEDENT:
            lines.append(("DEDENT", str(val), lineno))
            continue
        if ttype == TOKEN_EOF:
            continue
        descriptor = ""
        if ttype == TOKEN_KEYWORD:
            descriptor = "keyword"
        elif ttype == TOKEN_DATATYPE:
            descriptor = "datatype"
        elif ttype == TOKEN_LITERAL:
            descriptor = "literal"
        elif ttype == TOKEN_IDENTIFIER:
            descriptor = "identifier"
        elif ttype == TOKEN_NUMBER:
            descriptor = "number"
        elif ttype == TOKEN_STRING:
            descriptor = "string"
        elif ttype == TOKEN_OPERATOR:
            descriptor = "operator"
        elif ttype == TOKEN_PUNCT:
            punct_map = {
                ",": "comma", ":": "colon", "=": "assign", ".": "dot",
                "(": "lparen", ")": "rparen", "{": "lbrace", "}": "rbrace",
                "+": "plus", "-": "minus", "*": "star", "/": "slash",
                "<": "lt", ">": "gt", "<=": "lte", ">=": "gte", "==": "eq", "!=": "neq",
            }
            descriptor = punct_map.get(val, "punct")
        elif ttype == TOKEN_COMMENT:
            descriptor = "comment"
        elif ttype == TOKEN_UNKNOWN:
            descriptor = "unknown"
        else:
            descriptor = ttype.lower()
        lines.append((val, descriptor, lineno))
    pretty = []
    maxlen = 0
    for v, d, ln in lines:
        vstr = str(v)
        if len(vstr) > maxlen:
            maxlen = len(vstr)
    for v, d, ln in lines:
        pretty.append(f"{str(v).ljust(maxlen)}    → {d}    (line {ln})")
    return "\n".join(pretty)