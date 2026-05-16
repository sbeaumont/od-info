# Refactoring Plan: od-info

*Created: December 2024*
*Status: Phases 1-3.1 Complete - Core refactoring done, remaining phases optional*

This document tracks the planned improvements to the od-info architecture. See `architecture-critique.md` for the full analysis.

---

## Guiding Principles

1. **Incremental changes**: Each refactoring should be small enough to complete in one session and not break the application.
2. **Tests first**: Where possible, add tests before refactoring to catch regressions.
3. **Keep it working**: The app should remain functional after each change.
4. **One thing at a time**: Don't combine multiple refactorings in one change.

## Learning Goals

This refactoring process is also a learning opportunity. During the work, focus on:

- **Design patterns**: When and why to use patterns like Repository, Factory, Service
- **SOLID principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Pythonic idioms**: List comprehensions, context managers, generators, dataclasses, type hints
- **Clean code practices**: Meaningful names, small functions, DRY (Don't Repeat Yourself)
- **Testing strategies**: Unit vs integration tests, mocking, fixtures, test isolation
- **Library best practices**: SQLAlchemy patterns, Flask conventions, typing module usage

Each refactoring session should include brief explanations of the principles being applied.

---

## Proposed Improvements

### Phase 1: Foundation (Database Abstraction)

**Goal**: Establish a clean database access pattern that works for both Flask and cron.

#### 1.1 Create Repository Pattern
- [x] Create `odinfo/repositories/` package
- [x] Create `GameRepository` class that encapsulates all Dominion and TownCrier queries
- [x] Repository receives a session, not the Flask `db` object
- [x] Add `transaction()` context manager for Unit of Work pattern
- [x] Update facade to use repository
- [x] Update `AwardStats` to use session directly
- [x] Update `updater.py` to use repository
- [x] Update `networthcalculator.py` to use repository
- [x] Update `query_stealables` to use repository
- [x] Update `flask_app.py` to create repository and inject into facade
- [x] Update `cron.py` to use repository
- [x] Remove `EngineWrapper` from cron.py
- [x] Clean up/remove `dataaccesslayer.py`
- [x] Test everything works

**Files affected**:
- New: `odinfo/repositories/__init__.py`, `odinfo/repositories/game.py`
- Modified: `odinfo/facade/odinfo.py`, `odinfo/facade/awardstats.py`, `odinfoweb/flask_app.py`, `cron.py`
- Modified: `odinfo/opsdata/updater.py`, `odinfo/calculators/networthcalculator.py`
- Removed: `odinfo/domain/dataaccesslayer.py`

**Risk**: Medium - touches core data access

**Status**: ✅ COMPLETE (December 2024)

---

### Phase 2: Configuration and Services

**Goal**: Create injectable configuration and split the monolithic facade into focused services.

#### 2.1 Extract Session Manager ✅
- [x] Create `odinfo/services/od_session.py`
- [x] Move OpenDominion login/session logic from scrapetools to ODSession class
- [x] Facade uses ODSession instead of login()
- [x] Removed login(), select_current_dominion(), pull_csrf_token() from scrapetools

#### 2.2 Create Config Class ✅
- [x] Create `Config` dataclass for injectable runtime configuration
- [x] Include: credentials (username, password), current_player_id, database_name, discord_webhook, feature_toggles, local_time_shift, secret_key
- [x] Keep URLs and paths as module-level constants (infrastructure concerns)
- [x] Added `get_config()` function to get default config instance
- [x] Update ODSession to receive Config instead of importing globals
- [x] Update facade to receive Config and use it for current_player_id
- [x] Update flask_app and cron.py to pass Config to facade
- [x] Remove legacy module-level variables (username, password, DATABASE_NAME, etc.)
- [x] Update all code to use `get_config()` instead of direct imports
- [x] Use Flask context_processor to inject feature_toggles into templates

#### 2.3 Extract Update Service ✅
- [x] Create `odinfo/services/update_service.py`
- [x] Move `update_ops`, `update_dom_index`, `update_all`, `update_realmies`, `update_town_crier`
- [x] Facade delegates to update service

#### 2.4 Extract Report Service ✅
- [x] Create `odinfo/services/report_service.py`
- [x] Move `get_top_bot_nw`, `get_unchanged_nw`, `send_top_bot_nw_to_discord`
- [x] Facade delegates to report service

#### 2.5 Extract Query Methods to Domain Services ✅
- [x] Create `odinfo/services/military_service.py` for military-related queries
- [x] Move `military_list`, `top_op`, `realmies_with_blops_info`
- [x] Removed `doms_as_mil_calcs` from facade (was internal implementation detail)

**Files affected**:
- New: `odinfo/services/` package with multiple modules
- Modified: `odinfo/facade/odinfo.py` (significantly smaller after)

**Risk**: Medium - many changes but each extraction is straightforward

---

### Phase 3: View Models

**Goal**: Move template data transformation out of facade/services into dedicated view model classes.

#### 3.1 Create View Models ✅
- [x] Create `odinfoweb/viewmodels/` package
- [x] Create `MilitaryRowVM` dataclass for military overview
- [x] Create `RealmieRowVM` dataclass for realmies overview
- [x] `MilitaryService` returns view models instead of dicts
- [x] Templates updated to use view model properties
- [ ] Repeat for other major views (overview, ratios, etc.) - deferred

**Why after Phase 2**: Once services are extracted, it's clear which service produces data for which view. View models become the bridge between service output and template input.

**Files affected**:
- New: `odinfoweb/viewmodels/__init__.py`, `odinfoweb/viewmodels/military.py`
- Modified: `odinfo/services/military_service.py`, `odinfoweb/templates/military.html`, `odinfoweb/templates/realmies.html`

**Risk**: Low - can be done incrementally per template

---

### Phase 4: Package Reorganization

**Goal**: Clear boundaries between domain, infrastructure, and application layers.

#### 4.1 Reorganize Package Structure
Current:
```
odinfo/
  calculators/
  domain/
  facade/
  opsdata/
```

Proposed:
```
odinfo/
  domain/           # Pure domain: models, calculators, game logic
    models.py
    calculators/
    refdata.py
  infrastructure/   # External concerns: database, web scraping
    repositories/
    scraping/
  application/      # Use cases, services, facade
    services/
    facade.py
```

- [ ] Plan file moves
- [ ] Update all imports
- [ ] Verify no circular dependencies

**Risk**: High - many import changes, but no logic changes

---

### Phase 5: Improve Calculator Robustness

**Goal**: Make calculators explicit about their data requirements.

#### 5.1 Add Data Requirement Checking
- [ ] Extend `missing_intel_for_stats()` pattern to cover all calculator methods
- [ ] Create a `@requires_intel('clear_sight', 'castle_spy')` decorator or similar
- [ ] Calculators raise clear errors when required data is missing

#### 5.2 Consider Calculator Factory
- [ ] Factory checks data availability before creating calculator
- [ ] Returns appropriate calculator variant or raises descriptive error

**Files affected**: `odinfo/calculators/military.py`, potentially new decorator module

**Risk**: Low - additive changes

---

### Phase 6: Testing Infrastructure

**Goal**: Make the codebase more testable.

#### 6.1 Repository Testing
- [ ] Add tests for repository methods using in-memory SQLite
- [ ] Simpler fixtures than current approach

#### 6.2 Service Testing
- [ ] Services can be tested with mock repositories
- [ ] No real database or web scraping needed

#### 6.3 Integration Tests
- [ ] Test facade with real (test) database
- [ ] Cover main user flows

---

## Progress Log

| Date | Change | Status |
|------|--------|--------|
| 2024-12-03 | Created architecture critique and refactoring plan | Done |
| 2024-12-03 | Phase 1: Created `GameRepository` with transaction support | Done |
| 2024-12-03 | Phase 1: Updated facade to use repository (dependency injection) | Done |
| 2024-12-03 | Phase 1: Updated `AwardStats` to accept session | Done |
| 2024-12-03 | Phase 1: Updated `updater.py`, `networthcalculator.py` to use repository | Done |
| 2024-12-03 | Phase 1: Updated `flask_app.py` and `cron.py` to use repository | Done |
| 2024-12-03 | Phase 1: Removed `EngineWrapper` and `dataaccesslayer.py` | Done |
| 2024-12-03 | Phase 1: COMPLETE - All tests pass | Done |
| 2024-12-03 | Phase 2.1: Created `ODSession` class, moved login logic from scrapetools | Done |
| 2024-12-03 | Phase 2.2: Created `Config` dataclass, updated facade/ODSession/flask_app/cron.py | Done |
| 2024-12-03 | Phase 2.2: Removed legacy config variables, all code uses `get_config()` | Done |
| 2024-12-15 | Phase 2.3: Created `UpdateService`, facade delegates update operations | Done |
| 2024-12-15 | Phase 2.4: Created `ReportService`, facade delegates report operations | Done |
| 2024-12-15 | Phase 2.5: Created `MilitaryService`, facade delegates military queries | Done |
| 2024-12-15 | Phase 3.1: Created view models (`MilitaryRowVM`, `RealmieRowVM`) for military views | Done |

---

## Notes & Decisions

*Record important decisions and their rationale here*

- **Config loading at import time**: Intentionally kept - takes performance hit early, simplifies runtime.

- **GameRepository vs DominionRepository**: Chose a single `GameRepository` instead of multiple entity-specific repositories. Pragmatic for a small codebase, can split later if needed.

- **Unit of Work pattern**: Added `transaction()` context manager to repository. All write methods use it internally and auto-commit. This is "idiot-proof" - callers don't need to remember to commit.

- **Batch methods**: Created both `add_dominion()` (single, auto-commits) and `add_dominions()` (batch, single transaction) for efficiency.

- **AwardStats and complex queries**: Complex read-only aggregate queries (like in `AwardStats`) don't need to go through the repository. They receive a session directly. This is a CQRS-lite approach - repository for entity CRUD, separate query classes for analytics.

- **Facade receives repository**: The facade now receives a `GameRepository` via dependency injection instead of creating it. This improves testability and follows the Dependency Inversion Principle.

- **Session naming**: Renamed `self._session` to `self._od_session` in facade to distinguish OpenDominion web session from database session.

- **UpdateService session provider**: The `UpdateService` receives a callable `session_provider` instead of a direct session reference. This allows lazy initialization - the OpenDominion session is only created when actually needed for an update operation. The facade passes `lambda: self.od_session` to enable this pattern.

- **ReportService receives repository directly**: Unlike the initial approach of passing facade methods as callables (which would create tight coupling to facade implementation details), the `ReportService` receives the `GameRepository` directly. It computes what it needs from fundamental data sources rather than depending on derived/cached facade methods.

- **MilitaryService receives current_day as parameter**: Methods like `military_list` and `realmies_with_blops_info` need the current game day for boat protection calculations. Rather than having the service fetch this from OpenDominion (which would require a session), the facade provides `current_day` as a parameter. This keeps the service pure and testable.

- **View models as dataclasses**: Using Python dataclasses for view models provides type safety, automatic `__init__`, and can include computed properties (like `temples_percent`). View models flatten nested domain objects - e.g., `RealmieRowVM` includes `docks` and `ares` directly rather than exposing the full Dominion object. This keeps templates simple and decouples them from domain model structure.

---

## Parking Lot

*Ideas that came up but aren't prioritized yet*

- **ReferenceData class**: Consolidate game constants (PLAT_PER_ALCHEMY_PER_TICK, etc.) and refdata.py classes (races, spells, techs, wonders) into a single injectable ReferenceData object
- Consider using dataclasses for some domain objects
- Evaluate if Flask-SQLAlchemy is still the best choice vs plain SQLAlchemy
- Look into async for web scraping (probably overkill for this use case)

---

## Bugs / Issues Found During Refactoring

- **Late joiners not added**: Dominions are only initialized once at startup. If someone joins the round late, they won't be in the dominion list. Need to handle incremental updates to the dominion index.