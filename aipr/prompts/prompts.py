"""Prompt management for AIPR."""

import importlib.resources
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Union


class InvalidPromptError(Exception):
    """Raised when a prompt file is invalid."""

    pass


class PromptManager:
    """Manages system and user prompts for AI models."""

    REQUIRED_XML_ELEMENTS = ["changes-set", "vulnerabilities-set"]

    def __init__(self, prompt_name: str = None):
        """Initialize the PromptManager with an optional custom prompt name."""
        self._default_system_prompt = (
            "You are a helpful assistant for generating Merge Requests.\n"
            "Your task is to analyze Git changes and vulnerability comparison data to create "
            "clear, well-structured merge request descriptions.\n"
            "Response should end with the last specific change or security finding discussed.\n"
            "If you find yourself wanting to write a concluding statement, stop writing instead."
        )

        self.prompt_name = prompt_name
        self._xml_prompt = None

        if prompt_name:
            self._load_prompt(prompt_name)

    def _load_prompt(self, prompt_name: str) -> None:
        """Load a prompt from either a file path or a built-in prompt name."""
        # First check if this is a file path (has .xml extension)
        path = Path(os.path.expanduser(prompt_name))
        if path.suffix == ".xml":
            if path.exists():
                self._load_xml_prompt(str(path))
                return
            # Try local prompts directory
            local_path = Path("prompts") / path.name
            if local_path.exists():
                self._load_xml_prompt(str(local_path))
                return
            raise InvalidPromptError(f"Prompt file not found: {path}")

        # If no .xml extension, treat as a built-in prompt name
        available_prompts = self._get_available_prompts()
        try:
            with (
                importlib.resources.files("aipr.prompts").joinpath(f"{prompt_name}.xml").open("r")
            ) as f:
                self._load_xml_prompt_from_string(f.read())
        except Exception as e:
            raise InvalidPromptError(
                f"Could not load prompt '{prompt_name}'. "
                f"Error: {e}\n\n"
                f"Available built-in prompts: {', '.join(available_prompts)}"
            )

    def _validate_xml_prompt(self, root: ET.Element) -> None:
        """Validate that the XML prompt has all required elements."""
        for element in self.REQUIRED_XML_ELEMENTS:
            if root.find(f".//{element}") is None:
                raise InvalidPromptError(
                    f"Invalid prompt file: Missing required element '{element}'"
                )

    def _load_xml_prompt(self, file_path: str) -> None:
        """Load and parse the XML prompt template from a file."""
        try:
            tree = ET.parse(file_path)  # nosec B314 - parsing trusted local XML files
            root = tree.getroot()
            self._validate_xml_prompt(root)
            self._xml_prompt = root
        except ET.ParseError as e:
            raise InvalidPromptError(f"Error parsing XML prompt file: {e}")
        except FileNotFoundError:
            raise InvalidPromptError(f"Prompt file not found: {file_path}")
        except PermissionError:
            raise InvalidPromptError(f"Permission denied reading prompt file: {file_path}")

    def _load_xml_prompt_from_string(self, xml_content: str) -> None:
        """Load and parse the XML prompt template from a string."""
        try:
            root = ET.fromstring(xml_content)  # nosec B314 - parsing trusted local XML content
            self._validate_xml_prompt(root)
            self._xml_prompt = root
        except ET.ParseError as e:
            raise InvalidPromptError(f"Error parsing XML prompt content: {e}")

    def _get_available_prompts(self) -> list[str]:
        """Get list of available built-in prompts."""
        try:
            prompts_dir = importlib.resources.files("aipr.prompts")
            return [
                f.stem for f in prompts_dir.iterdir() if f.suffix == ".xml" and f.stem != "__init__"
            ]
        except Exception:
            return []

    def get_system_prompt(self) -> str:
        """Get the system prompt."""
        return self._default_system_prompt

    def get_user_prompt(self, diff: str, vuln_data: Union[str, dict, None] = None) -> str:
        """Get the user prompt with diff and optional vulnerability data."""
        if self.prompt_name:
            if self._xml_prompt is None:
                raise ValueError("XML prompt file was specified but could not be loaded")

            # Find the changes-set and vulnerabilities-set elements
            changes_set = self._xml_prompt.find(".//changes-set")
            vulns_set = self._xml_prompt.find(".//vulnerabilities-set")

            # Update the content
            if changes_set is not None:
                changes_set.text = "\n" + diff + "\n"  # Add newlines for better formatting
            if vulns_set is not None:
                if vuln_data:
                    vulns_set.text = (
                        "\n"
                        + (
                            json.dumps(vuln_data, indent=2)
                            if isinstance(vuln_data, dict)
                            else str(vuln_data)
                        )
                        + "\n"
                    )
                else:
                    vulns_set.text = ""

            # Get the example section
            example = self._xml_prompt.find(".//example")
            if example is not None:
                example.tail = "\n"  # Add newline after example

            # Convert to string while preserving formatting and remove XML declaration
            xml_str = ET.tostring(self._xml_prompt, encoding="unicode", method="xml")
            if xml_str.startswith("<?xml"):
                xml_str = xml_str[xml_str.find("?>") + 2 :]

            # Return the XML structure directly without wrapping it in additional text
            return xml_str.strip()

        # Default format when no XML prompt file is specified
        prompt = [
            "Please include:",
            "- A concise summary of the changes",
            "- Key modifications and their purpose",
            "- Any notable technical details",
            "- Security impact analysis (when vulnerability data is provided)",
            "",
            "Important Guidelines:",
            "1. Focus only on the specific changes shown in the diff and vulnerability comparison",
            "2. Each point must be directly tied to actual code changes or security findings",
            "3. When analyzing vulnerabilities:",
            "   - Highlight critical security changes",
            "   - Explain the impact of new vulnerabilities",
            "   - Acknowledge fixed vulnerabilities",
            "4. DO NOT include any of the following:",
            '   - Generic concluding statements (e.g., "This improves the overall system")',
            '   - Broad claims about improvements (e.g., "This enhances development processes")',
            '   - Value judgments about the changes (e.g., "This is a significant improvement")',
            "   - Future benefits or implications",
            "",
            "Git Diff:",
            diff,
        ]

        if vuln_data:
            prompt.extend(
                [
                    "",
                    "Vulnerability Analysis:",
                    (
                        json.dumps(vuln_data, indent=2)
                        if isinstance(vuln_data, dict)
                        else str(vuln_data)
                    ),
                ]
            )

        return "\n".join(prompt)

    def get_commit_prompt(
        self, staged_changes: str, file_summary: Dict[str, Any], context: str = ""
    ) -> str:
        """Get the commit prompt with staged changes and file summary."""
        # Load the commit prompt template
        commit_prompt_name = "commit"

        try:
            with (
                importlib.resources.files("aipr.prompts")
                .joinpath(f"{commit_prompt_name}.xml")
                .open("r")
            ) as f:
                xml_content = f.read()

            root = ET.fromstring(xml_content)  # nosec B314 - parsing trusted local XML content

            # Find the required elements
            staged_changes_elem = root.find(".//staged-changes")
            file_summary_elem = root.find(".//file-summary")
            context_elem = root.find(".//context")

            # Update the content
            if staged_changes_elem is not None:
                staged_changes_elem.text = "\n" + staged_changes + "\n"

            if file_summary_elem is not None:
                file_summary_text = (
                    f"Files changed: {file_summary.get('total', 0)}\n"
                    f"Added: {file_summary.get('added', 0)}, "
                    f"Modified: {file_summary.get('modified', 0)}, "
                    f"Deleted: {file_summary.get('deleted', 0)}\n"
                )
                file_summary_text += "Files:\n"
                for file_info in file_summary.get("files", []):
                    file_summary_text += f"  {file_info['status']} {file_info['path']}\n"
                file_summary_elem.text = "\n" + file_summary_text + "\n"

            if context_elem is not None:
                if context:
                    context_elem.text = "\n" + context + "\n"
                else:
                    context_elem.text = ""

            # Convert to string while preserving formatting and remove XML declaration
            xml_str = ET.tostring(root, encoding="unicode", method="xml")
            if xml_str.startswith("<?xml"):
                xml_str = xml_str[xml_str.find("?>") + 2 :]

            return xml_str.strip()

        except Exception as e:
            raise InvalidPromptError(f"Could not load commit prompt: {e}")

    def get_commit_system_prompt(self) -> str:
        """Get the system prompt for commit message generation."""
        return (
            "You are an expert code analyst and conventional commit message generator.\n\n"
            "Your task: Analyze the provided git diff and generate a precise conventional commit message.\n\n"
            "CRITICAL ANALYSIS REQUIREMENTS:\n"
            "1. Read the diff content carefully - look for new functions, classes, methods, imports\n"
            "2. Identify the PRIMARY functionality being implemented from the code changes\n"
            "3. Extract specific details from function names, class names, and implementation logic\n"
            "4. Determine the most accurate commit type based on actual code changes\n"
            "5. Generate a description that reflects what was specifically implemented\n\n"
            "OUTPUT FORMAT: type(scope): description\n"
            "- type: feat/fix/docs/test/build/ci/chore/refactor/style/perf\n"
            "- scope: optional, derived from the main area of change\n"
            "- description: imperative mood, specific to the implementation\n\n"
            "RESPOND WITH ONLY THE COMMIT MESSAGE - NO EXPLANATIONS OR ADDITIONAL TEXT."
        )
