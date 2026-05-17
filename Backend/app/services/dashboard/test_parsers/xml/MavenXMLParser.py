from .BaseJUnitXMLParser import BaseJUnitXMLParser


class MavenXMLParser(BaseJUnitXMLParser):

    framework_name = "maven"

    @property
    def supported_formats(self):
        return ["maven_xml"]

    @property
    def priority(self):
        return 15 # Higher than generic JUnit (20), but lower than explicit Pytest (10)

    def can_parse(self, content: str, filename: str = "") -> bool:

        #priority 1: Filename has Maven-specific markers
        if (
            "surefire" in filename.lower()
            or "failsafe" in filename.lower()
            or "target/" in filename.lower()
        ):
            return "<testcase" in content

        #priority 2: maven/java convention package.Class notation
        if "<testcase" in content and "classname=" in content:
            return "." in content and "<testcase" in content
        
        return False