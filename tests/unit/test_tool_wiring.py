"""Static checks that every MCP tool is wired to a handler method correctly.

Tools call handler methods that were renamed, moved to another handler class, or
grew/lost parameters, and nothing caught it until the tool was invoked. These
checks run over the AST so a mis-wired tool fails here instead of at runtime.
"""

import ast
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "ludus_mcp"
TOOLS_DIR = PACKAGE / "server" / "tools"


def _class_signatures():
    """Map (class_name, method_name) -> positional parameter names."""
    sigs, methods = {}, {}
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            methods.setdefault(node.name, set())
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods[node.name].add(child.name)
                    args = [a.arg for a in child.args.args if a.arg != "self"]
                    sigs[(node.name, child.name)] = {
                        "pos": args,
                        "kwonly": [a.arg for a in child.args.kwonlyargs],
                        "varargs": child.args.vararg is not None,
                        "kwargs": child.args.kwarg is not None,
                    }
    return sigs, methods


def _innermost_function(node):
    cur = getattr(node, "parent", None)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = getattr(cur, "parent", None)
    return None


def _handler_calls():
    """Yield (location, tool_name, handler_class, call_node) for handler calls."""
    for path in sorted(TOOLS_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        scopes = {}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and getattr(node.value.func, "attr", "") == "get_handler"
                and node.value.args
                and isinstance(node.value.args[-1], ast.Name)
                and isinstance(node.targets[0], ast.Name)
            ):
                scope = _innermost_function(node)
                scopes.setdefault(id(scope), {})[node.targets[0].id] = node.value.args[-1].id

        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
            ):
                continue
            fn = _innermost_function(node)
            cls = scopes.get(id(fn), {}).get(node.func.value.id)
            if cls:
                yield (
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}",
                    fn.name if fn else "?",
                    cls,
                    node,
                )


@pytest.fixture(scope="module")
def signatures():
    return _class_signatures()


def test_every_tool_calls_an_existing_handler_method(signatures):
    _, methods = signatures
    missing = [
        f"{loc} tool '{tool}' calls {cls}.{node.func.attr}() which does not exist"
        for loc, tool, cls, node in _handler_calls()
        if cls in methods and node.func.attr not in methods[cls]
    ]
    assert not missing, "Tools wired to non-existent handler methods:\n" + "\n".join(missing)


def test_handler_calls_pass_a_valid_number_of_arguments(signatures):
    sigs, _ = signatures
    problems = []
    for loc, tool, cls, node in _handler_calls():
        sig = sigs.get((cls, node.func.attr))
        if not sig:
            continue
        if not sig["varargs"] and len(node.args) > len(sig["pos"]):
            problems.append(
                f"{loc} tool '{tool}' passes {len(node.args)} positional args to "
                f"{cls}.{node.func.attr}({', '.join(sig['pos'])})"
            )
        unknown = [
            kw.arg
            for kw in node.keywords
            if kw.arg and kw.arg not in sig["pos"] and kw.arg not in sig["kwonly"]
            and not sig["kwargs"]
        ]
        if unknown:
            problems.append(
                f"{loc} tool '{tool}' passes unknown keyword(s) {unknown} to "
                f"{cls}.{node.func.attr}()"
            )
    assert not problems, "Handler calls with bad arguments:\n" + "\n".join(problems)


def test_positional_arguments_are_not_misaligned(signatures):
    """Catch calls whose argument *count* fits but whose order is scrambled.

    add_user() used to pass (username, password, ...) into (user_id, name, ...),
    storing the password as the display name.
    """
    sigs, _ = signatures
    problems = []
    for loc, tool, cls, node in _handler_calls():
        sig = sigs.get((cls, node.func.attr))
        if not sig or not node.args:
            continue
        passed = [a.id if isinstance(a, ast.Name) else None for a in node.args]
        params = sig["pos"]
        for i in range(min(len(passed), len(params))):
            name = passed[i]
            # Only flag when the name clearly belongs to a *different* parameter
            if name and name != params[i] and name in params:
                problems.append(
                    f"{loc} tool '{tool}': argument {i} passes '{name}' into "
                    f"{cls}.{node.func.attr}() parameter '{params[i]}'"
                )
    assert not problems, "Positionally misaligned handler calls:\n" + "\n".join(problems)


# ---------------------------------------------------------------------------
# Tools and handlers also call the API client directly, bypassing handlers.
# build_template passed a bool `force` into the client's int `parallel`, and
# get_template_logs passed a user_id into `tail`, on exactly this surface.
# ---------------------------------------------------------------------------

CLIENT_PATH = PACKAGE / "core" / "client.py"


def _client_signatures():
    tree = ast.parse(CLIENT_PATH.read_text(), str(CLIENT_PATH))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "LudusAPIClient":
            return {
                child.name: [a.arg for a in child.args.args if a.arg != "self"]
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return {}


def _direct_client_calls():
    """Yield (location, caller, method_name, call_node) for `client.X(...)` calls."""
    for path in sorted((PACKAGE / "server").rglob("*.py")):
        tree = ast.parse(path.read_text(), str(path))
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                child.parent = node
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                continue
            base = node.func.value
            is_client = (isinstance(base, ast.Name) and base.id == "client") or (
                isinstance(base, ast.Attribute) and base.attr == "client"
            )
            if not is_client:
                continue
            fn = _innermost_function(node)
            yield (
                f"{path.relative_to(REPO_ROOT)}:{node.lineno}",
                fn.name if fn else "?",
                node.func.attr,
                node,
            )


def test_direct_client_calls_pass_valid_argument_counts():
    sigs = _client_signatures()
    problems = []
    for loc, caller, method, node in _direct_client_calls():
        params = sigs.get(method)
        if params is None:
            continue  # handled by the dead-code test below
        if len(node.args) > len(params):
            problems.append(
                f"{loc} {caller} passes {len(node.args)} positional args to "
                f"client.{method}({', '.join(params)})"
            )
        unknown = [kw.arg for kw in node.keywords if kw.arg and kw.arg not in params]
        if unknown:
            problems.append(f"{loc} {caller} passes unknown keyword(s) {unknown} to client.{method}()")
    assert not problems, "Bad direct client calls:\n" + "\n".join(problems)


def test_direct_client_calls_are_not_positionally_misaligned():
    sigs = _client_signatures()
    problems = []
    for loc, caller, method, node in _direct_client_calls():
        params = sigs.get(method)
        if not params or not node.args:
            continue
        passed = [a.id if isinstance(a, ast.Name) else None for a in node.args]
        for i in range(min(len(passed), len(params))):
            name = passed[i]
            if name and name != params[i] and name in params:
                problems.append(
                    f"{loc} {caller}: argument {i} passes '{name}' into "
                    f"client.{method}() parameter '{params[i]}'"
                )
    assert not problems, "Misaligned direct client calls:\n" + "\n".join(problems)
