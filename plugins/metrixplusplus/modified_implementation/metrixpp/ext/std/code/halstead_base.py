# from metrixpp.mpp import api
# import re

# # ==============================================================================
# # CMT++-accurate Halstead for C/C++ using a lexical analyzer (no regex tokenizing)
# # - Paired delimiters counted once per pair: () [] {}
# # - No control-paren absorption (count all)
# # - 'typespec' (e.g., int) counted as an OPERATOR for this convention
# # - Identifiers (ids) are operands; numbers/chars/strings are operands
# # - Keywords/operators are case-insensitive (use lower for stable keys)
# # - Optional file-level rollups (sum of N's; union of n's)
# # ==============================================================================

# # --------------------------- Keyword/Operator sets ----------------------------
# # Storage class specifiers (operators)
# SCSPEC_CPP   = set("""auto extern inline register static typedef virtual mutable thread_local""".split())
# # Type qualifiers (operators)
# TYPEQUAL_CPP = set("""const friend volatile""".split())
# # Other reserved words that are operators (CMT++ list EXCEPT 'asm' and 'this')
# RESERVED_OPWORDS_CPP = set("""
# break case class continue default delete do else enum for goto if new operator
# private protected public return sizeof struct switch union while namespace using
# try catch throw const_cast static_cast dynamic_cast reinterpret_cast typeid
# template explicit true false typename
# """.split())
# # TYPESPEC are OPERANDS in classic Halstead, but for your target table they are OPERATORS.
# TYPESPEC_CPP = set("""bool char double float int long short signed unsigned void wchar_t char8_t char16_t char32_t""".split())
# # Special cases: 'asm' and 'this' are OPERANDS (not operators)
# SPECIAL_OPERAND_WORDS = set(["asm", "this"])

# # Word operators = union (but DO NOT include TYPESPEC or special operand words)
# OPWORD_CPP = SCSPEC_CPP | TYPEQUAL_CPP | RESERVED_OPWORDS_CPP

# # Control-structure grouping (not used for absorption; kept for completeness)
# RESPAREN_CPP = set(["for","if","switch","while","catch"])
# RESCOLN_CPP  = set(["case"])

# # Symbolic operators (longest-first)
# SYM_OPS = [
#     "->*", ".*", "##", "::", ">>=", "<<=", "...", "->", "==", "!=", ">=", "<=", "||", "&&",
#     ">>", "<<", "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
#     "~", "!", "=", ">", "<", "&", "|", "^", "%", "/", "*", "+", "-",
#     ".", ",", ";", ":", "(", ")", "[", "]", "{", "}"
# ]

# # ------------------------------- C++ Lexer -----------------------------------
# class CppLexer(object):
#     def __init__(self, text):
#         self.s = text
#         self.n = len(text)
#         self.i = 0

#     def eof(self): return self.i >= self.n

#     def peek(self, k=0):
#         j = self.i + k
#         return "" if j >= self.n else self.s[j]

#     def get(self):
#         if self.i >= self.n: return ""
#         ch = self.s[self.i]; self.i += 1; return ch

#     def skip_ws(self):
#         while not self.eof() and self.peek().isspace():
#             self.i += 1

#     def skip_comment(self):
#         # // comment
#         if self.peek() == "/" and self.peek(1) == "/":
#             self.i += 2
#             while not self.eof() and self.peek() != "\n":
#                 self.i += 1
#             return True
#         # /* comment */
#         if self.peek() == "/" and self.peek(1) == "*":
#             self.i += 2
#             while not self.eof():
#                 if self.peek() == "*" and self.peek(1) == "/":
#                     self.i += 2
#                     break
#                 self.i += 1
#             return True
#         return False

#     def read_identifier(self):
#         start = self.i
#         ch = self.peek()
#         if not (ch.isalpha() or ch == "_"):
#             return None
#         self.i += 1
#         while not self.eof():
#             ch = self.peek()
#             if ch.isalnum() or ch == "_":
#                 self.i += 1
#             else:
#                 break
#         return self.s[start:self.i]

#     def read_number(self):
#         i0 = self.i
#         ch = self.peek()
#         if ch.isdigit():
#             pass
#         elif ch == "." and self.peek(1).isdigit():
#             pass
#         else:
#             return None

#         # Hex / bin / oct or decimal/float
#         if ch == "0" and self.peek(1) in "xX":
#             self.i += 2
#             while not self.eof() and (self.peek().isdigit() or self.peek().lower() in "abcdef" or self.peek() in "_'"):
#                 self.i += 1
#         elif ch == "0" and self.peek(1) in "bB":
#             self.i += 2
#             while not self.eof() and (self.peek() in "01_'"):
#                 self.i += 1
#         else:
#             # integer / float with optional fraction
#             while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
#                 self.i += 1
#             if not self.eof() and self.peek() == "." and self.peek(1) != ".":
#                 self.i += 1
#                 while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
#                     self.i += 1
#             # exponent
#             if not self.eof() and self.peek().lower() == "e":
#                 if (self.peek(1) in "+-" and self.peek(2).isdigit()) or self.peek(1).isdigit():
#                     self.i += 1
#                     if self.peek() in "+-": self.i += 1
#                     while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
#                         self.i += 1
#         # suffixes
#         while not self.eof() and self.peek().lower() in "ulfd'":
#             self.i += 1
#         return self.s[i0:self.i]

#     def read_char(self):
#         if self.peek() not in ["'",]:
#             return None
#         i0 = self.i
#         self.i += 1
#         while not self.eof():
#             ch = self.get()
#             if ch == "\\":
#                 self.i += 1  # escape next char (best-effort)
#             elif ch == "'":
#                 return self.s[i0:self.i]
#         return self.s[i0:self.i]  # unterminated, still count one token

