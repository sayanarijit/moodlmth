"Performs and conversion."

import builtins
import logging
import re
import sys
import typing as t
import warnings
from html.parser import HTMLParser
from keyword import kwlist

import black
from htmldoom import elements
from htmlmin import minify

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
    def html(self) -> e.HTML:
        """Document HTML."""
        return {html}

    @property
    def head(self) -> e.Head:
        """Document head."""

        return {head}

    @property
    def body(self) -> e.Body:
        """Document body."""

        return {body}


if __name__ == "__main__":
    print(Layout())
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

    def render(self) -> str:
        return f"e.{self.tagname}{self.tagattrs}({repr(self.value)})"

    def __repr__(self) -> str:
        if self.parent and (
            self.parent.tagname == "Style" or self.parent.tagname == "Script"
        ):
            return repr(self.value)
        if self.tagname == "_Text":
            return repr(self.value)
        if self.tagname == "_RawText":
            return f"b{repr(self.value)}"
        return self.render()


class TagNode:
    def __init__(
        self, tagname: t.Optional[str] = None, tagattrs: t.Optional[str] = None
    ):
        self.tagname: t.Optional[str] = tagname
        self.tagattrs: str = tagattrs if tagattrs else ""
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

    def render(self) -> str:
        if not self.tagname:
            return ", ".join(map(repr, self.children))
        if not self.children:
            return f"e.{self.tagname}{self.tagattrs}"
        return f"e.{self.tagname}{self.tagattrs}({', '.join(map(repr, self.children))})"

    def __repr__(self) -> str:
        if self.tagname == "Title":
            return "self.title"
        if self.tagname == "HTML":
            return "self.html"
        if self.tagname == "Body":
            return "self.body"
        if self.tagname == "Head":
            return "self.head"
        return self.render()


class Converter(HTMLParser):
    """Converts raw HTML into python source code.
    
    Example:
        
        >>> converter = Converter()
        >>> converter.convert("<html><body>Hello</body></html>")
    """

    def __init__(self, fast=False, logger=None) -> None:
        super().__init__(convert_charrefs=True)
        self.template: str = TEMPLATE
        self.reserved_keywords: t.Set[str] = set(dir(builtins) + kwlist)
        self.tagnames: t.Dict[str, str] = {}
        self.tagmap: t.Dict[str, elements._Tag] = {}
        self.black_file_mode: black.FileMode = black.FileMode(
            target_versions={}, is_pyi=False, line_length=79, string_normalization=True
        )
        self.fast = fast
        self._tagtree: TagNode = TagNode()
        self._currtag: t.TagNode = self._tagtree
        self._doctype: t.Optional[str] = None
        self._title: t.Optional[str] = None
        self._html: t.Optional[str] = None
        self._head: t.Optional[str] = None
        self._body: t.Optional[str] = None
        self.log = logger if logger else logging.getLogger(__name__)
        self._init_tagmap()

    def _init_tagmap(self) -> None:
        for name in elements.__all__:
            thing: object = getattr(elements, name)
            if not thing or not hasattr(thing, "tagname"):
                continue
            while hasattr(thing, "__wrapped__"):
                thing = thing.__wrapped__
            self.tagnames[thing.tagname] = thing.__name__
            self.tagmap[thing.tagname] = thing

    def handle_decl(self, decl) -> None:
        if decl.lower().startswith("doctype "):
            self._doctype = f"e.DocType({repr(decl[8:])})"
            return
        raise ValueError(f"Unknown declaration: {decl}")

    def handle_comment(self, data) -> None:
        self._currtag.addchild(TagLeaf("_Comment", value=data))

    def handle_data(self, data) -> None:
        if not data:
            return

        if self._currtag.tagname in ["Script", "Style"]:
            self._currtag.addchild(TagLeaf("_RawText", value=data))
            return
        self._currtag.addchild(TagLeaf("_Text", value=data))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        self.log.debug(f"Handling leaf tag: {tag}")
        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}")
            self.tagnames[tag] = f"_new_adhoc_composite_tag({repr(tag)})"
            self.tagmap[tag] = elements._new_adhoc_composite_tag(tag)
        fmt_attrs = self._fmt_attrs(attrs)
        self._currtag.addchild(TagNode(self.tagnames[tag], tagattrs=fmt_attrs))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}")
            self.tagnames[tag] = f"_new_adhoc_composite_tag({repr(tag)})"
            self.tagmap[tag] = elements._new_adhoc_composite_tag(tag)

        prevtag = self.tagmap[tag]

        if issubclass(prevtag, elements._LeafTag):
            self.handle_startendtag(tag, attrs)
            return

        self.log.debug(f"Starting composite tag: {tag}")
        tag = tag.lower()
        fmt_attrs = self._fmt_attrs(attrs)
        self._currtag.addchild(TagNode(self.tagnames[tag], tagattrs=fmt_attrs))
        self._currtag = self._currtag.children[-1]

    def handle_endtag(self, tag):
        tag = tag.lower()
        if not self._currtag or not self._currtag.parent:
            raise ValueError(f"Tag closed before starting: {tag}")

        prevtag = self.tagmap[tag]
        if issubclass(prevtag, elements._LeafTag):
            self.handle_startendtag(tag, "")
            return

        self.log.debug(f"Closing composite tag: {tag}")
        if self.tagnames[tag] != self._currtag.tagname:
            warnings.warn(f"Tag was never closed: {self._currtag.tagname}", Warning)

        if tag == "title":
            self._title = self._currtag.render()
        if tag == "html":
            self._html = self._currtag.render()
        if tag == "head":
            self._head = self._currtag.render()
        if tag == "body":
            self._body = self._currtag.render()

        self._currtag = self._currtag.parent

    def _fmt_attrs(self, attrs) -> str:
        _attrs, _props = [], {}

        use_expansion = False
        for k, v in attrs:
            if not use_expansion and re.sub(r"[a-zA-Z_]", "", k):
                use_expansion = True

            if v is None:
                _attrs.append(k)
            else:
                _props[k] = v

        if (
            not use_expansion
            and len((set(_attrs) | set(_props)) & self.reserved_keywords) > 0
        ):
            use_expansion = True

        fmt_attrs = ", ".join(repr(x) for x in _attrs)
        fmt_props = f"**{_props}" if _props else ""
        if not use_expansion and _props:
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
        self.feed(minify(raw_html, remove_empty_space=True))
        result = self.template.format(
            doctype=self._doctype,
            title=self._title,
            html=self._html,
            head=self._head,
            body=self._body,
        )
        return black.format_file_contents(
            result, fast=self.fast, mode=self.black_file_mode
        )
