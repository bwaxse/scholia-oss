# Documentation Context

> See also: [Root CLAUDE.md](../CLAUDE.md) for overall architecture

## Documentation Structure

```
docs/
├── architecture.md  # System design, data flows, database schema
├── changelog.md     # Version history and feature releases
└── CLAUDE.md        # This file - documentation guidelines
```

## Documentation Maintenance

### When to Update `architecture.md`

Update after:
- ✅ New services, APIs, or major components
- ✅ Database schema changes (new tables, columns)
- ✅ New external integrations (Stripe, OAuth providers)
- ✅ Authentication/authorization flow changes
- ✅ New environment variables
- ✅ Major architectural refactors

**Don't update for:**
- ❌ Refactoring within existing components
- ❌ UI-only changes
- ❌ Minor utility functions
- ❌ Bug fixes (unless architectural impact)

### When to Update `changelog.md`

Update after:
- ✅ New user-facing features
- ✅ API changes or new endpoints
- ✅ Bug fixes that affect behavior
- ✅ Breaking changes
- ✅ Major dependency updates
- ✅ Security fixes
- ✅ Performance improvements

**Don't update for:**
- ❌ Code formatting/linting
- ❌ Internal refactors (no behavior change)
- ❌ Comment updates
- ❌ Minor variable renames
- ❌ Test-only changes
- ❌ Typo fixes

### Changelog Format

Use [Keep a Changelog](https://keepachangelog.com/) format:

```markdown
## Unreleased

### Added
- New feature descriptions

### Changed
- Modified functionality

### Fixed
- Bug fixes

### Removed
- Deprecated features

## [Version] - YYYY-MM-DD
...
```

### Architecture Document Structure

Sections:
1. **System Overview** - High-level architecture diagram
2. **Data Flow** - Step-by-step flows for key operations
3. **Component Architecture** - Frontend, backend, services breakdown
4. **Database Schema** - Table descriptions organized by domain
5. **Technology Stack** - Versions and dependencies
6. **Authentication Flow** - OAuth and session management
7. **Security Considerations** - Best practices and constraints
8. **Future Enhancements** - Planned improvements

## Documentation Style Guide

### Markdown Conventions

**Code blocks:**
```python
# Always specify language
def example():
    pass
```

**File paths:**
- Use backticks: `web/services/credit_service.py`
- Reference from project root

**API endpoints:**
- Use code format: `POST /api/subscriptions/checkout`
- Include HTTP method

**Links:**
```markdown
[Link text](relative/path/to/file.md)
[External link](https://example.com)
```

### Writing Style

- **Be concise** - Get to the point quickly
- **Use examples** - Show, don't just tell
- **Keep it current** - Remove outdated information
- **Link generously** - Cross-reference related docs
- **Use bullet points** - Easier to scan than paragraphs

### Technical Accuracy

- Test code examples before documenting
- Include version numbers when relevant
- Note platform-specific behavior
- Document edge cases and gotchas

## Auto-Documentation Tools

### API Documentation

FastAPI generates interactive docs automatically:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

**Improving API docs:**
```python
@router.post("/endpoint", response_model=ResponseModel)
async def endpoint(request: RequestModel):
    """
    Brief description.

    Longer description with details.

    **Args:**
    - request: Description of request body

    **Returns:**
    - ResponseModel with X, Y, Z

    **Raises:**
    - 400: When validation fails
    - 404: When resource not found
    """
```

### Database Schema Documentation

Generated from migrations in `web/db/`:
- `schema.sql` - Complete current schema
- `migrations/` - Historical evolution (optional)

Update `architecture.md` when schema changes.

## README.md

The README should contain:
1. **One-line description** - What is Scholia?
2. **Quick start** - How to run locally
3. **Key features** - What it does
4. **Tech stack** - What it's built with
5. **Documentation links** - Point to detailed docs
6. **Contributing** - How to contribute (if applicable)

Keep it short and high-level. Link to detailed docs.

## Documentation Workflow

### Using `/update-docs-and-commit`

When making changes, use the commit skill:
```bash
/update-docs-and-commit
```

This automatically:
1. Analyzes git changes
2. Updates `changelog.md` if needed
3. Updates `architecture.md` if needed
4. Creates a commit with all changes

### Manual Documentation Updates

If updating docs manually:
1. Read existing docs to match style
2. Update relevant sections
3. Check cross-references still work
4. Commit docs with code changes

## Documentation Review Checklist

Before committing documentation:

- [ ] Code examples are tested and work
- [ ] Version numbers are current
- [ ] Links are not broken
- [ ] Spelling and grammar are correct
- [ ] Formatting is consistent
- [ ] Cross-references are accurate
- [ ] Outdated information is removed
