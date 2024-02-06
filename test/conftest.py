import pytest
from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.json import JSONSnapshotExtension


@pytest.fixture
def snapshot_json(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """
    syrupyでJSONをsnapshotするためのfixture。

    Examples
    --------
    >>> def test_foo(snapshot_json: SnapshotAssertion):
    >>>     assert snapshot_json == {"key": "value"}
    """
    return snapshot.use_extension(JSONSnapshotExtension)
