---
name: update-docs-and-commit
description: Analyze git changes, conservatively update docs, and commit everything
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git add:*), Bash(git commit:*), Read, Edit, Write, Glob, Task
argument-hint: "[optional: commit message override]"
---

# Update Documentation and Commit

You are tasked with analyzing current git changes, updating relevant documentation **conservatively**, and creating a single commit with all changes.

## Current Git Context

- **Branch**: !`git branch --show-current`
- **Status**: !`git status`
- **All changes since last commit**: !`git diff HEAD`
- **Recent commits** (for style reference): !`git log --oneline -5`

## Step 1: Analyze Changes

Review the git status and diff above. Categorize the changes:

- **Features**: New functionality added
- **Fixes**: Bugs or issues resolved
- **Refactors**: Code restructuring without behavior change
- **Tests**: Test additions or modifications
- **Docs**: Documentation updates
- **Config**: Configuration or dependency changes
- **Chore**: Build/tooling/maintenance

## Step 2: Determine Documentation Needs (Conservative Approach)

### Update `docs/changelog.md` ONLY if changes include:

✅ **Yes, update for:**
- New user-facing features
- API changes or new endpoints
- Bug fixes that affect behavior
- Breaking changes
- Major dependency updates
- Security fixes
- Performance improvements

❌ **No, skip for:**
- Code formatting/linting
- Internal refactors (no behavior change)
- Comment updates
- Minor variable renames
- Test-only changes
- Typo fixes

### Update `docs/architecture.md` ONLY if changes include:

✅ **Yes, update for:**
- New services, APIs, or major components
- Database schema changes (new tables, columns)
- New external integrations (Zotero, Notion, APIs)
- Authentication/authorization flow changes
- New environment variables
- Major architectural refactors

❌ **No, skip for:**
- Refactoring within existing components
- UI-only changes
- Minor utility functions
- Bug fixes (unless architectural)
- Performance optimizations (unless structural)

**When in doubt, DON'T update docs.** Only document genuinely significant changes.

## Step 3: Update Documentation (If Needed)

**Delegate to the docs-updater agent** to handle all documentation updates.

Use the Task tool:
- `subagent_type`: "general-purpose"
- `description`: "Update docs conservatively"
- `prompt`: "Read the agent instructions at .claude/agents/docs-updater/AGENT.md and follow them to update documentation.

Git status:
[paste git status output from context]

Git diff summary:
[provide a concise summary of what changed - focus on the key changes, not every line]

Change categorization:
[paste your categorization from Step 1]

Follow the AGENT.md instructions to:
1. Decide if changelog update is warranted and update docs/changelog.md
2. Decide if architecture update is warranted and update docs/architecture.md
3. Report what was done

Be conservative - only update docs for genuinely significant changes."

Wait for the agent to complete before proceeding to commit.

## Step 4: Stage and Commit Everything

After updating docs (or determining no updates needed):

1. **Stage all changes**: `git add -A`

2. **Create commit message**:

Use conventional commit format:
```
<type>: <brief summary>

<optional body with more context>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Commit types**:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code restructuring
- `docs:` - Documentation only
- `chore:` - Maintenance/tooling
- `perf:` - Performance improvement
- `test:` - Test changes

**Examples**:
```
feat: Add Notion OAuth integration

Implemented OAuth flow for Notion with per-user credentials.
Updated architecture docs with new integration details.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
fix: Resolve PDF parsing for multi-column layouts

Updated changelog with fix entry.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
refactor: Simplify session loading logic

No doc updates needed - internal refactor only.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

3. **Execute commit** using HEREDOC:
```bash
git commit -m "$(cat <<'EOF'
<your commit message here>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
EOF
)"
```

## Step 5: Report Results

Tell the user:

```
✓ Documentation update and commit complete

Changes analyzed:
  • [Brief summary of code changes]

Documentation updates (from docs-updater agent):
  • Changelog: [Agent result - what was done]
  • Architecture: [Agent result - what was done]

Commit created:
  [Show the commit message]

What's next?
1. Review the changes (git show)
2. Push to remote
3. Create pull request
4. Other
```

## Argument Handling

If user provides `$ARGUMENTS`, use it as the commit message summary instead of auto-generating.

Example:
```
/update-docs-and-commit feat: Add export feature
```

Uses "feat: Add export feature" as the commit summary, but still analyzes changes to update docs appropriately.

## Important Notes

- **Be conservative**: When uncertain, don't update docs
- **Create docs/ if needed**: Don't fail if directory doesn't exist
- **Single commit**: Code + docs in one commit
- **No empty commits**: If no changes staged, inform user
- **Preserve formatting**: Match existing changelog/architecture style

## Error Handling

- **No changes to commit**: Inform user, don't create empty commit
- **Docs read errors**: Create new docs if they don't exist
- **Git errors**: Report error and stop (don't continue with partial work)
