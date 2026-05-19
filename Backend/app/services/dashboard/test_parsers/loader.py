def load_parsers():
    from .json.GenericJsonParser import GenericJSONParser
    from .json.JestJsonParser import JestJSONParser
    from .json.MochaJsonParser import MochaJSONParser
    from .json.PlaywrightJsonParser import PlaywrightJSONParser
    from .json.RSpecJsonParser import RSpecJSONParser

    from .xml.JUnitXMLParser import JUnitXMLParser
    from .xml.MavenXMLParser import MavenXMLParser
    from .xml.NUnitXMLParser import NUnitXMLParser
    from .xml.PytestXMLParser import PytestXMLParser
    from .xml.TrxXMLParser import TrxXMLParser

    from .logs.log_parsers import UnittestLogsParser, MinitestLogsParser, RspecLogsParser, GoLogsParser, PytestLogsParser, JestLogsParser
    
    print("[loader] All test parsers loaded and registered", flush=True)

    
