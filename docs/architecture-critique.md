# Architecture Review: od-info

*Review date: December 2024*

## Overview

This is a Flask web application that scrapes data from OpenDominion, stores it locally, and presents analysis/intelligence to help players make strategic decisions. It's ~4,500 lines of Python (excluding tests and venv).

### Context

- **Users**: Personal use + shared instance for realm members + distributed to others who run locally
- **Deployment**: Local (SQLite) and PythonAnywhere (MySQL). Distributed as PyInstaller executable for non-technical users.
- **History**: Organically grown. Started with hand-crafted SQL, moved to ORM. Game rules change frequently requiring ongoing adaptation.

## Current Architecture Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                         Entry Points                            │
│  flask_app.py (web)          cron.py (batch updates)           │
└──────────────┬─────────────────────────┬───────────────────────┘
               │                         │
               ▼                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ODInfoFacade                               │
│  (queries, commands, session management, caching)               │
└──────────────┬─────────────────────────┬───────────────────────┘
               │                         │
       ┌───────┴───────┐         ┌───────┴───────┐
       ┌───────┴───────┐         ┌───────┴───────┐
       ▼               ▼         ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ calculators │ │   domain    │ │   opsdata   │ │  ref-data   │
│ (military,  │ │ (models,    │ │ (scraping,  │ │ (YAML/JSON  │
│  economy)   │ │  refdata)   │ │  updater)   │ │  game data) │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

## What Works Well

1. **Facade pattern**: Having a single entry point for business logic keeps Flask routes thin and enables the cron script to share code.

2. **Reference data externalization**: Game rules in YAML/JSON files (`ref-data/`) is smart. When game mechanics change, you edit data files rather than code.

3. **Domain models**: The SQLAlchemy models in `models.py` are well-structured with clear relationships and useful properties like `military`, `buildings`, `land`.

4. **Timestamped ops pattern**: The `TimestampedOpsMixin` for tracking when intelligence was gathered is a clean abstraction.

5. **Calculator separation**: `MilitaryCalculator` being separate from `Dominion` keeps domain models from becoming bloated.

6. **Early config loading**: Loading configuration at import time is intentional - takes the performance hit early and keeps runtime fast.

---

## Architectural Issues

### 1. The Facade is Doing Too Much

**Location**: `odinfo/facade/odinfo.py` (406 lines)

`ODInfoFacade` handles:
- Web session management (login to OpenDominion)
- Caching
- Database queries
- Data transformation for templates
- Triggering updates
- Report generation
- Discord integration

This violates single responsibility. When you add a new feature, you almost always touch this file.

**Impact**: Hard to understand, hard to test, merge conflicts if multiple features developed.

### 2. Two Database Abstraction Styles

**Locations**: `odinfo/domain/dataaccesslayer.py`, `cron.py`, various facade methods

You have competing patterns:

```python
# Pattern A: Pass `db` object around (Flask-SQLAlchemy style)
def all_doms(db):
    return db.session.execute(db.select(Dominion)).scalars()

# Pattern B: Direct session usage
dom = session.scalar(db.select(Dominion).where(...))
```

The `EngineWrapper` in `cron.py` exists solely to make non-Flask code look like Flask-SQLAlchemy. This is a symptom of no clean database abstraction.

**Impact**: Confusing which pattern to use, duplication, harder to test.

### 3. Unclear Boundary Between `domain` and `opsdata`

**Locations**: `odinfo/domain/`, `odinfo/opsdata/`

The naming suggests `domain` is your domain model and `opsdata` is data acquisition, but:
- `dataaccesslayer.py` is in `domain` but does database queries (infrastructure concern)
- `updater.py` in `opsdata` directly creates domain model objects
- The mapping dictionaries (e.g., `CLEARSIGHT_MAPPING`) in `updater.py` are really about domain structure

**Impact**: Unclear where new code should go, concepts leak across boundaries.

### 4. Calculators Have Hidden Dependencies on Domain State

**Location**: `odinfo/calculators/military.py`

`MilitaryCalculator` looks clean but accesses deeply nested state:
```python
self.dom.buildings.ratio_of('gryphon_nest')  # needs SurveyDominion
self.dom.last_castle.forges_rating           # needs CastleSpy
self.dom.tech.value_for_perk('offense')      # needs Vision
```

If any of these are `None`, you get runtime errors or silent wrong values. The calculator doesn't declare what data it needs.

**Note**: The `missing_intel_for_stats()` method is a good step toward addressing this.

**Impact**: Subtle bugs, unclear error messages, defensive coding scattered throughout.

### 5. Template Data Transformation in Facade

**Location**: `odinfo/facade/odinfo.py` methods like `military_list()`

The facade transforms domain objects into dictionaries for templates:
```python
dom_result = {
    'code': mc.dom.code,
    'name': mc.dom.name,
    'realm': mc.dom.realm,
    # ... 20+ fields
}
```

This is presentation logic living in the business layer.

**Impact**: Facade grows with every new UI field, mixing concerns.

### 6. Limited Test Coverage

**Location**: `test/`

~250 lines of test code for ~4,500 lines of application code. Tests focus on calculators (good) but don't cover:
- The facade
- Data scraping/parsing
- Database operations

The fixture setup in `fixtures.py` is substantial, suggesting testing is difficult.

**Impact**: Refactoring is risky, bugs caught late.

---

## Summary Table

| Aspect | Assessment |
|--------|------------|
| **Separation of concerns** | Partial - facade is overloaded, boundaries unclear |
| **Testability** | Difficult - tight coupling to database |
| **Maintainability** | Moderate - adding features requires touching many files |
| **Understandability** | Moderate - naming is sometimes misleading |
| **Extensibility** | Good for game data, harder for new features |

## Root Causes

The "incoherence" feeling comes from:

1. The facade accumulating responsibilities over time
2. Blurred boundaries between packages
3. No clear data flow pattern (some places use raw SQL, some ORM, some pass `db`, some import directly)
4. Organic growth without periodic restructuring