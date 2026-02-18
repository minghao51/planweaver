"""GitHub repository context analyzer"""
from github import Github, GithubException
from typing import Dict, Any, List
import re


class GitHubAnalyzer:
    """Analyze GitHub repositories for planning context"""

    def __init__(self, github_token: str = None):
        self.github = Github(github_token) if github_token else Github()

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

                if len(files) >= 20:
                    break

            return files[:20]
        except:
            return []

    def _get_key_files(self, repo) -> Dict[str, str]:
        """Get content of key files (README, package files)"""
        key_files = {}

        try:
            # README
            readme = repo.get_readme()
            key_files["README.md"] = readme.decoded_content.decode()[:1000]
        except:
            pass

        try:
            # package.json
            pkg_file = repo.get_contents("package.json")
            key_files["package.json"] = pkg_file.decoded_content.decode()
        except:
            pass

        try:
            # requirements.txt
            req_file = repo.get_contents("requirements.txt")
            key_files["requirements.txt"] = req_file.decoded_content.decode()
        except:
            pass

        return key_files

    def _get_dependencies(self, repo) -> Dict[str, List[str]]:
        """Extract dependencies from package files"""
        dependencies = {"python": [], "javascript": [], "other": []}

        try:
            req_file = repo.get_contents("requirements.txt")
            requirements = req_file.decoded_content.decode().split("\n")
            dependencies["python"] = [r.strip() for r in requirements if r.strip() and not r.startswith("#")]
        except:
            pass

        try:
            pkg_file = repo.get_contents("package.json")
            import json
            pkg_json = json.loads(pkg_file.decoded_content.decode())
            dependencies["javascript"] = list(pkg_json.get("dependencies", {}).keys())
        except:
            pass

        return dependencies

    def _build_summary(
        self,
        metadata: Dict[str, Any],
        file_structure: List[str],
        key_files: Dict[str, str],
        dependencies: Dict[str, List[str]]
    ) -> str:
        """Build a comprehensive summary for the planner"""
        summary = f"""## GitHub Repository: {metadata['name']}

**Description:** {metadata['description']}
**Language:** {metadata['language']}
**Stars:** {metadata['stars']}
**URL:** {metadata['url']}

### File Structure (Top 20 by size):
"""
        for file in file_structure[:10]:
            summary += f"- {file}\n"

        summary += "\n### Dependencies:\n"
        if dependencies['python']:
            summary += "**Python:** " + ", ".join(dependencies['python'][:10]) + "\n"
        if dependencies['javascript']:
            summary += "**JavaScript:** " + ", ".join(dependencies['javascript'][:10]) + "\n"

        summary += "\n### Key Files:\n"
        for filename, content in key_files.items():
            summary += f"\n**{filename}**:\n```\n{content[:500]}...\n```\n"

        return summary