#     def read_string(self):
#         if self.peek() not in ['"']:
#             return None
#         i0 = self.i
#         self.i += 1
#         while not self.eof():
#             ch = self.get()
#             if ch == "\\":
#                 self.i += 1
#             elif ch == '"':
#                 return self.s[i0:self.i]
#         return self.s[i0:self.i]

#     def read_symop(self):
#         # match longest operator
#         for op in SYM_OPS:
#             L = len(op)
#             if self.s.startswith(op, self.i):
#                 self.i += L
#                 return op
#         return None

#     def tokens(self):
#         """Yield (kind, lexeme).
#            kind in: 'kw_op', 'sym_op', 'typespec', 'id', 'number', 'char', 'string'."""
#         while not self.eof():
#             # whitespace/comments
#             self.skip_ws()
#             if self.skip_comment():
#                 continue
#             if self.eof():
#                 break

#             # literals
#             tok = self.read_char()
#             if tok is not None:
#                 yield ("char", tok); continue
#             tok = self.read_string()
#             if tok is not None:
#                 yield ("string", tok); continue
#             tok = self.read_number()
#             if tok is not None:
#                 yield ("number", tok); continue

#             # identifiers / keywords (case-insensitive membership)
#             ident = self.read_identifier()
#             if ident is not None:
#                 lo = ident.lower()
#                 if lo in TYPESPEC_CPP:
#                     yield ("typespec", ident)
#                 elif lo in OPWORD_CPP:
#                     yield ("kw_op", ident)
#                 else:
#                     yield ("id", ident)
#                 continue

#             # symbolic operators
#             op = self.read_symop()
#             if op is not None:
#                 yield ("sym_op", op); continue

#             # unknown char: skip it
#             self.i += 1


# # ------------------------------------------------------------------------------
# # Java fallback (unchanged), only to keep plugin happy if it meets Java files
# # ------------------------------------------------------------------------------
# OPENPARENS_JAVA = r"""\(|\[|\{"""
# OPERATORS_JAVA = r"""#|!=|!|~|\+\+|\+=|\+|--|-=|->|-|\*=|\*|/=|/|%=|%|==|=|>>>=|>>>|>>=|>>|>=|>|<<=|<<|<=|<|\|\||\|=|\||\^\^|\^=|\^|&&|&=|&|::|:|\?|\.\.\.|\.|\,|;"""
# SCSPEC_JAVA    = r"""static|abstract|native|import|final|implements|extends|throws"""
# TYPEQUAL_JAVA  = r"""const|volatile"""
# RESERVED_JAVA  = r"""assert|class|else|enum|goto|new|this|try|throw|break|continue|return|private|protected|public|true|false|package|instanceof|interface|synchronized"""
# RESPAREN_JAVA  = r"""for|if|switch|while|catch|finally|super"""
# RESCOLN_JAVA   = r"""case|default"""
# RESWORD_JAVA   = SCSPEC_JAVA+"|"+TYPEQUAL_JAVA+"|"+RESERVED_JAVA+"|"+RESPAREN_JAVA+"|"+RESCOLN_JAVA
# RESWORDALL_JAVA = r"(\b"+RESWORD_JAVA+"|do"+r")\b"


# # ==============================================================================
# class Plugin(api.Plugin,
#              api.IConfigurable,
#              api.Child,
#              api.MetricPluginMixin):

#     halstead_dict = {}
#     opt_prefix = 'std.code.halstead.'

#     def __init__(self, *args, **kwargs):
#         super(Plugin, self).__init__(*args, **kwargs)
#         self.ops_dict_by_region = {}       # region_name -> {op_kind: count}
#         self.operands_dict_by_region = {}  # region_name -> {operand_kind: count}
#         self.options = None

#     def declare_configuration(self, parser):
#         def add_option(opt,action,default,help):
#             parser.add_option("--"+self.opt_prefix+opt, "--sch"+opt, action=action, default=default,
#                 help=help)
#         self.parser = parser
#         add_option("all", action="store_true", default=False,
#             help="Halstead metrics plugin: all metrics are calculated [default: %default]")
#         add_option("base", action="store_true", default=False,
#             help="Halstead metrics plugin: base metrics n1,n2,N1,N2 [default: %default]")
#         add_option("rollup", action="store_true", default=False,
#             help="Halstead: also compute file-level rollups (sum of N's, union of n's) [default: %default]")

#     def configure(self, options):
#         self.options = options
#         self.is_active_ehb = options.__dict__[self.opt_prefix+'base'] or options.__dict__[self.opt_prefix+'all']

#     def initialize(self):
#         # Dummy/fallback patterns (Java/catch-all). C++ path ignores patterns.
#         operator_pattern_search = re.compile(r"[\+\-\*\/\=]")
#         operator_pattern_java = re.compile(
#             r"(\b("+RESWORD_JAVA+r")\b|"+OPERATORS_JAVA+"|"+OPENPARENS_JAVA+")"
#         )
#         operand_pattern_search = re.compile(r"(\b\w+\b)")

#         # N1
#         self.declare_metric(self.is_active_ehb,
#                             self.Field('N1', int, non_zero=True),
#                             {
#                              'std.code.java': (operator_pattern_java, self.HalsteadCounter_N1_java),
#                              'std.code.cpp':  (None,                   self.HalsteadCounter_N1_cpp),
#                              '*': operator_pattern_search
#                             },
#                             marker_type_mask=api.Marker.T.CODE+api.Marker.T.PREPROCESSOR,
#                             region_type_mask=api.Region.T.ANY)

#         # n1
#         self.declare_metric(self.is_active_ehb,
#                             self.Field('_n1', int, non_zero=True),
#                             {'*':(None, self.HalsteadCounter_n1)},
#                             marker_type_mask=api.Marker.T.NONE)

