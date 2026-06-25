from .BaseJUnitXMLParser import BaseJUnitXMLParser


class JUnitXMLParser(BaseJUnitXMLParser):

    framework_name = "junit"

    @property
    def supported_formats(self):
        return ["junit_xml"]

    @property
    def priority(self):
        return 100  #lowest - generic catch-all

    def can_parse(self, content: str, filename: str = "") -> bool:

        return ((filename.endswith(".xml")
                or content.lstrip().startswith("<"))
            and "<testcase" in content
            and "classname=" in content
        )