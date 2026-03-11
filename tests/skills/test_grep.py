import os
import tempfile
import shutil

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import grep
from fairlead.skills._grep import GrepOptions


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="helm-grep-test-")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def agent(cwd: str):
    return create_fairlead(FairleadOptions(permissions={"grep.*": "allow"})).use(grep(cwd=cwd))


class TestGrepSkill:
    @pytest.mark.asyncio
    async def test_finds_matches(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "hello.txt"), "w") as f:
            f.write("hello world\ngoodbye world")
        result = await agent(tmp_dir).grep.search("hello")
        assert len(result["matches"]) == 1
        assert result["matches"][0].line == 1
        assert result["matches"][0].text == "hello world"

    @pytest.mark.asyncio
    async def test_searches_recursively(self, tmp_dir: str) -> None:
        os.mkdir(os.path.join(tmp_dir, "sub"))
        with open(os.path.join(tmp_dir, "sub", "deep.txt"), "w") as f:
            f.write("deep match here")
        result = await agent(tmp_dir).grep.search("deep")
        assert len(result["matches"]) == 1
        assert "deep.txt" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_filters_by_glob(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "a.ts"), "w") as f:
            f.write("match ts")
        with open(os.path.join(tmp_dir, "b.js"), "w") as f:
            f.write("match js")
        result = await agent(tmp_dir).grep.search(
            "match", GrepOptions(glob="*.ts")
        )
        assert len(result["matches"]) == 1
        assert "a.ts" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_case_insensitive(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "test.txt"), "w") as f:
            f.write("Hello World")
        sensitive = await agent(tmp_dir).grep.search("hello")
        assert len(sensitive["matches"]) == 0
        insensitive = await agent(tmp_dir).grep.search(
            "hello", GrepOptions(ignore_case=True)
        )
        assert len(insensitive["matches"]) == 1

    @pytest.mark.asyncio
    async def test_respects_max_results(self, tmp_dir: str) -> None:
        lines = "\n".join(f"match {i}" for i in range(50))
        with open(os.path.join(tmp_dir, "many.txt"), "w") as f:
            f.write(lines)
        result = await agent(tmp_dir).grep.search(
            "match", GrepOptions(max_results=5)
        )
        assert len(result["matches"]) == 5

    @pytest.mark.asyncio
    async def test_context_lines(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "ctx.txt"), "w") as f:
            f.write("before\ntarget\nafter")
        result = await agent(tmp_dir).grep.search(
            "target", GrepOptions(context_lines=1)
        )
        assert len(result["matches"]) == 1
        assert result["matches"][0].context is not None
        assert result["matches"][0].context.before == ["before"]
        assert result["matches"][0].context.after == ["after"]

    @pytest.mark.asyncio
    async def test_skips_node_modules(self, tmp_dir: str) -> None:
        os.mkdir(os.path.join(tmp_dir, "node_modules"))
        with open(os.path.join(tmp_dir, "node_modules", "dep.js"), "w") as f:
            f.write("hidden match")
        with open(os.path.join(tmp_dir, "src.js"), "w") as f:
            f.write("visible match")
        result = await agent(tmp_dir).grep.search("match")
        assert len(result["matches"]) == 1
        assert "src.js" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_skips_binary_files(self, tmp_dir: str) -> None:
        buf = bytearray(100)
        buf[50] = 0
        with open(os.path.join(tmp_dir, "binary.bin"), "wb") as f:
            f.write(buf)
        with open(os.path.join(tmp_dir, "text.txt"), "w") as f:
            f.write("findme")
        result = await agent(tmp_dir).grep.search("findme")
        assert len(result["matches"]) == 1
        assert "text.txt" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_column_position(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "col.txt"), "w") as f:
            f.write("abc def ghi")
        result = await agent(tmp_dir).grep.search("def")
        assert result["matches"][0].column == 5

    @pytest.mark.asyncio
    async def test_respects_gitignore(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, ".gitignore"), "w") as f:
            f.write("ignored_dir\n*.log\n")
        os.mkdir(os.path.join(tmp_dir, "ignored_dir"))
        with open(os.path.join(tmp_dir, "ignored_dir", "file.txt"), "w") as f:
            f.write("hidden match")
        with open(os.path.join(tmp_dir, "app.log"), "w") as f:
            f.write("log match")
        with open(os.path.join(tmp_dir, "visible.txt"), "w") as f:
            f.write("visible match")
        result = await agent(tmp_dir).grep.search("match")
        assert len(result["matches"]) == 1
        assert "visible.txt" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_path_option(self, tmp_dir: str) -> None:
        os.mkdir(os.path.join(tmp_dir, "sub"))
        with open(os.path.join(tmp_dir, "root.txt"), "w") as f:
            f.write("match root")
        with open(os.path.join(tmp_dir, "sub", "nested.txt"), "w") as f:
            f.write("match nested")
        result = await agent(tmp_dir).grep.search(
            "match", GrepOptions(path=os.path.join(tmp_dir, "sub"))
        )
        assert len(result["matches"]) == 1
        assert "nested.txt" in result["matches"][0].file

    @pytest.mark.asyncio
    async def test_no_matches(self, tmp_dir: str) -> None:
        with open(os.path.join(tmp_dir, "empty.txt"), "w") as f:
            f.write("nothing here")
        result = await agent(tmp_dir).grep.search("xyz_not_found")
        assert result["matches"] == []