#         # N2
#         self.declare_metric(self.is_active_ehb,
#                             self.Field('N2', int, non_zero=True),
#                             {
#                              'std.code.java': (operand_pattern_search, self.HalsteadCounter_N2_java),
#                              'std.code.cpp':  (None,                    self.HalsteadCounter_N2_cpp),
#                              '*': operand_pattern_search
#                             },
#                             marker_type_mask=api.Marker.T.CODE+api.Marker.T.STRING+api.Marker.T.PREPROCESSOR,
#                             region_type_mask=api.Region.T.ANY)

#         # n2
#         self.declare_metric(self.is_active_ehb,
#                             self.Field('_n2', int, non_zero=True),
#                             {'*':(None, self.HalsteadCounter_n2)},
#                             marker_type_mask=api.Marker.T.NONE)

#         # Optional file-level rollup fields (no markers; we will set them in callback)
#         want_rollup = self.options and (self.options.__dict__[self.opt_prefix+'rollup'] or self.options.__dict__[self.opt_prefix+'all'])
#         if want_rollup:
#             self._fields.append((
#                 self.Field('N1_file', int, non_zero=True), api.Marker.T.NONE, True, False,
#                 {'*': (None, api.MetricPluginMixin.PlainCounter)}, api.Region.T.ANY
#             ))
#             self._fields.append((
#                 self.Field('N2_file', int, non_zero=True), api.Marker.T.NONE, True, False,
#                 {'*': (None, api.MetricPluginMixin.PlainCounter)}, api.Region.T.ANY
#             ))
#             self._fields.append((
#                 self.Field('_n1_file', int, non_zero=True), api.Marker.T.NONE, True, False,
#                 {'*': (None, api.MetricPluginMixin.PlainCounter)}, api.Region.T.ANY
#             ))
#             self._fields.append((
#                 self.Field('_n2_file', int, non_zero=True), api.Marker.T.NONE, True, False,
#                 {'*': (None, api.MetricPluginMixin.PlainCounter)}, api.Region.T.ANY
#             ))

#         super(Plugin, self).initialize(fields=self.get_fields(), support_regions=True)
#         if self.is_active():
#             self.subscribe_by_parents_interface(api.ICode)

#     # Ordered-field helpers (unchanged)
#     def declare_metric(self, is_active, field, pattern_to_search_or_map_of_patterns,
#                        marker_type_mask=api.Marker.T.ANY, region_type_mask=api.Region.T.ANY,
#                        exclude_subregions=True, merge_markers=False):
#         if hasattr(self, '_fields') == False:
#             self._fields = []
#         if isinstance(pattern_to_search_or_map_of_patterns, dict):
#             map_of_patterns = pattern_to_search_or_map_of_patterns
#         else:
#             map_of_patterns = {'*': pattern_to_search_or_map_of_patterns}
#         for key in list(map_of_patterns.keys()):
#             if not isinstance(map_of_patterns[key], tuple):
#                 map_of_patterns[key] = (map_of_patterns[key],
#                                         api.MetricPluginMixin.PlainCounter)
#         if is_active:
#             self._fields.append((field, marker_type_mask, exclude_subregions,
#                                  merge_markers, map_of_patterns, region_type_mask))

#     def is_active(self): return (len(self._fields) > 0)
#     def get_fields(self): return [f[0] for f in self._fields]

#     def callback(self, parent, data, is_updated):
#         is_updated = is_updated or self.is_updated
#         if is_updated:
#             for idx in range(len(self._fields)):
#                 self.count(self.get_namespace(), self._fields[idx], data, alias=parent.get_name())

#         # -------------------- File-level rollups (optional) --------------------
#         want_rollup = self.options and (self.options.__dict__[self.opt_prefix+'rollup'] or self.options.__dict__[self.opt_prefix+'all'])
#         if want_rollup:
#             N1_sum = 0
#             N2_sum = 0
#             op_kinds = set()
#             operand_kinds = set()

#             for region in data.iterate_regions(filter_group=api.Region.T.ANY):
#                 rname = region.name
#                 if rname is None:
#                     continue  # skip file-level as a source for rollup
#                 ops = self.ops_dict_by_region.get(rname, {})
#                 opr = self.operands_dict_by_region.get(rname, {})
#                 N1_sum += sum(ops.values())
#                 N2_sum += sum(opr.values())
#                 op_kinds.update(ops.keys())
#                 operand_kinds.update(opr.keys())

#             # Store on the FILE region
#             data.set_data(self.get_namespace(), 'N1_file',  N1_sum)
#             data.set_data(self.get_namespace(), 'N2_file',  N2_sum)
#             data.set_data(self.get_namespace(), '_n1_file', len(op_kinds))
#             data.set_data(self.get_namespace(), '_n2_file', len(operand_kinds))

#         self.notify_children(data, is_updated)

#     def count(self, namespace, field_data, data, alias='*'):
#         field_name = field_data[0].name
#         if alias not in list(field_data[4].keys()):
#             alias = '*' if '*' in list(field_data[4].keys()) else alias
#         (pattern_to_search, counter_class) = field_data[4][alias]
#         if field_data[0]._regions_supported:
#             for region in data.iterate_regions(filter_group=field_data[5]):
#                 counter = counter_class(namespace, field_name, self, alias, data, region)
#                 if field_data[1] != api.Marker.T.NONE:
#                     for marker in data.iterate_markers(filter_group=field_data[1],
#                                                        region_id=region.get_id(),
#                                                        exclude_children=field_data[2],
#                                                        merge=field_data[3]):
#                         counter.count(marker, pattern_to_search)
#                 count = counter.get_result()
#                 if (count != 0) or not field_data[0].non_zero:
#                     region.set_data(namespace, field_name, count)
#         else:
#             counter = counter_class(namespace, field_name, self, alias, data, None)
#             if field_data[1] != api.Marker.T.NONE:
#                 for marker in data.iterate_markers(filter_group=field_data[1],
#                                                    region_id=None,
#                                                    exclude_children=field_data[2],
#                                                    merge=field_data[3]):
#                     counter.count(marker, pattern_to_search)
#             count = counter.get_result()
#             if count != 0 or field_data[0].non_zero == False:
#                 data.set_data(namespace, field_name, count)

