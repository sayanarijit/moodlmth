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

from moodlmth.const import LEAF_TAGS
from moodlmth.protocols import PConverter

TEMPLATE = """
from htmldoom import base as b
from htmldoom import elements as e
from htmldoom import render as _render
from htmldoom import renders

doctype = _render({doctype})

contents = _render({body})


@renders({title})
def render_title(data):
    return {{}}


@renders({head})
def render_head(data, title_renderer=render_title):
    return {{"title": title_renderer(data=data)}}


@renders(e.body()("{{contents}}"))
def render_body(data) -> None:
    return {{'contents': contents}}


@renders({html})
def render_html(
    data,
    title_renderer=render_title,
    head_renderer=render_head,
    body_renderer=render_body,
):
    return {{
        "head": head_renderer(data=data, title_renderer=render_title),
        "body": body_renderer(data=data),
    }}


@renders("{{doctype}}{{html}}")
def render_document(
    data,
    title_renderer=render_title,
    head_renderer=render_head,
    body_renderer=render_body,
    html_renderer=render_html,
):
    return {{
        "doctype": doctype,
        "html": html_renderer(
            data=data,
            title_renderer=title_renderer,
            head_renderer=head_renderer,
            body_renderer=body_renderer,
        ),
    }}


def render(data):
    return render_document(data=data)


if __name__ == "__main__":
    print(render({{}}))
"""


class TagLeaf:
    def __init__(self, tagname, tagattrs="", value=""):
        self.tagname = tagname
        self.tagattrs = tagattrs
        self.value = value
        self.parent: t.Optional["TagNode"] = None
        self.next: t.Optional["TagNode"] = None
        self.prev: t.Optional["TagNode"] = None

    def render(self):
        return f"{self.tagname}{self.tagattrs}({repr(self.value)})"

    def __repr__(self):
        if self.tagname == "b.txt":
            return repr(self.value)
        if self.tagname == "b.raw":
            return f"b{repr(self.value)}"
        return self.render()


class TagNode:
    def __init__(
        self, tagname: t.Optional[str] = None, tagattrs: t.Optional[str] = None
    ):
        self.tagname: t.Optional[str] = tagname
        self.tagattrs = tagattrs if tagattrs else ""
        self.children: t.List[t.Union["TagNode", TagTree]] = []
        self.parent: t.Optional["TagNode"] = None
        self.next: t.Optional["TagNode"] = None
        self.prev: t.Optional["TagNode"] = None

    def addchild(self, childtag: "TagNode") -> None:
        self.children.append(childtag)
        childtag.parent = self

    def render(self):
        if not self.tagname or self.tagname == "e.body":
            return ", ".join(map(repr, self.children))
        if not self.children:
            return f"{self.tagname}{self.tagattrs}"
        return f"{self.tagname}{self.tagattrs}({', '.join(map(repr, self.children))})"

    def __repr__(self):
        if self.tagname in ["e.title", "e.html", "e.body", "e.head"]:
            return f'''"{{{self.tagname.lstrip('e.')}}}"'''
        return self.render()


class Converter(HTMLParser, PConverter):
    """Converts raw HTML into python source code.
    
    Example:
        
        >>> converter = Converter()
        >>> converter.convert("<html><body>Hello</body></html>")
    """

    def __init__(self, fast=False, logger=None) -> None:
        super().__init__(convert_charrefs=True)
        self.template = TEMPLATE
        self.reserved_keywords: t.Set[str] = set(dir(builtins) + kwlist)
        self.tagnames: t.Dict[str, str] = {}
        self.tagmap: t.Dict[str, callable] = {}
        self.black_file_mode: black.FileMode = black.FileMode(
            target_versions={}, is_pyi=False, line_length=79, string_normalization=True
        )
        self.fast: bool = fast
        self._tagtree: TagNode = TagNode()
        self._currtag: TagNode = self._tagtree
        self._doctype: str = ""
        self._title: str = ""
        self._html: str = ""
        self._head: str = ""
        self._body: str = ""
        self.log = logger if logger else logging.getLogger(__name__)
        self._init_tagmap()

    def _init_tagmap(self) -> None:
        for name in elements.__all__:
            tag: object = getattr(elements, name)
            tagname = name.rstrip("_").replace("_", "-")
            self.tagnames[tagname] = f"e.{name}"
            self.tagmap[tagname] = tag

    def handle_decl(self, decl) -> None:
        if decl.lower().startswith("doctype "):
            self._doctype = f"b.doctype({repr(decl[8:])})"
            return
        raise ValueError(f"Unknown declaration: {decl}")  # pragma: nocover

    def handle_comment(self, data) -> None:
        self._currtag.addchild(TagLeaf("b.comment", value=data))

    def handle_data(self, data) -> None:
        if not data:  # pragma: nocover
            return
        if self._currtag.tagname in ["e.script", "e.style", "e.textarea"]:
            self._currtag.addchild(TagLeaf("b.raw", value=data))
            return
        self._currtag.addchild(TagLeaf("b.txt", value=data))

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        self.log.debug(f"Handling leaf tag: {tag}")
        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}")
            self.tagnames[tag] = f"b.leaf_tag({repr(tag)})"
            self.tagmap[tag] = elements.leaf_tag(tag)
        fmt_attrs = self._fmt_attrs(attrs)
        self._currtag.addchild(TagNode(self.tagnames[tag], tagattrs=fmt_attrs))

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag not in self.tagmap:
            warnings.warn(f"Tag not found in htmldoom: {tag}")
            self.tagnames[tag] = f"b.composite_tag({repr(tag)})"
            self.tagmap[tag] = elements.composite_tag(tag)

        if tag in LEAF_TAGS:
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

    def _fmt_attrs(self, attrs):
        _attrs, _props = [], {}

        for k, v in attrs:
            if v is None:
                _attrs.append(k)
                continue

            k = k.replace("-", "_")
            if k in self.reserved_keywords:
                k = f"{k}_"
            _props[k] = v

        fmt_attrs = ", ".join(repr(x) for x in _attrs)
        fmt_props = ", ".join(f"{k}={repr(v)}" for k, v in _props.items())

        if _attrs and _props:
            return f"({fmt_attrs}, {fmt_props})"

        if _attrs:
            return f"({fmt_attrs})"

        return f"({fmt_props})"

    def convert(self, raw_html):
        """Do the conversion.
        
        raw_html: The raw html text to convert.
        """
        self.feed(minify(raw_html, remove_empty_space=True))
        result = self.template.format(
            doctype=self._doctype,
            title=self._title.replace("{", "{{").replace("}", "}}"),
            head=self._head.replace("{", "{{")
            .replace("}", "}}")
            .replace('"{{title}}"', '"{title}"'),
            html=self._html.replace("{", "{{")
            .replace("}", "}}")
            .replace('"{{head}}"', '"{head}"')
            .replace('"{{body}}"', '"{body}"'),
            body=self._body,
        )
        return black.format_file_contents(
            result, fast=self.fast, mode=self.black_file_mode
        )
