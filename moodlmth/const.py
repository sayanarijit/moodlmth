from enum import Enum


class Syntax(Enum):
    python = "Python"
    yaml = "YAML"


LEAF_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "foreignobject",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "meter",
    "param",
    "source",
    "track",
    "wbr",
}
