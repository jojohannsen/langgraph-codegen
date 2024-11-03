import ast
import builtins

import_dict = {
    # key: what we are importing, value: complete import statement
    'END': 'from langgraph.graph import END',
    'START': 'from langgraph.graph import START',
    'StateGraph': 'from langgraph.graph import StateGraph',
    'add_messages': 'from langgraph.graph.message import add_messages',
    'TypedDict': 'from typing import TypedDict',
    'Annotated': 'from typing import Annotated'
}

builtin_names = { "ValueError" }

def import_statements(defined, used):
    return [import_dict[name] for name in used - defined if import_dict.get(name, None)]

class CodeSnippetAnalyzer:
    def __init__(self):
        self.snippets = {}
        self.builtin_names = set(dir(builtins))

    def analyze_code(self, code_snippet):
        defined_variables = set()
        used_variables = set()
        code_snippet = code_snippet.replace("async ", "")
        class Visitor(ast.NodeVisitor):
            def __init__(self, builtin_names):
                self.builtin_names = builtin_names
                super().__init__()

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    defined_variables.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    if node.id not in self.builtin_names:
                        used_variables.add(node.id)

            def visit_Import(self, node):
                for alias in node.names:
                    defined_variables.add(alias.name)

            def visit_ImportFrom(self, node):
                pass

            def visit_FunctionDef(self, node):
                defined_variables.add(node.name)
                for arg in node.args.args:
                    defined_variables.add(arg.arg)
                self.generic_visit(node)  # Visit the function body

            def visit_ClassDef(self, node):
                defined_variables.add(node.name)
                self.generic_visit(node)  # Visit the class body

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    used_variables.add(node.func.id)
                self.generic_visit(node)

            def visit_ExceptHandler(self, node):
                if node.name:
                    defined_variables.add(node.name)
                self.generic_visit(node)

        try:
            tree = ast.parse(code_snippet)
            visitor = Visitor(self.builtin_names)
            visitor.visit(tree)
        except SyntaxError:
            return set(), set(), set(), []

        imports = import_statements(defined_variables, used_variables)
        undefined_variables = {var for var in used_variables 
                             if var not in defined_variables and 
                             var not in builtin_names and
                             var not in [x.split(' ')[-1] for x in imports]}
        
        return defined_variables, used_variables, undefined_variables, imports
    
    def add_snippet(self, name, code):
        defined, used, undefined, import_statements = self.analyze_code(code)
        self.snippets[name] = {
            'code': code,
            'defined': defined,
            'used': used,
            'undefined': undefined,
            'imports': import_statements
        }
        return self.snippets[name]
    
    def analyze_all_snippets(self):
        all_defined = set().union(*(data['defined'] for data in self.snippets.values()))
        all_defined.update(self.builtin_names)  # Add built-in names to all_defined

        for snippet_name, data in self.snippets.items():
            defined = data['defined']
            used = data['used']
            undefined = used - all_defined - defined  # Change here
            defined_elsewhere = used.intersection(all_defined) - defined

            self.snippets[snippet_name]['analysis'] = {
                'defined': defined,
                'undefined': undefined,
                'defined_elsewhere': defined_elsewhere
            }

    def get_snippet_summary(self, snippet_name):
        if snippet_name not in self.snippets:
            return None
        analysis = self.snippets[snippet_name]['analysis']
        return (
            analysis['defined'],
            analysis['undefined'],
            analysis['defined_elsewhere']
        )

    def get_all_summaries(self):
        return {
            snippet_name: self.get_snippet_summary(snippet_name)
            for snippet_name in self.snippets
        }
