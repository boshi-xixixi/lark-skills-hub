---
name: lark-project-manager
version: 1.0.0
description: "Full lifecycle project manager using native Lark ecosystem. Create project spaces (folder+doc+kanban+calendar), task status flow with auto-notification, meeting minutes auto-linking with action item extraction, AI-driven weekly reports and progress dashboard, one-click archive. Use when: create new project, check project progress, link meeting notes, generate project reports, manage task kanban, archive projects."
metadata:
  requires:
    bins: ["lark-cli"]
---

# Lark Project Manager

**CRITICAL: Read ../lark-shared/SKILL.md first**

## Capabilities
| Capability | Description | Underlying Skill |
|-----------|-----------|-----------------|
| Create Project | Full project space setup | drive + doc + base |
| Progress Dashboard | Visual health metrics | base + task |
| Meeting Link | Minutes->doc + actions->tasks | calendar + minutes + doc + task |
| Smart Report | AI weekly report generation | base + doc + im |
| Task Flow | Status change + notification | base + task + im |
| Archive | One-click project closure | drive + doc + calendar |

## Quick Start
```bash
python3 scripts/init_project.py --name "MyProject"
python3 scripts/status.py --config .project_MyProject.json
python3 scripts/gen_report.py --config .project_MyProject.json --mode weekly
python3 scripts/meeting_link.py --project-doc xxx --minute-token yyy
```
