"""Corpus dependent setup of the annotation tool.
"""

from ..browser.html import H
from ..core.helpers import console
from ..core.files import readYaml, fileExists, APP_CONFIG


ERROR = "error"

TOOLKEY = "ner"
"""The name of this annotation tool.

This name is used

*   in directory paths on the file system to find the data that is managed by this tool;
*   as a key to address the in-memory data that belongs to this tool;
*   as a prefix to modularize the Flask app for this tool within the encompassing
    TF browser Flask app and also it CSS files.
"""

SET_ENT = "🟰"
SET_SHEET = "🧾"
SET_MAIN = "🖍️"

DEFAULT_SETTINGS = """
entityType: ent
entitySet: "{entityType}-nodes"

bucketType: chunk

strFeature: str
afterFeature: after

features:
  - eid
  - kind

keywordFeatures:
  - kind

defaultValues:
  kind: PER

spaceEscaped: false
"""

NONE = "⌀"
"""GUI representiation of an empty value.

Used to mark the fact that an occurrence does not have a value for an entity feature.
That happens when an occurrence is not part of an entity.
"""

EMPTY = "␀"
"""GUI representation of the empty string.

If an entity feature has the empty string as value, and we want to create a button for
it, this is the label we draw on that button.
"""

STYLES = dict(
    minus=dict(bg="#ffaaaa;"),
    plus=dict(bg="#aaffaa;"),
    replace=dict(bg="#ffff88;"),
    free=dict(
        ff="monospace",
        fz="small",
        fw="normal",
        fg="black",
        bg="white",
    ),
    free_active=dict(
        fg="black",
        bg="yellow",
    ),
    free_bordered=dict(
        bg="white",
        br="0.5rem",
        bw="1pt",
        bs="solid",
        bc="white",
        p="0.4rem",
        m="0.1rem 0.2rem",
    ),
    free_bordered_active=dict(
        bw="1pt",
        bs="solid",
        bc="yellow",
    ),
    keyword=dict(
        ff="monospace",
        fz="medium",
        fw="bold",
        fg="black",
        bg="white",
    ),
    keyword_active=dict(
        fg="black",
        bg="yellow",
    ),
    keyword_bordered=dict(
        bg="white",
        br="0.5rem",
        bw="1pt",
        bs="solid",
        bc="white",
        p="0.3rem",
        m="0.1rem 0.2rem",
    ),
    keyword_bordered_active=dict(
        bw="1pt",
        bs="solid",
        bc="yellow",
    ),
)
"""CSS style configuration for entity features.

Here we define properties of the styling of the entity features and their
values.
Since these features are defined in configuration, we cannot work with a fixed
style sheet.

We divide entity features in *keyword* features and *free* features.
The typical keyword feature is `kind`, it has a limited set of values.
The typical free feature is `eid`, it has an unbounded number of values.

As it is now, we could have expressed this in a fixed style sheet.
But if we open up to allowing for more entity features, we can use this setup
to easily configure the formatting of them.

However, we should move these definitions to the `ner.yaml` file then, so that the
only place of configuration is that YAML file, and not this file.
"""


def makeCss(features, keywordFeatures):
    """Generates CSS for the tool.

    The CSS for this tool has a part that depends on the choice of entity features.
    For now, the dependency is mild: keyword features such as `kind` are formatted
    differently than features with an unbounded set of values, such as `eid`.

    Parameters
    ----------
    features, keywordFeatures: iterable
        What the features are and what the keyword features are.
        These derive ultimately from the corpus-dependent `ner/config.yaml`.
    """
    propMap = dict(
        ff="font-family",
        fz="font-size",
        fw="font-weight",
        fg="color",
        bg="background-color",
        bw="border-width",
        bs="border-style",
        bc="border-color",
        br="border-radius",
        p="padding",
        m="margin",
    )

    def makeBlock(manner):
        props = STYLES[manner]
        defs = [f"\t{propMap[abb]}: {val};\n" for (abb, val) in props.items()]
        return H.join(defs)

    def makeCssDef(selector, *blocks):
        return selector + " {\n" + H.join(blocks) + "}\n"

    css = []

    for feat in features:
        manner = "keyword" if feat in keywordFeatures else "free"

        plain = makeBlock(manner)
        bordered = makeBlock(f"{manner}_bordered")
        active = makeBlock(f"{manner}_active")
        borderedActive = makeBlock(f"{manner}_bordered_active")

        css.extend(
            [
                makeCssDef(f".{feat}", plain),
                makeCssDef(f".{feat}.active", active),
                makeCssDef(f"span.{feat}_sel,button.{feat}_sel", plain, bordered),
                makeCssDef(f"button.{feat}_sel[st=v]", borderedActive, active),
            ]
        )

    featureCss = H.join(css, sep="\n")
    allCss = H.style(featureCss, type="text/css")
    return allCss


class Settings:
    def __init__(self):
        """Provides configuration details.

        There is fixed configuration, that is not intended to be modifiable by users.
        These configuration values are put in variables in this module, which
        other modules can import.

        There is also customisable configuration, meant to adapt the tool to the
        specifics of a corpus.
        Those configuration values are read from a YAML file, located in a directory
        `ner` next to the `tf` data of the corpus.
        """
        specDir = self.specDir

        nerSpec = f"{specDir}/{APP_CONFIG}"
        kwargs = (
            dict(asFile=nerSpec) if fileExists(nerSpec) else dict(text=DEFAULT_SETTINGS)
        )
        settings = readYaml(preferTuples=True, **kwargs)
        settings.entitySet = (settings.entitySet or "entity-nodes").format(
            entityType=settings.entityType
        )
        self.settings = settings

        features = self.settings.features
        keywordFeatures = self.settings.keywordFeatures
        self.settings.summaryIndices = tuple(
            i for i in range(len(features)) if features[i] in keywordFeatures
        )

    def console(self, msg, **kwargs):
        """Print something to the output.

        This works exactly as `tf.core.helpers.console`

        When the silent member of the object is True, the message will be suppressed.
        """
        silent = self.silent

        if not silent:
            console(msg, **kwargs)

    def consoleLine(self, isError, indent, msg):
        silent = self.silent

        if silent and not isError:
            return

        tabs = "  " * indent
        head = "-" * len(msg)

        if isError is None:
            console("")
            console(f"{tabs}{head}")

        console(f"{tabs}{msg}\n", error=isError)

        if isError is None:
            console(f"{tabs}{head}")