"""
Code parsing with Tree-sitter for polyglot code analysis
Extracts function definitions and metadata
"""

import tree_sitter_python
from tree_sitter import Language, Parser
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ParsingError(Exception):
    """Base exception for parsing errors"""
    pass


class CodeParser:
    """
    Tree-sitter based code parser for extracting functions
    
    Features:
    - Extract function definitions with metadata
    - Get function name, code, and line numbers
    - Robust error handling
    """
    
    def __init__(self, language: str = "python"):
        """
        Initialize parser with specified language
        
        Args:
            language: Programming language (currently only 'python' supported)
        """
        self.language = language
        
        if language == "python":
            try:
                # Modern tree-sitter-python API
                self.ts_language = Language(tree_sitter_python.language())
                self.parser = Parser(self.ts_language)
                logger.info("Python parser initialized successfully")
            except Exception as e:
                raise ParsingError(f"Failed to initialize Python parser: {e}") from e
        else:
            raise ParsingError(f"Unsupported language: {language}")
    
    def parse_functions(self, file_content: str) -> List[Dict]:
        """
        Extract all function definitions from source code
        
        Args:
            file_content: Source code as string
            
        Returns:
            List of function metadata dictionaries with:
            - name: Function name
            - code: Full function code
            - start_line: Starting line number (1-indexed)
            - end_line: Ending line number (1-indexed)
            - docstring: Function docstring if present
            
        Raises:
            ParsingError: If parsing fails
        """
        try:
            # Parse the code
            tree = self.parser.parse(bytes(file_content, "utf-8"))
            root_node = tree.root_node
            
            functions = []
            
            # Find all function definitions
            self._extract_functions_recursive(root_node, file_content, functions)
            
            logger.info(f"Extracted {len(functions)} functions")
            return functions
            
        except Exception as e:
            raise ParsingError(f"Failed to parse code: {e}") from e
    
    def _extract_functions_recursive(
        self,
        node,
        source_code: str,
        functions: List[Dict]
    ):
        """
        Recursively extract function definitions from AST
        
        Args:
            node: Tree-sitter node
            source_code: Original source code
            functions: List to append found functions to
        """
        # Check if this node is a function definition
        if node.type == "function_definition":
            function_data = self._extract_function_data(node, source_code)
            if function_data:
                functions.append(function_data)
        
        # Recursively process child nodes
        for child in node.children:
            self._extract_functions_recursive(child, source_code, functions)
    
    def _extract_function_data(self, node, source_code: str) -> Optional[Dict]:
        """
        Extract metadata from a function definition node
        
        Args:
            node: Function definition node
            source_code: Original source code
            
        Returns:
            Dictionary with function metadata or None if extraction fails
        """
        try:
            # Get function name
            name_node = node.child_by_field_name("name")
            if not name_node:
                return None
            
            function_name = source_code[name_node.start_byte:name_node.end_byte]
            
            # Get full function code
            function_code = source_code[node.start_byte:node.end_byte]
            
            # Get line numbers (1-indexed)
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # Extract docstring if present
            docstring = self._extract_docstring(node, source_code)
            
            return {
                "name": function_name,
                "code": function_code,
                "start_line": start_line,
                "end_line": end_line,
                "docstring": docstring,
                "node_type": "function"
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract function data: {e}")
            return None
    
    def _extract_docstring(self, function_node, source_code: str) -> Optional[str]:
        """
        Extract docstring from function definition
        
        Args:
            function_node: Function definition node
            source_code: Original source code
            
        Returns:
            Docstring content or None if not present
        """
        try:
            body_node = function_node.child_by_field_name("body")
            if not body_node:
                return None
            
            # Check first statement in body
            for child in body_node.children:
                if child.type == "expression_statement":
                    # Check if it's a string (docstring)
                    for expr_child in child.children:
                        if expr_child.type == "string":
                            docstring_raw = source_code[expr_child.start_byte:expr_child.end_byte]
                            # Clean up quotes
                            docstring = docstring_raw.strip('"""').strip("'''").strip('"').strip("'")
                            return docstring.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract docstring: {e}")
            return None
    
    def parse_classes(self, file_content: str) -> List[Dict]:
        """
        Extract all class definitions from source code
        
        Args:
            file_content: Source code as string
            
        Returns:
            List of class metadata dictionaries
        """
        try:
            tree = self.parser.parse(bytes(file_content, "utf-8"))
            root_node = tree.root_node
            
            classes = []
            self._extract_classes_recursive(root_node, file_content, classes)
            
            logger.info(f"Extracted {len(classes)} classes")
            return classes
            
        except Exception as e:
            raise ParsingError(f"Failed to parse classes: {e}") from e
    
    def _extract_classes_recursive(self, node, source_code: str, classes: List[Dict]):
        """Recursively extract class definitions"""
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                class_name = source_code[name_node.start_byte:name_node.end_byte]
                class_code = source_code[node.start_byte:node.end_byte]
                
                classes.append({
                    "name": class_name,
                    "code": class_code,
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "node_type": "class"
                })
        
        for child in node.children:
            self._extract_classes_recursive(child, source_code, classes)
    
    def get_imports(self, file_content: str) -> List[Dict]:
        """
        Extract import statements
        
        Args:
            file_content: Source code as string
            
        Returns:
            List of import dictionaries with module names
        """
        try:
            tree = self.parser.parse(bytes(file_content, "utf-8"))
            root_node = tree.root_node
            
            imports = []
            
            for child in root_node.children:
                if child.type in ("import_statement", "import_from_statement"):
                    import_code = file_content[child.start_byte:child.end_byte]
                    imports.append({
                        "code": import_code,
                        "line": child.start_point[0] + 1,
                        "type": child.type
                    })
            
            return imports
            
        except Exception as e:
            logger.warning(f"Failed to extract imports: {e}")
            return []


def create_parser(language: str = "python") -> CodeParser:
    """
    Factory function to create a CodeParser
    
    Args:
        language: Programming language
        
    Returns:
        CodeParser instance
    """
    return CodeParser(language=language)