#     def set_halstead_dict(self, key, entry, kind=None):
#         # kind in {"op","operand"}; also keep legacy single dict for _n1/_n2
#         if kind == "op":
#             self.ops_dict_by_region[key] = dict(entry)
#         elif kind == "operand":
#             self.operands_dict_by_region[key] = dict(entry)
#         # legacy store for distinct counters
#         self.halstead_dict[key] = entry

#     def get_halstead_dict(self, key):
#         if key not in self.halstead_dict:
#             self.halstead_dict[key] = {}
#         return self.halstead_dict[key]

#     # =============================== Counters =================================
#     class DictCounter(api.MetricPluginMixin.IterIncrementCounter):
#         def __init__(self, *args, **kwargs):
#             super(Plugin.DictCounter, self).__init__(*args, **kwargs)
#             self.dictcounter = {}

#         def inc_dictcounter(self, key):
#             if key not in self.dictcounter:
#                 self.dictcounter[key] = 0
#             self.dictcounter[key] += 1

#         def increment(self, match):
#             # Not used in lexer path; kept for fallback
#             self.inc_dictcounter(match.group(0))
#             return 1

#     class HalsteadCounter(DictCounter):
#         def __init__(self, namespace, field_name, plugin, alias, data, region):
#             super(Plugin.HalsteadCounter, self).__init__(namespace, field_name, plugin, alias, data, region)
#             self.plugin = plugin
#             self.data = data
#             self.region = region
#             self.result = 0

#         def get_dictkey(self):
#             return "__file__" if (self.region is None or self.region.name is None) else self.region.name

#     class HalsteadCounter_N(HalsteadCounter):
#         def get_result(self):
#             # store for distinct (_n1/_n2) readers
#             self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter)
#             return self.result

#     class HalsteadCounter_n(HalsteadCounter):
#         def get_result(self):
#             self.dictcounter = self.plugin.get_halstead_dict(self.get_dictkey())
#             return len(self.dictcounter)

#     # ------------------------------- N1 (operators)
#     class HalsteadCounter_N1(HalsteadCounter_N):
#         def count(self, marker, _unused):
#             text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
#             self.marker = marker

#             if marker.group == api.Marker.T.PREPROCESSOR:
#                 m = re.match(r"^[ \t]*\#[ \t]*([A-Za-z]\w+)", text)
#                 if m:
#                     key = "#" + m.group(1).lower()
#                     self.inc_dictcounter(key); self.result += 1
#                 return

#             if marker.group != api.Marker.T.CODE:
#                 return  # skip comments/strings here

#             lex = CppLexer(text)
#             for kind, tok in lex.tokens():
#                 if kind == "sym_op":
#                     # Count pairs once: only when we see the opening delimiter
#                     if tok in ("(", "[", "{"):
#                         key = {"(":"()", "[":"[]", "{":"{}"}[tok]
#                         self.inc_dictcounter(key); self.result += 1
#                     elif tok in (")", "]", "}"):
#                         pass  # ignore closing side
#                     else:
#                         self.inc_dictcounter(tok); self.result += 1
#                     continue

#                 # Treat type specifiers as OPERATOR for your expected table
#                 if kind == "typespec":
#                     self.inc_dictcounter(tok); self.result += 1
#                     continue

#                 # Keyword operators (if, for, return, etc.) — normalize to lower
#                 if kind == "kw_op":
#                     self.inc_dictcounter(tok.lower()); self.result += 1
#                     continue
#                 # other kinds are not operators here

#         def get_result(self):
#             # Save categorized dict for rollups, and legacy store for _n1
#             self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter, kind="op")
#             return super(Plugin.HalsteadCounter_N1, self).get_result()

#     class HalsteadCounter_N1_cpp(HalsteadCounter_N1):
#         pass

#     class HalsteadCounter_N1_java(HalsteadCounter_N):
#         def count(self, marker, pattern_to_search):
#             # keep original regex-based Java path
#             text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
#             self.marker = marker
#             if marker.group == api.Marker.T.PREPROCESSOR:
#                 m = re.match(r"^[ \t]*\#[ \t]*([A-Za-z]\w+)", text)
#                 if m:
#                     key = "#" + m.group(1).lower()
#                     self.inc_dictcounter(key); self.result += 1
#                 return
#             for match in pattern_to_search.finditer(text):
#                 self.result += self.increment(match)

#         def get_result(self):
#             self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter, kind="op")
#             return super(Plugin.HalsteadCounter_N1_java, self).get_result()

#     # ------------------------------- N2 (operands)
#     class HalsteadCounter_N2(HalsteadCounter_N):
#         def count(self, marker, _unused):
#             text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
#             self.marker = marker

#             if marker.group == api.Marker.T.PREPROCESSOR:
#                 return  # no operands in preprocessor directives

#             if marker.group == api.Marker.T.STRING:
#                 if text:
#                     self.inc_dictcounter(text)
#                     self.result += 1
#                 return

#             if marker.group != api.Marker.T.CODE:
#                 return

#             lex = CppLexer(text)
#             for kind, tok in lex.tokens():
#                 if kind in ("number", "char", "string"):
#                     self.inc_dictcounter(tok); self.result += 1
#                 elif kind == "id":
#                     self.inc_dictcounter(tok); self.result += 1
#                 # NOTE: typespec NOT counted as operand for your expected table

#         def get_result(self):
#             self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter, kind="operand")
#             return super(Plugin.HalsteadCounter_N2, self).get_result()

#     class HalsteadCounter_N2_cpp(HalsteadCounter_N2):
#         pass

