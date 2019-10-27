import logging
import typing as t
import warnings
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

import black
from htmlmin import minify
from yaml import dump

from moodlmth.const import LEAF_TAGS
from moodlmth.protocols import PConverter

RENDERER_TEMPLATE = """
@renders(lr(f"{{ASSETS}}/{varname}.txt", static=True))
def {varname}():
    return {{}}
"""

TEMPLATE = """
from htmldoom import doctype, render, renders, loadraw as lr
from htmldoom.yaml_loader import loadyaml as ly

ASSETS = "assets"
COMPONENTS = f"{{ASSETS}}/components.yml"

{raw_renderers}
@renders(doctype("{doctype}"), ly(COMPONENTS))
def document():
    return {raw_elements}


if __name__ == "__main__":
    print(render(document()))
"""


@dataclass
class RendererCall:
    varname: str

    def __repr__(self):
        return f"{self.varname}()"


@dataclass
class LeafTag:
    parent: t.Union["LeafTag", "CompositeTag", "Document"]
    tagname: str
    attributes: t.Dict[str, str]

    def render(self):
        return {self.tagname: [self.attributes]}


@dataclass
class CompositeTag:
    parent: t.Union["LeafTag", "CompositeTag", "Document"]
    tagname: str
    attributes: t.Dict[str, str]
    children: t.List[t.Union[LeafTag, "CompositeTag", str]]

    def render(self):
        if not self.attributes:
            return {self.tagname: [[c.render() for c in self.children]]}
        return {self.tagname: [self.attributes, [c.render() for c in self.children]]}


@dataclass
class Txt:
    parent: t.Union["LeafTag", "CompositeTag", "Document"]
    content: str

    def render(self):
        return self.content


@dataclass
class Comment:
    parent: t.Union["LeafTag", "CompositeTag", "Document"]
    content: str

    def render(self):
        return "# {}".format(self.content.replace("\n", "\n# "))


@dataclass(frozen=False)
class Document:
    doctype: t.Optional[str]
    children: t.List[t.Union[LeafTag, "CompositeTag", str]]

    def render(self):
        return [c.render() for c in self.children]


@dataclass(frozen=False)
class RawFile:
    varname: str
    content: str


class Converter(HTMLParser, PConverter):
    def __init__(self, fast: bool = False, logger: logging.Logger = None):
        super().__init__(convert_charrefs=True)
        self.log = logger if logger else logging.getLogger(__name__)
        self.doc = Document(doctype=None, children=[])
        self._elem = self.doc
        self.raw_files: t.List[RawFile] = []
        self.fast = fast
        self.black_file_mode: black.FileMode = black.FileMode(
            target_versions={}, is_pyi=False, line_length=79, string_normalization=True
        )

    def handle_decl(self, decl) -> None:
        if decl.lower().startswith("doctype "):
            self.doc.doctype = decl[8:]
            return
        raise ValueError(f"Unknown declaration: {decl}")  # pragma: nocover

    def handle_comment(self, data) -> None:
        # TODO: use ramuel.yaml for comments
        pass

    def handle_data(self, data) -> None:
        if not data:  # pragma: nocover
            return

        tagname = None if self._elem is self.doc else self._elem.tagname

        if tagname in ["script", "style", "textarea"]:
            rf = RawFile(f"raw{len(self.raw_files)}", data)
            self.raw_files.append(rf)
            self._elem.children.append(
                Txt(parent=self._elem, content=f"{{{rf.varname}}}")
            )
            return

        self._elem.children.append(Txt(parent=self._elem, content=data))

    def _attributes(self, attrs):
        return {k: (True if v is None else v) for k, v in attrs}

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        self.log.debug(f"Handling leaf tag: {tag}")
        self._elem.children.append(
            LeafTag(parent=self._elem, tagname=tag, attributes=self._attributes(attrs))
        )

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in LEAF_TAGS:
            self.handle_startendtag(tag, attrs)
            return
        self.log.debug(f"Starting composite tag: {tag}")
        self._elem.children.append(
            CompositeTag(
                parent=self._elem,
                tagname=tag,
                attributes=self._attributes(attrs),
                children=[],
            )
        )
        self._elem = self._elem.children[-1]

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._elem is self.doc or not self._elem or not self._elem.parent:
            raise ValueError(f"Tag closed before starting: {tag}")

        self.log.debug(f"Closing composite tag: {tag}")
        if tag != self._elem.tagname:
            warnings.warn(f"Tag was never closed: {self._currtag.tagname}", Warning)
        self._elem = self._elem.parent

    def convert(self, raw_html):
        self.feed(minify(raw_html, remove_empty_space=True))

        p = Path("assets")
        if not p.exists():
            p.mkdir()

        raw_renderers = []
        raw_elements = {}

        for rf in self.raw_files:
            fpath = str(p / f"{rf.varname}.txt")

            raw_renderers.append(RENDERER_TEMPLATE.format(varname=rf.varname))
            raw_elements[rf.varname] = RendererCall(rf.varname)

            with open(fpath, "w") as f:
                f.write(rf.content)

        with open(str(p / "components.yml"), "w") as f:
            dump(self.doc.render(), f)

        result = TEMPLATE.format(
            doctype=self.doc.doctype if self.doc.doctype else "html",
            raw_renderers="\n".join(raw_renderers),
            raw_elements=repr(raw_elements),
        )
        return black.format_file_contents(
            result, fast=self.fast, mode=self.black_file_mode
        )
