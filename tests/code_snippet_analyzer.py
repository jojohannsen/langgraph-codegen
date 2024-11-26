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
        parameter_variables = set()
        class_instance_variables = set()
        global_variables = set()
        used_variables = set()
        code_snippet = code_snippet.replace("async ", "")
        class Visitor(ast.NodeVisitor):
            def __init__(self, builtin_names):
                self.builtin_names = builtin_names
                super().__init__()

            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    # Check if we're in a class context and it's an instance variable (self.x)
                    if isinstance(node.parent, ast.Attribute) and isinstance(node.parent.value, ast.Name) and node.parent.value.id == 'self':
                        class_instance_variables.add(node.parent.attr)
                    else:
                        defined_variables.add(node.id)
                elif isinstance(node.ctx, ast.Load):
                    if node.id not in self.builtin_names:
                        used_variables.add(node.id)

            def visit_Global(self, node):
                for name in node.names:
                    global_variables.add(name)

            def visit_Import(self, node):
                for alias in node.names:
                    defined_variables.add(alias.name)

            def visit_ImportFrom(self, node):
                pass

            def visit_FunctionDef(self, node):
                defined_variables.add(node.name)
                for arg in node.args.args:
                    if arg.arg != 'self':  # Skip 'self' parameter
                        parameter_variables.add(arg.arg)
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
            # Add parent references to make it easier to check context
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child.parent = node
            visitor = Visitor(self.builtin_names)
            visitor.visit(tree)
        except SyntaxError:
            return set(), set(), set(), set(), set(), set(), []

        imports = import_statements(defined_variables, used_variables)
        undefined_variables = {var for var in used_variables 
                             if var not in defined_variables and 
                             var not in builtin_names and
                             var not in parameter_variables and
                             var not in class_instance_variables and
                             var not in global_variables and
                             var not in [x.split(' ')[-1] for x in imports]}
        
        return (defined_variables, parameter_variables, class_instance_variables, 
                global_variables, used_variables, undefined_variables, imports)
    
    def add_snippet(self, name, code):
        defined, parameter_variables, class_instance_variables, global_variables, used, undefined, import_statements = self.analyze_code(code)
        self.snippets[name] = {
            'code': code,
            'defined': defined,
            'parameter_variables': parameter_variables,
            'class_instance_variables': class_instance_variables,
            'global_variables': global_variables,
            'used': used,
            'undefined': undefined,
            'imports': import_statements
        }
        return self.snippets[name]
    
    def analyze_all_snippets(self):
        all_defined = set().union(*(data['defined'] for data in self.snippets.values()))
        all_parameters = set().union(*(data['parameter_variables'] for data in self.snippets.values()))
        all_instance_vars = set().union(*(data['class_instance_variables'] for data in self.snippets.values()))
        all_globals = set().union(*(data['global_variables'] for data in self.snippets.values()))
        all_defined.update(self.builtin_names)  # Add built-in names to all_defined

        for snippet_name, data in self.snippets.items():
            defined = data['defined']
            parameter_vars = data['parameter_variables']
            instance_vars = data['class_instance_variables']
            global_vars = data['global_variables']
            used = data['used']
            
            # A variable is undefined if it's used but not defined anywhere
            undefined = used - all_defined - all_parameters - all_instance_vars - all_globals
            # A variable is defined elsewhere if it's used but defined in another snippet
            defined_elsewhere = used.intersection(all_defined | all_parameters | all_instance_vars | all_globals) - defined - parameter_vars - instance_vars - global_vars

            self.snippets[snippet_name]['analysis'] = {
                'defined': defined,
                'parameter_variables': parameter_vars,
                'class_instance_variables': instance_vars,
                'global_variables': global_vars,
                'undefined': undefined,
                'defined_elsewhere': defined_elsewhere
            }

    def get_snippet_summary(self, snippet_name):
        if snippet_name not in self.snippets:
            return None
        analysis = self.snippets[snippet_name]['analysis']
        return (
            analysis['defined'],
            analysis['parameter_variables'],
            analysis['class_instance_variables'],
            analysis['global_variables'],
            analysis['undefined'],
            analysis['defined_elsewhere']
        )

    def get_all_summaries(self):
        return {
            snippet_name: self.get_snippet_summary(snippet_name)
            for snippet_name in self.snippets
        }
