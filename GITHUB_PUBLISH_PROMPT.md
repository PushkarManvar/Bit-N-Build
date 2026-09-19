# OpenCode GitHub Publishing Prompt

Paste this prompt into OpenCode from the JourneyLens repository root after the local bootstrap checks pass.

---

Read `AGENTS.md`, `CONTRIBUTING.md`, and `docs/09_GITHUB_AND_COLLABORATION.md` before acting.

Publish this prepared repository to GitHub and verify the collaboration setup. Work autonomously and do not request separate permission for normal `git add`, `git commit`, or non-force `git push` operations. Never force-push, overwrite an unrelated repository, expose credentials, or make the repository public without explicit user direction.

Use this procedure:

1. Confirm this directory is the JourneyLens repository and that `git status` is clean.
2. Show the current branch and recent local commits.
3. Run the required local checks from `AGENTS.md`. Stop if a core check fails and fix the problem before publishing.
4. Check whether GitHub CLI (`gh`) is installed.
5. If `gh` is missing, identify the operating system and install it using the official GitHub CLI installation method. If system administrator privileges are required, ask only for that privilege; do not replace or remove unrelated packages.
6. Run `gh auth status`. If authentication is missing, start `gh auth login` and let the user complete GitHub authentication. Never print or persist an authentication token.
7. Determine the authenticated GitHub account with `gh api user --jq .login`.
8. Inspect `git remote -v`.
9. If no `origin` exists:
   - use repository name `journeylens`;
   - default to **private** visibility;
   - use the current directory as the source;
   - set the description to `Explainable customer identity resolution and broken-refund journey detection`;
   - create the remote without adding generated README, license, or `.gitignore` files;
   - push `main` and set upstream tracking.
10. Before creating anything, check whether `<authenticated-user>/journeylens` already exists. If it exists:
    - inspect its description, default branch, and existing history;
    - never overwrite or force-push it;
    - if it is this project, configure it as `origin` and push normally;
    - if it is unrelated, stop and request a different repository name.
11. If `origin` already exists, verify it points to the intended JourneyLens repository, then push the current branch normally.
12. Add repository topics where supported: `hackathon`, `fastapi`, `nextjs`, `postgresql`, `identity-resolution`, `customer-journey`.
13. Confirm GitHub Actions is enabled and that `.github/workflows/ci.yml` appears in the pushed default branch.
14. Attempt to configure `main` protection with these checks when the account/repository plan supports it:
    - require pull requests before merging;
    - require status checks named `Backend`, `Frontend`, and `Docker configuration`;
    - block force pushes and branch deletion.
15. If branch protection cannot be configured automatically, report the exact repository Settings path and the values the owner should select. Do not weaken another repository rule.
16. Do not invite collaborators until the user provides exact GitHub usernames. When usernames are supplied, verify each username before sending an invitation.
17. Inspect the first Actions run. If it fails, diagnose and fix repository-owned failures, commit the fix, and push normally. Do not bypass or disable CI.

At completion, report:

- repository URL;
- visibility;
- default branch;
- pushed commit SHA;
- CI run URL and status;
- branch-protection result;
- any collaborator usernames still needed.

---

Recommended command:

```bash
opencode --auto
```

Auto mode removes repeated low-risk prompts, while the repository configuration continues to deny force-pushes, destructive Git cleanup, and hard resets.
