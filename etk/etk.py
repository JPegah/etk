from typing import List, Dict
import spacy, copy, json, os, jsonpath_ng, importlib, logging
from etk.tokenizer import Tokenizer
from etk.document import Document
from etk.etk_exceptions import InvalidJsonPathError
from etk.etk_module import ETKModule
from etk.etk_exceptions import ErrorPolicy, NotGetETKModuleError


class ETK(object):

    def __init__(self, kg_schema=None, modules=None, extract_error_policy="process"):
        self.parser = jsonpath_ng.parse
        self.default_nlp = spacy.load('en_core_web_sm')
        self.default_tokenizer = Tokenizer(copy.deepcopy(self.default_nlp))
        self.parsed = dict()
        self.kg_schema = kg_schema
        if modules:
            if type(modules) == str:
                self.em_lst = self.load_ems(modules)
            elif issubclass(modules, ETKModule):
                self.em_lst = [modules(self)]
            else:
                raise NotGetETKModuleError("Not getting extraction module")

        if extract_error_policy.lower() == "throw_extraction":
            self.error_policy = ErrorPolicy.THROW_EXTRACTION
        if extract_error_policy.lower() == "throw_document":
            self.error_policy = ErrorPolicy.THROW_DOCUMENT
        if extract_error_policy.lower() == "raise_error":
            self.error_policy = ErrorPolicy.RAISE
        else:
            self.error_policy = ErrorPolicy.PROCESS

    def create_document(self, doc: Dict, mime_type: str = None, url: str = "http://ex.com/123") -> Document:
        """
        Factory method to wrap input JSON docs in an ETK Document object.

        Args:
            doc (object): a JSON object containing a document in CDR format.
            mime_type (str): if doc is a string, the mime_type tells what it is
            url (str): if the doc came from the web, specifies the URL for it

        Returns: wrapped Document

        """
        return Document(self, doc, mime_type, url)

    def parse_json_path(self, jsonpath):
    
        """
        Parse a jsonpath

        Args:
            jsonpath: str

        Returns: a parsed json path

        """

        if jsonpath not in self.parsed:
            try:
                self.parsed[jsonpath] = self.parser(jsonpath)
            except Exception:
                raise InvalidJsonPathError("Invalid Json Path")

        return self.parsed[jsonpath]

    def process_ems(self, doc: Document):
        """
        Factory method to wrap input JSON docs in an ETK Document object.

        Args:
            doc (Document): process on this document

        Returns: a Document object and a KnowledgeGraph object

        """
        for a_em in self.em_lst:
            if a_em.document_selector(doc):
                a_em.process_document(doc)

        return doc, doc.kg

    @staticmethod
    def load_glossary(file_path: str, read_json=False) -> List[str]:
        """
        A glossary is a text file, one entry per line.

        Args:
            file_path (str): path to a text file containing a glossary.
            read_json (bool): set True if the glossary is in json format
        Returns: List of the strings in the glossary.
        """
        with open(file_path) as fp:
            if read_json:
                return json.load(fp)
            return fp.read().splitlines()

    @staticmethod
    def load_spacy_rule(file_path: str) -> Dict:
        """
        A spacy rule file is a json file.

        Args:
            file_path (str): path to a text file containing a spacy rule sets.

        Returns: Dict as the representation of spacy rules
        """
        with open(file_path) as fp:
            return json.load(fp)

    def load_ems(self, modules_path: str):
        """
        Load all extraction modules from the path

        Args:
            modules_path: str

        Returns:

        """
        modules_path = modules_path.strip(".").strip("/")
        em_lst = []
        try:
            for file_name in os.listdir(modules_path):
                if file_name.startswith("em_") and file_name.endswith(".py"):
                    this_module = importlib.import_module(modules_path + "." + file_name[:-3])
                    for em in self.classes_in_module(this_module):
                        em_lst.append(em(self))
        except:
            raise NotGetETKModuleError("Wrong file path for ETK modules")

        try:
            em_lst = self.topological_sort(em_lst)
        except:
            raise NotGetETKModuleError("Topological sort for ETK modules fails")

        if not em_lst:
            raise NotGetETKModuleError("No ETK module in dir, module file should start with em_, end with .py")
        return em_lst

    @staticmethod
    def topological_sort(lst: List[ETKModule]) -> List[ETKModule]:
        """
        Return topological order of ems

        Args:
            lst: List[ExtractionModule]

        Returns: List[ExtractionModule]

        """
        "TODO"
        return lst

    @staticmethod
    def classes_in_module(module) -> List:
        """
        Return all classes with super class ExtractionModule

        Args:
            module:

        Returns: List of classes

        """
        md = module.__dict__
        return [
            md[c] for c in md if (
                    isinstance(md[c], type) and
                    issubclass(md[c], ETKModule
                               ) and
                    md[c].__module__ == module.__name__)
        ]