#     class HalsteadCounter_N2_java(HalsteadCounter_N2):
#         def count(self, marker, pattern_to_search):
#             text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
#             self.marker = marker
#             if marker.group == api.Marker.T.PREPROCESSOR:
#                 return
#             if marker.group == api.Marker.T.STRING:
#                 if text:
#                     self.inc_dictcounter(text); self.result += 1
#                 return
#             for match in pattern_to_search.finditer(text):
#                 self.result += self.increment(match)

#         def get_result(self):
#             self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter, kind="operand")
#             return super(Plugin.HalsteadCounter_N2_java, self).get_result()

#     # ------------------------- Distinct counts ---------------------------------
#     class HalsteadCounter_n1(HalsteadCounter_n): pass
#     class HalsteadCounter_n2(HalsteadCounter_n): pass




from metrixpp.mpp import api
import re

# ==============================================================================
# CMT++-accurate Halstead for C++ using a lexical analyzer (no regex tokenizing)
# ==============================================================================

# --------------------------- Keyword/Operator sets ----------------------------
# Storage class specifiers (operators)
SCSPEC_CPP   = set("""auto extern inline register static typedef virtual mutable thread_local""".split())
# Type qualifiers (operators)
TYPEQUAL_CPP = set("""const friend volatile""".split())
# Other reserved words that are operators (CMT++ list EXCEPT 'asm' and 'this')
RESERVED_OPWORDS_CPP = set("""
break case class continue default delete do else enum for goto if new operator
private protected public return sizeof struct switch union while namespace using
try catch throw const_cast static_cast dynamic_cast reinterpret_cast typeid
template explicit true false typename
""".split())
# TYPESPEC are OPERANDS per CMT++
TYPESPEC_CPP = set("""bool char double float int long short signed unsigned void wchar_t char8_t char16_t char32_t""".split())
# Special cases: 'asm' and 'this' are OPERANDS (not operators)
SPECIAL_OPERAND_WORDS = set(["asm", "this"])

# Word operators = union (but DO NOT include TYPESPEC or special operand words)
OPWORD_CPP = SCSPEC_CPP | TYPEQUAL_CPP | RESERVED_OPWORDS_CPP

# Control-structure grouping
RESPAREN_CPP = set(["for","if","switch","while","catch"])
RESCOLN_CPP  = set(["case"])  # add "default" here if you want to absorb its colon too

# Symbolic operators (longest-first)
SYM_OPS = [
    "->*", ".*", "##", "::", ">>=", "<<=", "...", "->", "==", "!=", ">=", "<=", "||", "&&",
    ">>", "<<", "++", "--", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=",
    "~", "!", "=", ">", "<", "&", "|", "^", "%", "/", "*", "+", "-",
    ".", ",", ";", ":", "(", ")", "[", "]", "{", "}"
]

# ------------------------------- C++ Lexer -----------------------------------
class CppLexer(object):
    def __init__(self, text):
        self.s = text
        self.n = len(text)
        self.i = 0

    def eof(self): return self.i >= self.n

    def peek(self, k=0):
        j = self.i + k
        return "" if j >= self.n else self.s[j]

    def get(self):
        if self.i >= self.n: return ""
        ch = self.s[self.i]; self.i += 1; return ch

    def skip_ws(self):
        while not self.eof() and self.peek().isspace():
            self.i += 1

    def skip_comment(self):
        # // comment
        if self.peek() == "/" and self.peek(1) == "/":
            self.i += 2
            while not self.eof() and self.peek() != "\n":
                self.i += 1
            return True
        # /* comment */
        if self.peek() == "/" and self.peek(1) == "*":
            self.i += 2
            while not self.eof():
                if self.peek() == "*" and self.peek(1) == "/":
                    self.i += 2
                    break
                self.i += 1
            return True
        return False

    def read_identifier(self):
        start = self.i
        ch = self.peek()
        if not (ch.isalpha() or ch == "_"):
            return None
        self.i += 1
        while not self.eof():
            ch = self.peek()
            if ch.isalnum() or ch == "_":
                self.i += 1
            else:
                break
        return self.s[start:self.i]

    def read_number(self):
        i0 = self.i
        ch = self.peek()
        if ch.isdigit():
            pass
        elif ch == "." and self.peek(1).isdigit():
            pass
        else:
            return None

        # Hex / bin / oct or decimal/float
        if ch == "0" and self.peek(1) in "xX":
            self.i += 2
            while not self.eof() and (self.peek().isdigit() or self.peek().lower() in "abcdef" or self.peek() in "_'"):
                self.i += 1
        elif ch == "0" and self.peek(1) in "bB":
            self.i += 2
            while not self.eof() and (self.peek() in "01_'"):
                self.i += 1
        else:
            # integer / float with optional fraction
            while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
                self.i += 1
            if not self.eof() and self.peek() == "." and self.peek(1) != ".":
                self.i += 1
                while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
                    self.i += 1
            # exponent
            if not self.eof() and self.peek().lower() == "e":
                if (self.peek(1) in "+-" and self.peek(2).isdigit()) or self.peek(1).isdigit():
                    self.i += 1
                    if self.peek() in "+-": self.i += 1
                    while not self.eof() and (self.peek().isdigit() or self.peek() in "_'"):
                        self.i += 1
        # suffixes
        while not self.eof() and self.peek().lower() in "ulfd'":
            self.i += 1
        return self.s[i0:self.i]

    def read_char(self):
        if self.peek() not in ["'",]:
            return None
        i0 = self.i
        self.i += 1
        while not self.eof():
            ch = self.get()
            if ch == "\\":
                self.i += 1  # escape next char (best-effort)
            elif ch == "'":
                return self.s[i0:self.i]
        return self.s[i0:self.i]  # unterminated, still count one token

    def read_string(self):
        if self.peek() not in ['"']:
            return None
        i0 = self.i
        self.i += 1
        while not self.eof():
            ch = self.get()
            if ch == "\\":
                self.i += 1
            elif ch == '"':
                return self.s[i0:self.i]
        return self.s[i0:self.i]

    def read_symop(self):
        # match longest operator
        for op in SYM_OPS:
            L = len(op)
            if self.s.startswith(op, self.i):
                # For '.' ensure not a decimal point; handled by read_number before
                self.i += L
                return op
        return None

    def tokens(self):
        """Yield (kind, lexeme).
           kind in: 'kw_op', 'sym_op', 'typespec', 'id', 'number', 'char', 'string'."""
        while not self.eof():
            # whitespace/comments
            self.skip_ws()
            if self.skip_comment():
                continue
            if self.eof():
                break

            # literals
            tok = self.read_char()
            if tok is not None:
                yield ("char", tok); continue
            tok = self.read_string()
            if tok is not None:
                yield ("string", tok); continue
            tok = self.read_number()
            if tok is not None:
                yield ("number", tok); continue

            # identifiers / keywords
            ident = self.read_identifier()
            if ident is not None:
                lo = ident.lower()   # <-- lowercase for set membership
                if lo in TYPESPEC_CPP:
                    yield ("typespec", ident)
                elif lo in OPWORD_CPP:
                    yield ("kw_op", ident)
                else:
                    yield ("id", ident)
                continue

            # symbolic operators
            op = self.read_symop()
            if op is not None:
                yield ("sym_op", op); continue

            # unknown char: skip it
            self.i += 1


