import sys

import pytest

from sentry_sdk.utils import event_from_exception

try:
    # Python 3.11
    from builtins import ExceptionGroup  # type: ignore
except ImportError:
    # Python 3.10 and below
    ExceptionGroup = None


minimum_python_311 = pytest.mark.skipif(
    sys.version_info < (3, 11), reason="ExceptionGroup tests need Python >= 3.11"
)


@minimum_python_311
def test_exceptiongroup():
    exception_group = None

    try:
        try:
            raise RuntimeError("something")
        except RuntimeError:
            raise ExceptionGroup(
                "nested",
                [
                    ValueError(654),
                    ExceptionGroup(
                        "imports",
                        [
                            ImportError("no_such_module"),
                            ModuleNotFoundError("another_module"),
                        ],
                    ),
                    TypeError("int"),
                ],
            )
    except ExceptionGroup as e:
        exception_group = e

    (event, _) = event_from_exception(
        exception_group,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    values = event["exception"]["values"]

    # For this test the stacktrace and the module is not important
    for x in values:
        if "stacktrace" in x:
            del x["stacktrace"]
        if "module" in x:
            del x["module"]

    expected_values = [
        {
            "mechanism": {
                "exception_id": 6,
                "handled": False,
                "parent_id": 0,
                "source": "exceptions[2]",
                "type": "chained",
            },
            "type": "TypeError",
            "value": "int",
        },
        {
            "mechanism": {
                "exception_id": 5,
                "handled": False,
                "parent_id": 3,
                "source": "exceptions[1]",
                "type": "chained",
            },
            "type": "ModuleNotFoundError",
            "value": "another_module",
        },
        {
            "mechanism": {
                "exception_id": 4,
                "handled": False,
                "parent_id": 3,
                "source": "exceptions[0]",
                "type": "chained",
            },
            "type": "ImportError",
            "value": "no_such_module",
        },
        {
            "mechanism": {
                "exception_id": 3,
                "handled": False,
                "is_exception_group": True,
                "parent_id": 0,
                "source": "exceptions[1]",
                "type": "chained",
            },
            "type": "ExceptionGroup",
            "value": "imports",
        },
        {
            "mechanism": {
                "exception_id": 2,
                "handled": False,
                "parent_id": 0,
                "source": "exceptions[0]",
                "type": "chained",
            },
            "type": "ValueError",
            "value": "654",
        },
        {
            "mechanism": {
                "exception_id": 1,
                "handled": False,
                "parent_id": 0,
                "source": "__context__",
                "type": "chained",
            },
            "type": "RuntimeError",
            "value": "something",
        },
        {
            "mechanism": {
                "exception_id": 0,
                "handled": False,
                "is_exception_group": True,
                "type": "test_suite",
            },
            "type": "ExceptionGroup",
            "value": "nested",
        },
    ]

    assert values == expected_values


@minimum_python_311
def test_exceptiongroup_simple():
    exception_group = None

    try:
        raise ExceptionGroup(
            "simple",
            [
                RuntimeError("something strange's going on"),
            ],
        )
    except ExceptionGroup as e:
        exception_group = e

    (event, _) = event_from_exception(
        exception_group,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    exception_values = event["exception"]["values"]

    assert len(exception_values) == 2

    assert exception_values[0]["type"] == "RuntimeError"
    assert exception_values[0]["value"] == "something strange's going on"
    assert exception_values[0]["mechanism"] == {
        "type": "chained",
        "handled": False,
        "exception_id": 1,
        "source": "exceptions[0]",
        "parent_id": 0,
    }

    assert exception_values[1]["type"] == "ExceptionGroup"
    assert exception_values[1]["value"] == "simple"
    assert exception_values[1]["mechanism"] == {
        "type": "test_suite",
        "handled": False,
        "exception_id": 0,
        "is_exception_group": True,
    }
    frame = exception_values[1]["stacktrace"]["frames"][0]
    assert frame["module"] == "tests.test_exceptiongroup"
    assert frame["context_line"] == "        raise ExceptionGroup("


@minimum_python_311
def test_exception_chain_cause():
    exception_chain_cause = ValueError("Exception with cause")
    exception_chain_cause.__context__ = TypeError("Exception in __context__")
    exception_chain_cause.__cause__ = TypeError(
        "Exception in __cause__"
    )  # this implicitly sets exception_chain_cause.__suppress_context__=True

    (event, _) = event_from_exception(
        exception_chain_cause,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    expected_exception_values = [
        {
            "mechanism": {
                "handled": False,
                "type": "test_suite",
            },
            "module": None,
            "type": "TypeError",
            "value": "Exception in __cause__",
        },
        {
            "mechanism": {
                "handled": False,
                "type": "test_suite",
            },
            "module": None,
            "type": "ValueError",
            "value": "Exception with cause",
        },
    ]

    exception_values = event["exception"]["values"]
    assert exception_values == expected_exception_values


@minimum_python_311
def test_exception_chain_context():
    exception_chain_context = ValueError("Exception with context")
    exception_chain_context.__context__ = TypeError("Exception in __context__")

    (event, _) = event_from_exception(
        exception_chain_context,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    expected_exception_values = [
        {
            "mechanism": {
                "handled": False,
                "type": "test_suite",
            },
            "module": None,
            "type": "TypeError",
            "value": "Exception in __context__",
        },
        {
            "mechanism": {
                "handled": False,
                "type": "test_suite",
            },
            "module": None,
            "type": "ValueError",
            "value": "Exception with context",
        },
    ]

    exception_values = event["exception"]["values"]
    assert exception_values == expected_exception_values


@minimum_python_311
def test_simple_exception():
    simple_excpetion = ValueError("A simple exception")

    (event, _) = event_from_exception(
        simple_excpetion,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    expected_exception_values = [
        {
            "mechanism": {
                "handled": False,
                "type": "test_suite",
            },
            "module": None,
            "type": "ValueError",
            "value": "A simple exception",
        },
    ]

    exception_values = event["exception"]["values"]
    assert exception_values == expected_exception_values


@minimum_python_311
def test_exceptiongroup_starlette_collapse():
    """
    Simulates the Starlette collapse_excgroups() pattern where a single-exception
    ExceptionGroup is caught and the inner exception is unwrapped and re-raised.

    See: https://github.com/Kludex/starlette/blob/0e88e92b592bfa11fd92e331869a8d49ba34b541/starlette/_utils.py#L79-L87

    When using FastAPI with multiple BaseHTTPMiddleware instances, anyio wraps
    exceptions in ExceptionGroups. Starlette's collapse_excgroups() then unwraps
    single-exception groups and re-raises the inner exception.

    When re-raising the unwrapped exception, Python implicitly sets __context__
    on it pointing back to the ExceptionGroup (because the re-raise happens
    inside the except block that caught the ExceptionGroup), creating a cycle:

        ExceptionGroup -> .exceptions[0] -> ValueError -> __context__ -> ExceptionGroup

    Without cycle detection in exceptions_from_error(), this causes infinite
    recursion and a silent RecursionError that drops the event.

    The cycle edge (ValueError -> ExceptionGroup) is emitted as an
    exception_ref node instead of being expanded, and ValueError itself is
    serialized exactly once.
    """
    exception_group = None

    try:
        try:
            raise RuntimeError("something")
        except RuntimeError:
            raise ExceptionGroup(
                "nested",
                [
                    ValueError(654),
                ],
            )
    except ExceptionGroup as exc:
        exception_group = exc
        unwrapped = exc.exceptions[0]
        try:
            raise unwrapped
        except Exception:
            pass

    (event, _) = event_from_exception(
        exception_group,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    values = event["exception"]["values"]

    # For this test the stacktrace and the module is not important
    for x in values:
        if "stacktrace" in x:
            del x["stacktrace"]
        if "module" in x:
            del x["module"]

    expected_values = [
        {
            "mechanism": {
                "exception_id": 3,
                "handled": False,
                "parent_id": 2,
                "source": "__context__",
                "type": "chained",
                "exception_ref": 0,
            },
        },
        {
            "mechanism": {
                "exception_id": 2,
                "handled": False,
                "parent_id": 0,
                "source": "exceptions[0]",
                "type": "chained",
            },
            "type": "ValueError",
            "value": "654",
        },
        {
            "mechanism": {
                "exception_id": 1,
                "handled": False,
                "parent_id": 0,
                "source": "__context__",
                "type": "chained",
            },
            "type": "RuntimeError",
            "value": "something",
        },
        {
            "mechanism": {
                "exception_id": 0,
                "handled": False,
                "is_exception_group": True,
                "type": "test_suite",
            },
            "type": "ExceptionGroup",
            "value": "nested",
        },
    ]

    assert values == expected_values


@minimum_python_311
def test_cyclic_exception_group_cause():
    """
    Test case related to `test_exceptiongroup_starlette_collapse` above. We want to make sure that
    the same cyclic loop cannot happen via the __cause__ as well as the __context__
    """

    original = ValueError("original error")
    group = ExceptionGroup("unhandled errors in a TaskGroup", [original])
    original.__cause__ = group
    original.__suppress_context__ = True

    # When the ExceptionGroup is the top-level exception, exceptions_from_error
    # is called directly (not walk_exception_chain which has cycle detection).
    (event, _) = event_from_exception(
        group,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    exception_values = event["exception"]["values"]

    # Must produce a finite list of exceptions without hitting RecursionError.
    assert len(exception_values) >= 1

    by_id = {
        v["mechanism"]["exception_id"]: v for v in exception_values
    }

    # The group (id 0) is the root; the ValueError (id 1) is its only child.
    assert by_id[0]["type"] == "ExceptionGroup"
    assert by_id[1]["type"] == "ValueError"
    assert by_id[1]["mechanism"]["source"] == "exceptions[0]"
    assert by_id[1]["mechanism"]["parent_id"] == 0

    # ValueError.__cause__ points back at the group: the cycle is truncated with
    # a reference node pointing at the already-serialized group, never expanded.
    refs = [v for v in exception_values if "exception_ref" in v["mechanism"]]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["mechanism"]["exception_ref"] == 0
    assert ref["mechanism"]["source"] == "__cause__"
    assert ref["mechanism"]["parent_id"] == 1
    assert "type" not in ref and "stacktrace" not in ref


@minimum_python_311
def test_deeply_nested_cyclic_exception_group():
    """
    Related to the `test_exceptiongroup_starlette_collapse` test above.

    Testing a more complex cycle: ExceptionGroup -> ValueError -> __cause__ ->
    ExceptionGroup (nested) -> TypeError -> __cause__ -> original ExceptionGroup
    """
    inner_error = TypeError("inner")
    outer_error = ValueError("outer")
    inner_group = ExceptionGroup("inner group", [inner_error])
    outer_group = ExceptionGroup("outer group", [outer_error])

    # Create a cycle spanning two ExceptionGroups
    outer_error.__cause__ = inner_group
    outer_error.__suppress_context__ = True
    inner_error.__cause__ = outer_group
    inner_error.__suppress_context__ = True

    (event, _) = event_from_exception(
        outer_group,
        client_options={
            "include_local_variables": True,
            "include_source_context": True,
            "max_value_length": 1024,
        },
        mechanism={"type": "test_suite", "handled": False},
    )

    exception_values = event["exception"]["values"]
    assert len(exception_values) >= 1

    # Every serialized exception (non-reference) appears once.
    concrete = [v for v in exception_values if "type" in v]
    exc_types = [v["type"] for v in concrete]
    assert exc_types.count("ExceptionGroup") == 2
    assert exc_types.count("ValueError") == 1
    assert exc_types.count("TypeError") == 1

    # The cycle that closes during traversal (TypeError.__cause__ -> outer
    # group, which is still active on the DFS path) is truncated with a
    # reference instead of being expanded. The other back edge is beyond the
    # truncation point and is therefore not traversed.
    refs = [v for v in exception_values if "exception_ref" in v["mechanism"]]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["mechanism"]["source"] == "__cause__"
    assert ref["mechanism"]["exception_ref"] == 0  # points at outer group
    assert ref["mechanism"]["parent_id"] == 3  # edge originates at TypeError
    assert "value" not in ref and "stacktrace" not in ref


CLIENT_OPTIONS = {
    "include_local_variables": True,
    "include_source_context": True,
    "max_value_length": 1024,
}
MECHANISM = {"type": "test_suite", "handled": False}


def _values(exception):
    (event, _) = event_from_exception(
        exception,
        client_options=CLIENT_OPTIONS,
        mechanism=dict(MECHANISM),
    )
    values = event["exception"]["values"]
    for value in values:
        value.pop("stacktrace", None)
        value.pop("module", None)
    return values


def _concrete(values):
    """Nodes that carry a full serialized exception."""
    return [v for v in values if "type" in v]


def _references(values):
    """Nodes that only reference another serialized node."""
    return [v for v in values if "exception_ref" in v["mechanism"]]


@minimum_python_311
def test_shared_leaf_serialized_once():
    """
    The same exception object reachable through two branches of a group (as
    happens when concurrent tasks propagate the *same* error object) must be
    serialized exactly once; the second occurrence is an exception_ref.
    """
    shared = ValueError("shared failure")
    group = ExceptionGroup("parallel", [shared, shared])

    values = _values(group)

    concrete = _concrete(values)
    assert [v["type"] for v in concrete] == ["ValueError", "ExceptionGroup"]

    value_errors = [v for v in concrete if v["type"] == "ValueError"]
    assert len(value_errors) == 1
    serialized_id = value_errors[0]["mechanism"]["exception_id"]

    references = _references(values)
    assert len(references) == 1
    ref = references[0]
    assert ref["mechanism"]["exception_ref"] == serialized_id
    assert ref["mechanism"]["source"] == "exceptions[1]"
    assert ref["mechanism"]["parent_id"] == 0
    # references never duplicate the payload
    assert "value" not in ref
    assert "stacktrace" not in ref


@minimum_python_311
def test_shared_leaf_in_nested_groups_diamond():
    """
    Diamond: root -> [group_a, group_b] and both group_a/group_b contain the
    same leaf object. The leaf is serialized once and the second occurrence
    references it.
    """
    leaf = RuntimeError("diamond")
    group_a = ExceptionGroup("a", [leaf])
    group_b = ExceptionGroup("b", [leaf])
    root = ExceptionGroup("root", [group_a, group_b])

    values = _values(root)

    runtime_errors = [v for v in _concrete(values) if v["type"] == "RuntimeError"]
    assert len(runtime_errors) == 1
    serialized_id = runtime_errors[0]["mechanism"]["exception_id"]

    references = _references(values)
    assert len(references) == 1
    assert references[0]["mechanism"]["exception_ref"] == serialized_id

    # Tree integrity: every non-root parent_id resolves to a serialized node
    # and every reference resolves too.
    concrete_ids = {v["mechanism"]["exception_id"] for v in _concrete(values)}
    for v in values:
        mechanism = v["mechanism"]
        if "parent_id" in mechanism:
            assert mechanism["parent_id"] in concrete_ids
        if "exception_ref" in mechanism:
            assert mechanism["exception_ref"] in concrete_ids


@minimum_python_311
def test_exception_tree_ids_are_stable():
    """Building the same exception tree repeatedly yields identical ids."""

    def structure():
        leaf = RuntimeError("diamond")
        root = ExceptionGroup(
            "root",
            [ExceptionGroup("a", [leaf]), ExceptionGroup("b", [leaf])],
        )
        values = _values(root)
        return [
            (
                v["mechanism"].get("exception_id"),
                v.get("type"),
                v["mechanism"].get("parent_id"),
                v["mechanism"].get("source"),
                v["mechanism"].get("exception_ref"),
            )
            for v in values
        ]

    assert structure() == structure()


@minimum_python_311
def test_cause_vs_context_distinction_preserved():
    """
    __cause__ (raise ... from ...) and __context__ (implicit) must remain
    distinguishable via mechanism.source and the chain edges must be linear
    (child's parent is the containing exception, not the root).
    """
    cause = KeyError("direct")
    with_cause = RuntimeError("with cause")
    with_cause.__cause__ = cause
    with_cause.__suppress_context__ = True

    context = TypeError("implicit")
    with_context = RuntimeError("with context")
    with_context.__context__ = context

    group = ExceptionGroup("g", [with_cause, with_context])
    values = _values(group)
    by_id = {v["mechanism"]["exception_id"]: v for v in values}

    # with_cause -> __cause__ -> KeyError, edge parent is the RuntimeError node
    runtime_nodes = {
        v["value"]: v for v in values if v["type"] == "RuntimeError"
    }
    cause_holder = runtime_nodes["with cause"]
    context_holder = runtime_nodes["with context"]

    cause_node = next(v for v in values if v["type"] == "KeyError")
    context_node = next(v for v in values if v["type"] == "TypeError")

    assert cause_node["mechanism"]["source"] == "__cause__"
    assert cause_node["mechanism"]["parent_id"] == cause_holder["mechanism"][
        "exception_id"
    ]

    assert context_node["mechanism"]["source"] == "__context__"
    assert context_node["mechanism"]["parent_id"] == context_holder["mechanism"][
        "exception_id"
    ]

    # The group's two direct children use exceptions[i] sources.
    assert cause_holder["mechanism"]["source"] == "exceptions[0]"
    assert context_holder["mechanism"]["source"] == "exceptions[1]"
    assert by_id[0]["type"] == "ExceptionGroup"


@minimum_python_311
def test_cancellation_branch_marked():
    """
    Cancellation branches (CancelledError members of an ExceptionGroup) are
    flagged with mechanism.is_cancellation so they can be grouped separately
    from genuine error branches.
    """
    import asyncio

    group = BaseExceptionGroup(
        "tasks", [RuntimeError("real error"), asyncio.CancelledError()]
    )

    values = _values(group)

    by_type = {}
    for v in _concrete(values):
        by_type.setdefault(v["type"], []).append(v)

    runtime = by_type["RuntimeError"][0]
    cancellation = by_type["CancelledError"][0]

    assert runtime["mechanism"].get("is_cancellation") is None
    assert cancellation["mechanism"].get("is_cancellation") is True
    assert cancellation["mechanism"]["source"] == "exceptions[1]"

    # The group container itself is not a cancellation.
    root = next(v for v in values if "is_exception_group" in v["mechanism"])
    assert root["mechanism"].get("is_cancellation") is None


@minimum_python_311
def test_scrubbing_preserves_tree_structure():
    """
    Event scrubbing (sensitive frame vars) must not touch the tree metadata in
    mechanism (ids/parent_id/exception_ref/source), so grouping structure
    remains stable after scrubbing.
    """
    leaf = ValueError("secret failure")
    root = ExceptionGroup("root", [ExceptionGroup("a", [leaf]), leaf])

    values_before = _values(root)

    # Scrub the whole event the way the client would.
    (event, _) = event_from_exception(
        root, client_options=CLIENT_OPTIONS, mechanism=dict(MECHANISM)
    )
    from sentry_sdk.scrubber import EventScrubber

    EventScrubber(recursive=True).scrub_event(event)

    values_after = event["exception"]["values"]

    def tree_signature(values):
        return sorted(
            (
                v["mechanism"].get("exception_id"),
                v["mechanism"].get("parent_id"),
                v["mechanism"].get("source"),
                v["mechanism"].get("exception_ref"),
                v["mechanism"].get("is_exception_group"),
                v.get("type"),
            )
            for v in values
        )

    assert tree_signature(values_before) == tree_signature(values_after)


@minimum_python_311
def test_cycle_truncation_reference_is_valid_and_finite():
    """
    A self-referencing chain inside a group terminates and the truncation
    reference always points at an existing serialized node.
    """
    leaf = ValueError("loopy")
    leaf.__context__ = leaf  # direct self cycle

    group = ExceptionGroup("g", [leaf])
    values = _values(group)

    concrete_ids = {v["mechanism"]["exception_id"] for v in _concrete(values)}
    references = _references(values)
    assert len(references) == 1
    assert references[0]["mechanism"]["exception_ref"] in concrete_ids
    assert references[0]["mechanism"]["source"] == "__context__"

    # The leaf is serialized once with its full payload.
    assert len([v for v in values if v.get("type") == "ValueError"]) == 1
