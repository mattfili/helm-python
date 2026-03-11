import os
import tempfile
import shutil

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import edit


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="fairlead-edit-test-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def agent():
    return create_fairlead(FairleadOptions(permissions={"edit.*": "allow"})).use(edit())


class TestEditSkill:
    @pytest.mark.asyncio
    async def test_replaces_first_occurrence(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("foo bar foo baz")
        result = await agent().edit.replace(path, "foo", "qux")
        assert result == {"count": 1}
        with open(path) as f:
            assert f.read() == "qux bar foo baz"

    @pytest.mark.asyncio
    async def test_replaces_all_occurrences(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("foo bar foo baz foo")
        result = await agent().edit.replace(path, "foo", "qux", {"all": True})
        assert result == {"count": 3}
        with open(path) as f:
            assert f.read() == "qux bar qux baz qux"

    @pytest.mark.asyncio
    async def test_returns_zero_count_no_match(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("hello world")
        result = await agent().edit.replace(path, "xyz", "abc")
        assert result == {"count": 0}
        with open(path) as f:
            assert f.read() == "hello world"

    @pytest.mark.asyncio
    async def test_inserts_at_line(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2\nline3")
        await agent().edit.insert(path, 2, "inserted")
        with open(path) as f:
            assert f.read() == "line1\ninserted\nline2\nline3"

    @pytest.mark.asyncio
    async def test_inserts_at_beginning(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("line1\nline2")
        await agent().edit.insert(path, 1, "header")
        with open(path) as f:
            assert f.read() == "header\nline1\nline2"

    @pytest.mark.asyncio
    async def test_removes_lines(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("a\nb\nc\nd\ne")
        await agent().edit.remove_lines(path, 2, 4)
        with open(path) as f:
            assert f.read() == "a\ne"

    @pytest.mark.asyncio
    async def test_batch_apply(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("a\nb\nc\nd\ne")
        await agent().edit.apply(path, [
            {"type": "insert", "line": 2, "content": "X"},
            {"type": "remove", "start": 4, "end": 4},
            {"type": "replace", "start": 5, "end": 5, "content": "E!"},
        ])
        with open(path) as f:
            assert f.read() == "a\nX\nb\nc\nE!"