# ------------------------------------------------------------------------------
# Java fallback (unchanged), only to keep plugin happy if it meets Java files
# ------------------------------------------------------------------------------
OPENPARENS_JAVA = r"""\(|\[|\{"""
OPERATORS_JAVA = r"""#|!=|!|~|\+\+|\+=|\+|--|-=|->|-|\*=|\*|/=|/|%=|%|==|=|>>>=|>>>|>>=|>>|>=|>|<<=|<<|<=|<|\|\||\|=|\||\^\^|\^=|\^|&&|&=|&|::|:|\?|\.\.\.|\.|\,|;"""
SCSPEC_JAVA    = r"""static|abstract|native|import|final|implements|extends|throws"""
TYPEQUAL_JAVA  = r"""const|volatile"""
RESERVED_JAVA  = r"""assert|class|else|enum|goto|new|this|try|throw|break|continue|return|private|protected|public|true|false|package|instanceof|interface|synchronized"""
RESPAREN_JAVA  = r"""for|if|switch|while|catch|finally|super"""
RESCOLN_JAVA   = r"""case|default"""
RESWORD_JAVA   = SCSPEC_JAVA+"|"+TYPEQUAL_JAVA+"|"+RESERVED_JAVA+"|"+RESPAREN_JAVA+"|"+RESCOLN_JAVA
RESWORDALL_JAVA = r"(\b"+RESWORD_JAVA+"|do"+r")\b"


