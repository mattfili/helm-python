import os
import subprocess
import tempfile
import shutil

import pytest

from fairlead import FairleadOptions, create_fairlead
from fairlead.skills import git


def exec_git(args: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout


@pytest.fixture
def git_repo():
    d = tempfile.mkdtemp(prefix="helm-git-test-")
    exec_git(["init"], d)
    exec_git(["config", "user.email", "test@test.com"], d)
    exec_git(["config", "user.name", "Test"], d)
    with open(os.path.join(d, "init.txt"), "w") as f:
        f.write("init")
    exec_git(["add", "."], d)
    exec_git(["commit", "-m", "initial"], d)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def agent(cwd: str):
    return create_fairlead(FairleadOptions(permissions={"git.*": "allow"})).use(git(cwd=cwd))


class TestStatus:
    @pytest.mark.asyncio
    async def test_reports_clean(self, git_repo: str) -> None:
        result = await agent(git_repo).git.status()
        assert result.branch
        assert result.staged == []
        assert result.unstaged == []
        assert result.untracked == []

    @pytest.mark.asyncio
    async def test_reports_untracked(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "new.txt"), "w") as f:
            f.write("new")
        result = await agent(git_repo).git.status()
        assert "new.txt" in result.untracked

    @pytest.mark.asyncio
    async def test_reports_staged(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "staged.txt"), "w") as f:
            f.write("staged")
        exec_git(["add", "staged.txt"], git_repo)
        result = await agent(git_repo).git.status()
        assert len(result.staged) == 1
        assert result.staged[0].path == "staged.txt"
        assert result.staged[0].status == "added"

    @pytest.mark.asyncio
    async def test_reports_unstaged(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "init.txt"), "w") as f:
            f.write("modified")
        result = await agent(git_repo).git.status()
        assert len(result.unstaged) == 1
        assert result.unstaged[0].status == "modified"

    @pytest.mark.asyncio
    async def test_reports_staged_deletions(self, git_repo: str) -> None:
        exec_git(["rm", "init.txt"], git_repo)
        result = await agent(git_repo).git.status()
        assert len(result.staged) == 1
        assert result.staged[0].status == "deleted"

    @pytest.mark.asyncio
    async def test_reports_staged_renames(self, git_repo: str) -> None:
        exec_git(["mv", "init.txt", "renamed.txt"], git_repo)
        result = await agent(git_repo).git.status()
        assert any(f.status == "renamed" for f in result.staged)
        assert any(f.old_path == "init.txt" for f in result.staged)


class TestDiff:
    @pytest.mark.asyncio
    async def test_shows_unstaged(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "init.txt"), "w") as f:
            f.write("modified content\n")
        result = await agent(git_repo).git.diff()
        assert len(result["files"]) == 1
        assert result["files"][0].path == "init.txt"
        assert result["files"][0].additions >= 1

    @pytest.mark.asyncio
    async def test_shows_staged(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "init.txt"), "w") as f:
            f.write("staged content\n")
        exec_git(["add", "init.txt"], git_repo)
        result = await agent(git_repo).git.diff({"staged": True})
        assert len(result["files"]) == 1
        assert result["files"][0].path == "init.txt"

    @pytest.mark.asyncio
    async def test_shows_diff_against_ref(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "new.txt"), "w") as f:
            f.write("new file\n")
        exec_git(["add", "."], git_repo)
        exec_git(["commit", "-m", "add new"], git_repo)
        result = await agent(git_repo).git.diff({"ref": "HEAD~1"})
        assert any(f.path == "new.txt" for f in result["files"])

    @pytest.mark.asyncio
    async def test_returns_empty_for_clean(self, git_repo: str) -> None:
        result = await agent(git_repo).git.diff()
        assert result["files"] == []


class TestLog:
    @pytest.mark.asyncio
    async def test_returns_commits(self, git_repo: str) -> None:
        result = await agent(git_repo).git.log()
        assert len(result["commits"]) == 1
        assert result["commits"][0].message == "initial"
        assert result["commits"][0].hash
        assert result["commits"][0].short_hash
        assert result["commits"][0].author == "Test"
        assert result["commits"][0].email == "test@test.com"

    @pytest.mark.asyncio
    async def test_respects_limit(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "second.txt"), "w") as f:
            f.write("second")
        exec_git(["add", "."], git_repo)
        exec_git(["commit", "-m", "second commit"], git_repo)
        result = await agent(git_repo).git.log({"limit": 1})
        assert len(result["commits"]) == 1
        assert result["commits"][0].message == "second commit"


class TestShow:
    @pytest.mark.asyncio
    async def test_shows_file_at_head(self, git_repo: str) -> None:
        result = await agent(git_repo).git.show("HEAD", {"path": "init.txt"})
        assert result["content"] == "init"

    @pytest.mark.asyncio
    async def test_shows_commit_without_path(self, git_repo: str) -> None:
        result = await agent(git_repo).git.show("HEAD")
        assert "initial" in result["content"]


class TestAdd:
    @pytest.mark.asyncio
    async def test_stages_files(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "to-add.txt"), "w") as f:
            f.write("add me")
        await agent(git_repo).git.add(["to-add.txt"])
        status = await agent(git_repo).git.status()
        assert any(f.path == "to-add.txt" for f in status.staged)


class TestCommit:
    @pytest.mark.asyncio
    async def test_creates_commit(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "commit-me.txt"), "w") as f:
            f.write("data")
        exec_git(["add", "commit-me.txt"], git_repo)
        result = await agent(git_repo).git.commit("test commit")
        assert result["hash"]
        assert len(result["hash"]) >= 7
        log = await agent(git_repo).git.log({"limit": 1})
        assert log["commits"][0].message == "test commit"


class TestBranchList:
    @pytest.mark.asyncio
    async def test_lists_branches(self, git_repo: str) -> None:
        result = await agent(git_repo).git.branch_list()
        assert len(result["branches"]) >= 1
        assert result["current"]
        assert any(
            b.current and b.name == result["current"]
            for b in result["branches"]
        )


class TestBranchCreate:
    @pytest.mark.asyncio
    async def test_creates_branch(self, git_repo: str) -> None:
        await agent(git_repo).git.branch_create("feature-test")
        result = await agent(git_repo).git.branch_list()
        assert any(b.name == "feature-test" for b in result["branches"])

    @pytest.mark.asyncio
    async def test_creates_at_start_point(self, git_repo: str) -> None:
        with open(os.path.join(git_repo, "second.txt"), "w") as f:
            f.write("second")
        exec_git(["add", "."], git_repo)
        exec_git(["commit", "-m", "second"], git_repo)
        await agent(git_repo).git.branch_create(
            "from-first", {"start_point": "HEAD~1"}
        )
        await agent(git_repo).git.checkout("from-first")
        log = await agent(git_repo).git.log({"limit": 1})
        assert log["commits"][0].message == "initial"


class TestCheckout:
    @pytest.mark.asyncio
    async def test_switches_branch(self, git_repo: str) -> None:
        await agent(git_repo).git.branch_create("switch-target")
        await agent(git_repo).git.checkout("switch-target")
        status = await agent(git_repo).git.status()
        assert status.branch == "switch-target"
