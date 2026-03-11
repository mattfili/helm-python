import os
import tempfile
import shutil

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import fs


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="helm-fs-test-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def agent():
    return create_fairlead(FairleadOptions(permissions={"fs.*": "allow"})).use(fs())


class TestFsSkill:
    @pytest.mark.asyncio
    async def test_reads_a_file(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "test.txt")
        with open(path, "w") as f:
            f.write("hello world")

        result = await agent().fs.read_file(path)
        assert result == {"content": "hello world"}

    @pytest.mark.asyncio
    async def test_writes_a_file(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "out.txt")
        await agent().fs.write_file(path, "written content")

        with open(path) as f:
            assert f.read() == "written content"

    @pytest.mark.asyncio
    async def test_lists_directory_entries(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "a.txt"), "w") as f:
            f.write("a")
        with open(os.path.join(tmp_dir, "b.ts"), "w") as f:
            f.write("b")
        os.mkdir(os.path.join(tmp_dir, "sub"))

        result = await agent().fs.readdir(tmp_dir)
        assert len(result["entries"]) == 3
        names = sorted(e.name for e in result["entries"])
        assert names == ["a.txt", "b.ts", "sub"]

        sub = next(e for e in result["entries"] if e.name == "sub")
        assert sub.is_directory is True
        assert sub.is_file is False

    @pytest.mark.asyncio
    async def test_lists_with_glob_filter(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "a.txt"), "w") as f:
            f.write("a")
        with open(os.path.join(tmp_dir, "b.ts"), "w") as f:
            f.write("b")

        result = await agent().fs.readdir(tmp_dir, {"glob": "*.txt"})
        assert len(result["entries"]) == 1
        assert result["entries"][0].name == "a.txt"

    @pytest.mark.asyncio
    async def test_creates_directory_recursively(self, tmp_dir: str) -> None:
        dir_path = os.path.join(tmp_dir, "a", "b", "c")
        await agent().fs.mkdir(dir_path)
        assert os.path.isdir(dir_path)

    @pytest.mark.asyncio
    async def test_mkdir_noop_if_exists(self, tmp_dir: str) -> None:
        dir_path = os.path.join(tmp_dir, "existing")
        os.mkdir(dir_path)
        await agent().fs.mkdir(dir_path)  # should not raise

    @pytest.mark.asyncio
    async def test_stats_a_file(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "stat-me.txt")
        with open(path, "w") as f:
            f.write("hello")

        result = await agent().fs.stat(path)
        assert result.size == 5
        assert result.is_file is True
        assert result.is_directory is False
        assert result.modified
        assert result.created

    @pytest.mark.asyncio
    async def test_stats_a_directory(self, tmp_dir: str) -> None:
        dir_path = os.path.join(tmp_dir, "stat-dir")
        os.mkdir(dir_path)

        result = await agent().fs.stat(dir_path)
        assert result.is_file is False
        assert result.is_directory is True

    @pytest.mark.asyncio
    async def test_stat_throws_for_nonexistent(self, tmp_dir: str) -> None:
        with pytest.raises(Exception):
            await agent().fs.stat(os.path.join(tmp_dir, "nope"))

    @pytest.mark.asyncio
    async def test_removes_a_file(self, tmp_dir: str) -> None:
        path = os.path.join(tmp_dir, "to-remove.txt")
        with open(path, "w") as f:
            f.write("gone soon")

        await agent().fs.rm(path)
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_renames_a_file(self, tmp_dir: str) -> None:
        old = os.path.join(tmp_dir, "old.txt")
        new = os.path.join(tmp_dir, "new.txt")
        with open(old, "w") as f:
            f.write("moveme")

        await agent().fs.rename(old, new)
        assert not os.path.exists(old)
        with open(new) as f:
            assert f.read() == "moveme"

    @pytest.mark.asyncio
    async def test_returns_cwd(self) -> None:
        result = await agent().fs.cwd()
        assert result == os.getcwd()