# ==============================================================================
class Plugin(api.Plugin,
             api.IConfigurable,
             api.Child,
             api.MetricPluginMixin):

    halstead_dict = {}
    opt_prefix = 'std.code.halstead.'

    def declare_configuration(self, parser):
        def add_option(opt,action,default,help):
            parser.add_option("--"+self.opt_prefix+opt, "--sch"+opt, action=action, default=default,
                help=help)
        self.parser = parser
        add_option("all", action="store_true", default=False,
            help="Halstead metrics plugin: all metrics are calculated [default: %default]")
        add_option("base", action="store_true", default=False,
            help="Halstead metrics plugin: base metrics n1,n2,N1,N2 [default: %default]")

    def configure(self, options):
        self.is_active_ehb = options.__dict__[self.opt_prefix+'base'] or options.__dict__[self.opt_prefix+'all']

    def initialize(self):
        # Dummy/fallback patterns (Java/catch-all). C++ path ignores patterns.
        operator_pattern_search = re.compile(r"[\+\-\*\/\=]")
        operator_pattern_java = re.compile(
            r"(\b("+RESWORD_JAVA+r")\b|"+OPERATORS_JAVA+"|"+OPENPARENS_JAVA+")"
        )
        operand_pattern_search = re.compile(r"(\b\w+\b)")

        # N1
        self.declare_metric(self.is_active_ehb,
                            self.Field('N1', int, non_zero=True),
                            {
                             'std.code.java': (operator_pattern_java, self.HalsteadCounter_N1_java),
                             'std.code.cpp':  (None,                   self.HalsteadCounter_N1_cpp),
                             '*': operator_pattern_search
                            },
                            marker_type_mask=api.Marker.T.CODE+api.Marker.T.PREPROCESSOR,
                            region_type_mask=api.Region.T.ANY)

        # n1
        self.declare_metric(self.is_active_ehb,
                            self.Field('_n1', int, non_zero=True),
                            {'*':(None, self.HalsteadCounter_n1)},
                            marker_type_mask=api.Marker.T.NONE)

        # N2
        self.declare_metric(self.is_active_ehb,
                            self.Field('N2', int, non_zero=True),
                            {
                             'std.code.java': (operand_pattern_search, self.HalsteadCounter_N2_java),
                             'std.code.cpp':  (None,                    self.HalsteadCounter_N2_cpp),
                             '*': operand_pattern_search
                            },
                            marker_type_mask=api.Marker.T.CODE+api.Marker.T.STRING+api.Marker.T.PREPROCESSOR,
                            region_type_mask=api.Region.T.ANY)

        # n2
        self.declare_metric(self.is_active_ehb,
                            self.Field('_n2', int, non_zero=True),
                            {'*':(None, self.HalsteadCounter_n2)},
                            marker_type_mask=api.Marker.T.NONE)

        super(Plugin, self).initialize(fields=self.get_fields(), support_regions=True)
        if self.is_active():
            self.subscribe_by_parents_interface(api.ICode)

    # Ordered-field helpers (unchanged)
    def declare_metric(self, is_active, field, pattern_to_search_or_map_of_patterns,
                       marker_type_mask=api.Marker.T.ANY, region_type_mask=api.Region.T.ANY,
                       exclude_subregions=True, merge_markers=False):
        if hasattr(self, '_fields') == False:
            self._fields = []
        if isinstance(pattern_to_search_or_map_of_patterns, dict):
            map_of_patterns = pattern_to_search_or_map_of_patterns
        else:
            map_of_patterns = {'*': pattern_to_search_or_map_of_patterns}
        for key in list(map_of_patterns.keys()):
            if not isinstance(map_of_patterns[key], tuple):
                map_of_patterns[key] = (map_of_patterns[key],
                                        api.MetricPluginMixin.PlainCounter)
        if is_active:
            self._fields.append((field, marker_type_mask, exclude_subregions,
                                 merge_markers, map_of_patterns, region_type_mask))

    def is_active(self): return (len(self._fields) > 0)
    def get_fields(self): return [f[0] for f in self._fields]

    def callback(self, parent, data, is_updated):
        is_updated = is_updated or self.is_updated
        if is_updated:
            for idx in range(len(self._fields)):
                self.count(self.get_namespace(), self._fields[idx], data, alias=parent.get_name())
        self.notify_children(data, is_updated)

    def count(self, namespace, field_data, data, alias='*'):
        field_name = field_data[0].name
        if alias not in list(field_data[4].keys()):
            alias = '*' if '*' in list(field_data[4].keys()) else alias
        (pattern_to_search, counter_class) = field_data[4][alias]
        if field_data[0]._regions_supported:
            for region in data.iterate_regions(filter_group=field_data[5]):
                counter = counter_class(namespace, field_name, self, alias, data, region)
                if field_data[1] != api.Marker.T.NONE:
                    for marker in data.iterate_markers(filter_group=field_data[1],
                                                       region_id=region.get_id(),
                                                       exclude_children=field_data[2],
                                                       merge=field_data[3]):
                        counter.count(marker, pattern_to_search)
                count = counter.get_result()
                if (count != 0) or not field_data[0].non_zero:
                    region.set_data(namespace, field_name, count)
        else:
            counter = counter_class(namespace, field_name, self, alias, data, None)
            if field_data[1] != api.Marker.T.NONE:
                for marker in data.iterate_markers(filter_group=field_data[1],
                                                   region_id=None,
                                                   exclude_children=field_data[2],
                                                   merge=field_data[3]):
                    counter.count(marker, pattern_to_search)
            count = counter.get_result()
            if count != 0 or field_data[0].non_zero == False:
                data.set_data(namespace, field_name, count)

    def set_halstead_dict(self, key, entry):
        self.halstead_dict[key] = entry

    def get_halstead_dict(self, key):
        if key not in self.halstead_dict:
            self.halstead_dict[key] = {}
        return self.halstead_dict[key]

    def _normalize_symop(self, tok: str) -> str:
        if tok in ("(", ")"):
            return "()"
        if tok in ("[", "]"):
            return "[]"
        if tok in ("{", "}"):
            return "{}"
        return tok

    # =============================== Counters =================================
    class DictCounter(api.MetricPluginMixin.IterIncrementCounter):
        def __init__(self, *args, **kwargs):
            super(Plugin.DictCounter, self).__init__(*args, **kwargs)
            self.dictcounter = {}

        def inc_dictcounter(self, key):
            if key not in self.dictcounter:
                self.dictcounter[key] = 0
            self.dictcounter[key] += 1

        def increment(self, match):
            # Not used in lexer path; kept for fallback
            self.inc_dictcounter(match.group(0))
            return 1

    class HalsteadCounter(DictCounter):
        def get_dictkey(self):
            return "__file__" if self.region.name is None else self.region.name

    class HalsteadCounter_N(HalsteadCounter):
        def get_result(self):
            self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter)
            return self.result

    class HalsteadCounter_n(HalsteadCounter):
        def get_result(self):
            self.dictcounter = self.plugin.get_halstead_dict(self.get_dictkey())
            return len(self.dictcounter)

    # ------------------------------- N1 (operators)
    class HalsteadCounter_N1(HalsteadCounter_N):
        def count(self, marker, _unused):
            text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
            self.marker = marker

            if marker.group == api.Marker.T.PREPROCESSOR:
                m = re.match(r"^[ \t]*\#[ \t]*([A-Za-z]\w+)", text)
                if m:
                    key = "#" + m.group(1).lower()
                    self.inc_dictcounter(key); self.result += 1
                return

            if marker.group != api.Marker.T.CODE:
                return

            lex = CppLexer(text)
            for kind, tok in lex.tokens():
                if kind == "sym_op":
                    # Count pairs once: only on opening token
                    if tok in ("(", "[", "{"):
                        key = {"(":"()", "[":"[]", "{":"{}"}[tok]
                        self.inc_dictcounter(key); self.result += 1
                    elif tok in (")", "]", "}"):
                        pass  # skip closing side of the pair
                    else:
                        # all other symbolic operators (<=, =, ++, ,, ;, etc.)
                        self.inc_dictcounter(tok); self.result += 1
                    continue

                # Treat typespec (e.g., 'int') as operator for this convention
                if kind == "typespec":
                    self.inc_dictcounter(tok); self.result += 1
                    continue

                # Keyword operators (if, for, return, etc.)
                if kind == "kw_op":
                    self.inc_dictcounter(tok.lower()); self.result += 1
                    continue
                # other kinds are not operators here

        def get_result(self):
            # print("N1 operators:", sorted(self.dictcounter.items()))  # optional debug
            self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter)
            return self.result
    # class HalsteadCounter_N1(HalsteadCounter_N):
    #     def __init__(self, *args, **kwargs):
    #         super(Plugin.HalsteadCounter_N1, self).__init__(*args, **kwargs)
    #         self.absorb_paren = False
    #         self.in_ctrl_parens = 0
    #         self.absorb_colon = False

    #     def count(self, marker, _unused):
    #         text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
    #         self.marker = marker
    #         if marker.group == api.Marker.T.PREPROCESSOR:
    #             # Count the directive keyword as one operator, e.g. "#define"
    #             m = re.match(r"^[ \t]*\#[ \t]*([A-Za-z]\w+)", text)
    #             if m:
    #                 key = "#" + m.group(1).lower()
    #                 self.inc_dictcounter(key); self.result += 1
    #             return

    #         if marker.group != api.Marker.T.CODE:
    #             return  # strings/comments not operators

    #         lex = CppLexer(text)
    #         for kind, tok in lex.tokens():
    #             # Grouping: absorb '(' immediately after control keyword
    #             if kind == "kw_op" and tok in RESPAREN_CPP:
    #                 self.inc_dictcounter(tok); self.result += 1
    #                 self.absorb_paren = True
    #                 continue
    #             if kind == "kw_op" and tok in RESCOLN_CPP:
    #                 self.inc_dictcounter(tok); self.result += 1
    #                 self.absorb_colon = True
    #                 continue

    #             if kind == "sym_op":
    #                 key = self.plugin._normalize_symop(tok)
    #                 self.inc_dictcounter(key); self.result += 1
    #                 continue

    #             if kind == "kw_op":
    #                 # count all operator-like keywords (if, for, return, etc.)
    #                 self.inc_dictcounter(tok.lower()); self.result += 1
    #                 continue

    #             # if kind == "sym_op":
    #             #     if tok == "(":
    #             #         if self.absorb_paren and self.in_ctrl_parens == 0:
    #             #             self.absorb_paren = False
    #             #             self.in_ctrl_parens = 1
    #             #             continue  # absorbed
    #             #         elif self.in_ctrl_parens > 0:
    #             #             self.in_ctrl_parens += 1
    #             #             continue
    #             #     if tok == ")":
    #             #         if self.in_ctrl_parens > 0:
    #             #             self.in_ctrl_parens -= 1
    #             #             continue  # both opening and closing absorbed
    #             #     if tok == ":" and self.absorb_colon:
    #             #         self.absorb_colon = False
    #             #         continue  # absorbed

    #             #     # normal symbolic operator
    #             #     self.inc_dictcounter(tok); self.result += 1
    #             #     continue

    #             # if kind == "kw_op":
    #                 # operator-like keywords (already handled control/case above)
    #                 self.inc_dictcounter(tok); self.result += 1
    #                 continue
    #             # other kinds are not operators here

    class HalsteadCounter_N1_cpp(HalsteadCounter_N1):
        pass

    class HalsteadCounter_N1_java(HalsteadCounter_N1):
        def count(self, marker, pattern_to_search):
            # keep original regex-based Java path
            text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
            self.marker = marker
            if marker.group == api.Marker.T.PREPROCESSOR:
                m = re.match(r"^[ \t]*\#[ \t]*([A-Za-z]\w+)", text)
                if m:
                    key = "#" + m.group(1).lower()
                    self.inc_dictcounter(key); self.result += 1
                return
            for match in pattern_to_search.finditer(text):
                self.result += self.increment(match)

    # ------------------------------- N2 (operands)
    class HalsteadCounter_N2(HalsteadCounter_N):
        def count(self, marker, _unused):
            text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
            self.marker = marker

            if marker.group == api.Marker.T.PREPROCESSOR:
                return  # no operands in preprocessor directives

            if marker.group == api.Marker.T.STRING:
                if text:
                    self.inc_dictcounter(text)
                    self.result += 1
                return

            if marker.group != api.Marker.T.CODE:
                return

            lex = CppLexer(text)
            for kind, tok in lex.tokens():
                # Count numbers, char, string literals
                if kind in ("number", "char", "string"):
                    self.inc_dictcounter(tok)
                    self.result += 1
                # Identifiers are operands
                elif kind == "id":
                    self.inc_dictcounter(tok)
                    self.result += 1
                # typespec NOT counted here (int, etc.)

        def get_result(self):
            # DEBUG:
            # print("N2 operands:", sorted(self.dictcounter.items()))
            self.plugin.set_halstead_dict(self.get_dictkey(), self.dictcounter)
            return self.result
    # class HalsteadCounter_N2(HalsteadCounter_N):
    #     def count(self, marker, _unused):
    #         text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
    #         self.marker = marker
    #         if marker.group == api.Marker.T.PREPROCESSOR:
    #             return  # preprocessor are operators only
    #         if marker.group == api.Marker.T.STRING:
    #             # Entire string literal counts as one operand
    #             if text:
    #                 self.inc_dictcounter(text); self.result += 1
    #             return

    #         if marker.group != api.Marker.T.CODE:
    #             return

    #         lex = CppLexer(text)
    #         for kind, tok in lex.tokens():
    #             if kind in ("number","char","string","typespec"):
    #                 self.inc_dictcounter(tok); self.result += 1
    #             elif kind == "id":
    #                 # identifiers are operands (not reserved operator-words)
    #                 self.inc_dictcounter(tok); self.result += 1
    #             # kw_op and sym_op are operators, ignore here

    class HalsteadCounter_N2_cpp(HalsteadCounter_N2):
        pass

    class HalsteadCounter_N2_java(HalsteadCounter_N2):
        def count(self, marker, pattern_to_search):
            text = self.data.get_content()[marker.get_offset_begin():marker.get_offset_end()]
            self.marker = marker
            if marker.group == api.Marker.T.PREPROCESSOR:
                return
            if marker.group == api.Marker.T.STRING:
                if text:
                    self.inc_dictcounter(text); self.result += 1
                return
            for match in pattern_to_search.finditer(text):
                self.result += self.increment(match)

    # ------------------------- Distinct counts ---------------------------------
    class HalsteadCounter_n1(HalsteadCounter_n): pass
    class HalsteadCounter_n2(HalsteadCounter_n): pass
