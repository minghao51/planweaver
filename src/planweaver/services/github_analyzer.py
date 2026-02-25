"""GitHub repository context analyzer"""
import json
import re
from github import Github, GithubException
from typing import Dict, Any, List


class GitHubAnalyzer:
    """Analyze GitHub repositories for planning context"""

    def __init__(self, github_token: str = None):
        self.github = Github(github_token) if github_token else Github()
        self._max_files = 20
        self._max_readme_chars = 1000
        self._max_summary_list_items = 10

    async def analyze_repository(self, repo_url: str) -> Dict[str, Any]:
        """Analyze a GitHub repository and extract context"""
        # Parse owner/repo from URL
        owner, repo_name = self._parse_github_url(repo_url)

        try:
            repo = self.github.get_repo(f"{owner}/{repo_name}")

            # Extract repository metadata
            metadata = {
                "name": repo.name,
                "description": repo.description or "",
                "language": repo.language or "",
                "stars": repo.stargazers_count,
                "url": repo.html_url
            }

            # Get file structure
            file_structure = self._get_file_structure(repo)

            # Get key files
            key_files = self._get_key_files(repo)

            # Get dependencies
            dependencies = self._get_dependencies(repo)

            # Build content summary
            content_summary = self._build_summary(
                metadata, file_structure, key_files, dependencies
            )

            return {
                "metadata": metadata,
                "file_structure": file_structure,
                "key_files": key_files,
                "dependencies": dependencies,
                "content_summary": content_summary
            }

        except GithubException as e:
            raise ValueError(f"GitHub API error: {str(e)}")

    def _safe_repo_contents(self, repo, path: str):
        try:
            return repo.get_contents(path)
        except GithubException:
            return None

    def _safe_decoded_content(self, repo, path: str) -> str | None:
        file_obj = self._safe_repo_contents(repo, path)
        if file_obj is None:
            return None
        try:
            return file_obj.decoded_content.decode()
        except (AttributeError, UnicodeDecodeError):
            return None

    def _parse_github_url(self, url: str) -> tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name"""
        patterns = [
            r"github\.com/([^/]+)/([^/]+?)(\.git)?$",
            r"github\.com/([^/]+)/([^/]+)$"
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2)

        raise ValueError(f"Invalid GitHub URL: {url}")

    def _get_file_structure(self, repo) -> List[str]:
        """Get repository file structure (top 20 files by size)"""
        try:
            contents = repo.get_contents("")
            files = []

            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(repo.get_contents(file_content.path))
                else:
                    files.append(f"{file_content.path} ({file_content.size} bytes)")

                if len(files) >= self._max_files:
                    break

            return files[: self._max_files]
        except GithubException:
            return []

    def _get_key_files(self, repo) -> Dict[str, str]:
        """Get content of key files (README, package files)"""
        key_files = {}

        try:
            readme = repo.get_readme()
            key_files["README.md"] = readme.decoded_content.decode()[: self._max_readme_chars]
        except (GithubException, UnicodeDecodeError, AttributeError):
            pass

        package_json = self._safe_decoded_content(repo, "package.json")
        if package_json is not None:
            key_files["package.json"] = package_json

        requirements_txt = self._safe_decoded_content(repo, "requirements.txt")
        if requirements_txt is not None:
            key_files["requirements.txt"] = requirements_txt

        return key_files

    def _get_dependencies(self, repo) -> Dict[str, List[str]]:
        """Extract dependencies from package files"""
        dependencies = {"python": [], "javascript": [], "other": []}

        requirements_txt = self._safe_decoded_content(repo, "requirements.txt")
        if requirements_txt:
            requirements = requirements_txt.splitlines()
            dependencies["python"] = [
                line.strip()
                for line in requirements
                if line.strip() and not line.startswith("#")
            ]

        package_json = self._safe_decoded_content(repo, "package.json")
        if package_json:
            try:
                pkg_data = json.loads(package_json)
            except json.JSONDecodeError:
                pkg_data = {}
            dependencies["javascript"] = list(pkg_data.get("dependencies", {}).keys())

        return dependencies

    def _build_summary(
        self,
        metadata: Dict[str, Any],
        file_structure: List[str],
        key_files: Dict[str, str],
        dependencies: Dict[str, List[str]]
    ) -> str:
        """Build a comprehensive summary for the planner"""
        lines = [
            f"## GitHub Repository: {metadata['name']}",
            "",
            f"**Description:** {metadata['description']}",
            f"**Language:** {metadata['language']}",
            f"**Stars:** {metadata['stars']}",
            f"**URL:** {metadata['url']}",
            "",
            "### File Structure (Top 20 by size):",
        ]

        for file in file_structure[: self._max_summary_list_items]:
            lines.append(f"- {file}")

        lines.extend(["", "### Dependencies:"])
        if dependencies["python"]:
            lines.append("**Python:** " + ", ".join(dependencies["python"][: self._max_summary_list_items]))
        if dependencies["javascript"]:
            lines.append("**JavaScript:** " + ", ".join(dependencies["javascript"][: self._max_summary_list_items]))

        lines.extend(["", "### Key Files:"])
        for filename, content in key_files.items():
            preview = content[:500]
            suffix = "..." if len(content) > 500 else ""
            lines.extend(["", f"**{filename}**:", "```", f"{preview}{suffix}", "```"])

        return "\n".join(lines) + "\n"
