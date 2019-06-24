"Performs and conversion."

import builtins
import sys
import typing as t
import warnings
from html.parser import HTMLParser
from keyword import kwlist

import black
from htmldoom import elements

TEMPLATE = '''
from htmldoom import elements as e
from htmldoom.layouts import BaseLayout


class Layout(BaseLayout):
    """Layout class."""

    @property
    def doctype(self) -> e.DocType:
        """Document type."""

        return {doctype}

    @property
    def title(self) -> e.Title:
        """Document title."""

        return {title}

    @property
    def head(self) -> e.Head:
        """Document head."""

        return {head}

    @property
    def body(self) -> e.Body:
        """Document body."""

        return {body}
'''


class TagLeaf:
    def __init__(self, tagname: str, tagattrs: str = "", value: str = ""):
        self.tagname: str = tagname
        self.tagattrs: str = tagattrs
        self.value: str = value
        self.parent: t.Optional["TagNode"] = None
        self.next: t.Optional["TagNode"] = None
        self.prev: t.Optional["TagNode"] = None

    def addnext(self, nexttag: "TagNode") -> None:
        self.next = nexttag
        nexttag.prev = self
        nexttag.parent = self.parent

    def __repr__(self) -> str:
        return f"e.{self.tagname}{self.tagattrs}({repr(self.value)})"


class TagNode:
    def __init__(self, tagname: str, tagattrs: str = ""):
        self.tagname: str = tagname
        self.tagattrs: str = tagattrs
        self.children: t.List[t.Union["TagNode", TagTree]] = []
        self.parent: t.Optional["TagNode"] = None
        self.next: t.Optional["TagNode"] = None
        self.prev: t.Optional["TagNode"] = None

    def addnext(self, nexttag: "TagNode") -> None:
        self.next = nexttag
        nexttag.prev = self
        nexttag.parent = self.parent

    def addchild(self, childtag: "TagNode") -> None:
        self.children.append(childtag)
        childtag.parent = self

    def __repr__(self) -> str:
        if not self.children:
            return f"e.{self.tagname}{self.tagattrs}"
        return f"e.{self.tagname}{self.tagattrs}({', '.join(map(repr, self.children))})"


class Converter(HTMLParser):
    """Converts raw HTML into python source code.
    
    Example:
        
        >>> converter = Converter()
        >>> converter.convert("<html><body>Hello</body></html>")
    """

    def __init__(self, force=True) -> None:
        super().__init__(convert_charrefs=True)
        self.template: str = TEMPLATE
        self.reserved_keywords: t.Set[str] = set(dir(builtins) + kwlist)
        self.tagmap: t.Dict[str, str] = {}
        self.black_file_mode: black.FileMode = black.FileMode(
            target_versions={}, is_pyi=False, line_length=79, string_normalization=True
        )
        self.force = force
        self._tagtree: TagNode = TagNode("html")
        self._currtag: t.Optional[t.TagNode] = self._tagtree
        self._doctype: t.Optional[str] = None
        self._title: t.Optional[str] = None
        self._head: t.Optional[str] = None
        self._body: t.Optional[str] = None
        self._init_tagmap()

    def _init_tagmap(self) -> None:
        for name in elements.__all__:
            thing: object = getattr(elements, name)
            if not thing or not hasattr(thing, "tagname"):
                continue
            self.tagmap[thing.tagname] = thing.__name__

    def handle_decl(self, decl) -> None:
        if decl.lower().startswith("doctype "):
            self._doctype = f"e.DocType({repr(decl[8:])})"
            return
        raise ValueError(f"Unknown declaration: {decl}")

    def handle_comment(self, data) -> None:
        if not data.strip():
            return
        self._currtag.addchild(TagLeaf("_Comment", value=data))

    def handle_data(self, data) -> None:
        if not data.strip():
            return
        if self._currtag.tagname in ["Script", "Style"]:
            self._currtag.addchild(TagLeaf("_RawHtml", value=data))
            return
        self._currtag.addchild(TagLeaf("_Text", value=data))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}", Warning)
            return
        fmt_attrs = self._fmt_attrs(attrs)
        self._currtag.addchild(TagNode(self.tagmap[tag], tagattrs=fmt_attrs))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "html":
            return

        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}", Warning)
            return

        prevtag = getattr(elements, self.tagmap[tag])

        if issubclass(prevtag.__wrapped__, elements._LeafTag):
            self.handle_startendtag(tag, attrs)
            return

        tag = tag.lower()
        fmt_attrs = self._fmt_attrs(attrs)
        self._currtag.addchild(TagNode(self.tagmap[tag], tagattrs=fmt_attrs))
        self._currtag = self._currtag.children[-1]

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self._currtag or tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}", Warning)
            return

        if self.tagmap[tag] != self._currtag.tagname:
            warnings.warn(f"Tag was never closed: {self._currtag.tagname}", Warning)

        if tag == "title":
            self._title = repr(self._currtag)
        if tag == "head":
            self._head = repr(self._currtag)
        if tag == "body":
            self._body = repr(self._currtag)

        self._currtag = self._currtag.parent

    def _fmt_attrs(self, attrs) -> str:
        _attrs, _props = [], {}
        for k, v in attrs:
            if v is None:
                _attrs.append(k)
            else:
                _props[k] = v

        has_reserved_kw = False
        if len((set(_attrs) | set(_props)) & self.reserved_keywords) > 0:
            has_reserved_kw = True

        fmt_attrs = ", ".join(repr(x) for x in _attrs)
        fmt_props = f"**{_props}" if _props else ""
        if not has_reserved_kw and _props:
            fmt_props = ", ".join(f"{k}={repr(v)}" for k, v in _props.items())

        if _attrs and _props:
            return f"({fmt_attrs}, {fmt_props})"

        if _attrs:
            return f"({fmt_attrs})"

        return f"({fmt_props})"

    def convert(self, raw_html: str) -> str:
        """Do the conversion.
        
        raw_html: The raw html text to convert.
        """
        self.feed(raw_html)
        result = self.template.format(
            doctype=self._doctype, title=self._title, head=self._head, body=self._body
        )
        return black.format_file_contents(
            result, fast=self.force, mode=self.black_file_mode
        )
