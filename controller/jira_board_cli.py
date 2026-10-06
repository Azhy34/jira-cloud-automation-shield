#!/usr/bin/env python3
"""
Interactive CLI for inspecting and controlling Jira Kanban Board directly from IDE.
Usage:
    python controller/jira_board_cli.py board
    python controller/jira_board_cli.py move KAN-4 "Done"
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv(".env")
load_dotenv(".env.jira")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env.jira")

from client.jira_client import JiraCloudClient

def display_board(project_key: str):
    client = JiraCloudClient.from_env()
    search_res = client.search_issues_jql(f"project = {project_key} ORDER BY created ASC", max_results=50)

    columns = {"To Do": [], "In Progress": [], "Done": []}

    for issue in search_res.issues:
        key = issue.key
        summary = issue.fields.summary
        status = issue.fields.status.name
        itype = issue.fields.issuetype.name
        parent = f" [Parent: {issue.fields.parent.key}]" if issue.fields.parent else ""

        line = f"[{key}] ({itype}) {summary}{parent}"

        category_key = (issue.fields.status.statusCategory.key or "").lower() if issue.fields.status.statusCategory else ""
        if category_key == "done":
            columns["Done"].append(line)
        elif category_key == "indeterminate":
            columns["In Progress"].append(line)
        else:
            columns["To Do"].append(line)

    print(f"\n=================================================================")
    print(f"📊 LIVE JIRA KANBAN BOARD CONTROLLER (Project: {project_key})")
    print(f"=================================================================")
    for col, items in columns.items():
        print(f"\n📌 COLUMN: [{col.upper()}] ({len(items)} items)")
        for item in items:
            print(f"   • {item}")

def main():
    project_key = os.getenv("JIRA_PROJECT_KEY", "KAN")
    if len(sys.argv) > 1 and sys.argv[1] == "move":
        if len(sys.argv) >= 4:
            issue_key = sys.argv[2]
            target_status = sys.argv[3]
            client = JiraCloudClient.from_env()
            client.move_status(issue_key, target_status)
            print(f"[+] Successfully moved {issue_key} to '{target_status}'!")
        else:
            print("Usage: python controller/jira_board_cli.py move <KEY> <STATUS>")
    else:
        display_board(project_key)

if __name__ == "__main__":
    main()
