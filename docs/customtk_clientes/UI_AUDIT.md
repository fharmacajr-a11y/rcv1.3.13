# UI Technology Audit Report

**Date:** 2026-01-16  
**Project:** v1.5.42 - CustomTkinter Migration  
**Scope:** Global audit of UI technologies (ttkbootstrap, ttk, CustomTkinter)

---

## Executive Summary

### Technology Stack Status

| Technology | Files | Lines | Status | Action |
|-----------|-------|-------|--------|--------|
| **ttkbootstrap** | 67 | 1034+ | ⚠️ Legacy | Phase out from active UI |
| **ttk** | 56 | 124+ | ✅ Allowed | Keep for Treeview/fallback |
| **CustomTkinter** | 32 | 124+ | ✅ Primary | Expand usage |

### Priority Classification

- **P0 (SHELL - Critical):** 6 files - Must migrate immediately
- **P1 (Active UI):** 15 files - Migrate in phases
- **P2 (Fallback/ttk):** 56 files - Keep or style via ttk_compat
- **P3 (Tests/Scripts):** 45 files - Update after production code

---

## P0: SHELL (Critical - Immediate Migration)

These files are part of the app's "shell" (startup, login, navigation) and must be migrated first.

### 1. src/ui/splash.py
**Lines:** 11, 12, 25-26, 68, 71, 82, 103, 113, 122, 127, 136, 140  
**Technology:** ttkbootstrap  
**Widgets:** `tb.Toplevel`, `tb.Frame`, `tb.Label`, `tb.Separator`, `tb.Progressbar`  
**Bootstyle:** `INFO` on Progressbar  
**Risk:** HIGH - First screen user sees  
**Action:**
```python
# Replace:
import ttkbootstrap as tb
from ttkbootstrap.constants import INFO

splash = tb.Toplevel(root)
container = tb.Frame(splash, padding=20)
bar = tb.Progressbar(..., bootstyle=INFO)

# With:
from src.ui.ctk_config import ctk
splash = ctk.CTkToplevel(root)
container = ctk.CTkFrame(splash)
bar = ctk.CTkProgressBar(...)  # no bootstyle, auto-colored
```

**Estimated Time:** 2-3 hours

---

### 2. src/ui/login_dialog.py
**Lines:** 9, 10, 90, 102, 109, 117, 131, 139  
**Technology:** ttkbootstrap  
**Widgets:** `ttk.Entry`, `ttk.Button`, `ttk.Checkbutton`  
**Bootstyle:** `INFO` (entries, buttons), `DANGER` (error button)  
**Risk:** HIGH - Authentication critical  
**Action:**
```python
# Replace:
import ttkbootstrap as ttk
from ttkbootstrap.constants import DANGER, INFO

self.email_entry = ttk.Entry(self, bootstyle=INFO)
btn = ttk.Button(self, bootstyle=DANGER)

# With:
from src.ui.ctk_config import ctk

self.email_entry = ctk.CTkEntry(self)
btn = ctk.CTkButton(self, fg_color="red", hover_color="darkred")
```

**Estimated Time:** 1-2 hours

---

### 3. src/ui/topbar.py
**Lines:** 15, 83, 131  
**Technology:** ttkbootstrap  
**Widgets:** `tb.Frame`  
**Risk:** HIGH - Main navigation container  
**Action:**
```python
# Replace:
import ttkbootstrap as tb
class TopBar(tb.Frame):

# With:
from src.ui.ctk_config import ctk
class TopBar(ctk.CTkFrame):
```

**Estimated Time:** 30 minutes

---

### 4. src/ui/components/topbar_nav.py
**Status:** ✅ **ALREADY MIGRATED** (Microfase 24)  
**Lines:** 18, 105, 129, 146, 156, 166, 178  
**Technology:** CustomTkinter (CTkButton)  
**Notes:** Icons temporarily disabled (emoji fallback)

---

### 5. src/ui/components/notifications_button.py
**Status:** ✅ **ALREADY MIGRATED** (Microfase 24)  
**Lines:** 16, 60, 70, 109, 132  
**Technology:** CustomTkinter (CTkButton)  
**Notes:** Emoji fallback 🔔

---

### 6. src/modules/main_window/views/main_window_actions.py
**Lines:** 204 (ttk.Style comment)  
**Technology:** Minimal ttk usage  
**Risk:** MEDIUM - Main window action handlers  
**Action:** Audit for any ttkbootstrap Button usage, replace with CTkButton

**Estimated Time:** 1 hour

---

## P1: Active UI (High Priority - Phase 2-4)

### src/ui/components/

#### src/ui/components/progress_dialog.py
**Lines:** 9, 34, 37, 40, 51, 106, 127, 148, 158, 168, 177, 187, 192, 219  
**Widgets:** `tb.Toplevel`, `tb.Frame`, `tb.Label`, `tb.Progressbar`, `tb.Button`  
**Bootstyle:** `info-striped` (Progressbar), `danger` (Cancel button)  
**Risk:** MEDIUM - Used in file operations  
**Action:** Migrate to CTkToplevel, CTkProgressBar, CTkButton

---

#### src/ui/components/buttons.py
**Lines:** 9, 14-22, 46, 48-50, 58, 60, 69, 72-74, 84, 89, 94  
**Widgets:** `tb.Frame`, `tb.Button`  
**Bootstyle:** `success`, `secondary`, `info`, `danger`  
**Risk:** HIGH - Shared button factory  
**Action:** Replace with CTkButton factory, map bootstyles to colors

---

#### src/ui/components/inputs.py
**Lines:** 11, 25, 40-50, 91, 93, 140, 192, 207, 253, 257, 269, 273, 277, 284, 303, 314, 334, 341, 345, 351, 355  
**Widgets:** `tb.Frame`, `tb.Label`, `tb.Entry`, `tb.Button`, `tb.Combobox`  
**Bootstyle:** `info`, `secondary`, `warning`  
**Risk:** HIGH - Shared search controls  
**Action:** Complex migration - search bar with icons + comboboxes

---

#### src/ui/components/misc.py
**Lines:** 12, 40, 44-45, 105, 111, 113, 116, 120  
**Widgets:** `tb.Frame`, `tb.Label`  
**Bootstyle:** `warning` (status dot), `inverse` (status label)  
**Risk:** MEDIUM - Status indicators  
**Action:** Migrate to CTkFrame/CTkLabel with color mapping

---

#### src/ui/components/lists.py
**Lines:** 10, 11, 76, 90, 135, 205, 294, 345, 362, 370, 443, 546, 626  
**Widgets:** `tb.Style`, `tb.Treeview` (but should be ttk.Treeview!)  
**Risk:** MEDIUM - Treeview styling helper  
**Action:** Keep ttk.Treeview, update styling logic via ttk_compat

---

#### src/ui/components/notifications_popup.py
**Lines:** 12, 224, 228, 233, 237, 242, 246, 257, 261, 265, 57, 193, 314  
**Widgets:** `tb.Button`, `ttk.Treeview`  
**Bootstyle:** `success`, `danger-outline`, `danger`, `round-toggle`, `secondary`  
**Risk:** MEDIUM - Notification popup  
**Action:** Migrate buttons to CTkButton, keep ttk.Treeview

---

### src/ui/widgets/

#### src/ui/widgets/scrollable_frame.py
**Lines:** 13, 19, 35, 44-45, 64, 72  
**Widgets:** `tb.Frame`, `tb.Scrollbar`  
**Risk:** LOW - Reusable scroll container  
**Action:** Migrate to CTkScrollableFrame (native widget!)

---

### src/ui/

#### src/ui/placeholders.py
**Lines:** 9, 20, 29, 32, 35, 38, 41, 85, 88, 90  
**Widgets:** `tb.Frame`, `tb.Label`, `tb.Button`  
**Bootstyle:** `secondary`  
**Risk:** LOW - Placeholder screens  
**Action:** Migrate to CTkFrame/CTkLabel/CTkButton

---

#### src/ui/theme.py
**Lines:** 8, 18, 22, 26, 34  
**Technology:** ttkbootstrap.Style  
**Risk:** LOW - Legacy theme init (has ttk fallback)  
**Action:** Mark DEPRECATED, use theme_manager.py instead

---

#### src/ui/custom_dialogs.py
**Lines:** 71, 140, 141  
**Widgets:** `ttk.Button`  
**Bootstyle:** `primary`, `secondary-outline`  
**Risk:** LOW - Simple dialogs  
**Action:** Migrate buttons to CTkButton

---

## P2: ttk Fallback (Keep + Style)

These files correctly use `ttk.Treeview` (no CTk equivalent) and should be **kept** but styled via `ttk_compat.py`.

### Treeview Users (Correct Usage - Keep)

1. **src/features/cashflow/ui.py** - Line 89: `ttk.Treeview`
2. **src/modules/uploads/views/file_list.py** - Lines 4, 37, 38, 73: `ttk.Treeview` (hierarchical)
3. **src/modules/cashflow/views/fluxo_caixa_frame.py** - Line 75: `ttk.Treeview`
4. **src/modules/clientes/views/main_screen_ui_builder.py** - Line 11: `from tkinter import ttk` (for Treeview)
5. **src/modules/clientes/views/client_obligations_frame.py** - Lines 7, 120: `ttk.Treeview`
6. **src/ui/subpastas_dialog.py** - Line 74: `ttk.Treeview`
7. **src/modules/auditoria/views/components.py** - Lines 7, 103: `ttk.Treeview`
8. **src/modules/auditoria/views/dialogs.py** - Lines 8, 148: `ttk.Treeview`
9. **src/modules/anvisa/views/anvisa_screen.py** - Lines 93, 128, 177: `ttk.Treeview` (multiple instances)
10. **src/modules/clientes/forms/client_picker.py** - Line 117: `ttk.Treeview`
11. **src/modules/lixeira/views/lixeira.py** - Lines 12, 119: `ttk.Treeview`
12. **src/modules/passwords/views/passwords_screen.py** - Line 123: `ttk.Treeview`
13. **src/modules/passwords/views/client_passwords_dialog.py** - Line 119: `ttk.Treeview`
14. **src/ui/components/notifications/notifications_popup.py** - Lines 57, 193, 314: `ttk.Treeview`

**Action:** ✅ Keep as-is, ensure `apply_ttk_treeview_theme()` is called on mode switch

---

### ttk.Style Users (Styling - Review)

1. **src/modules/auditoria/views/main_frame.py** - Line 94: `ttk.Style(self)`
2. **src/modules/anvisa/views/anvisa_screen.py** - Line 612: `ttk.Style()`
3. **src/modules/main_window/views/main_window.py** - Lines 93, 171, 399: `ttk.Style()` + `_patch_style_element_create`

**Action:** Review - ensure compatibility with CTk appearance mode, don't interfere with CTk styling

---

## P3: Tests & Scripts (Update After P0-P1)

### Test Files (45 files)

**Strategy:**
1. Update mocks to match production code (CTk instead of tb)
2. Remove bootstyle assertions
3. Add appearance_mode tests
4. Keep ttkbootstrap tests for legacy modules until migrated

**Key Test Files:**
- `tests/unit/ui/test_splash_style.py` - Update for CTk splash
- `tests/unit/ui/test_feedback_protocol.py` - Update bootstyle mocks
- `tests/test_login_dialog_style.py` - Update for CTk login
- `tests/unit/modules/hub/**` - 11 files, update for CTk dashboard
- `tests/conftest.py` - Update ttkbootstrap patches

---

### Scripts (5 files)

**Low Priority - Can remain ttkbootstrap for now:**
- `scripts/clients_quickcheck.py`
- `scripts/perf_clients_treeview.py`
- `scripts/visual/*.py` (visual testing tools)

---

## Deprecated/Legacy Files

### Already Marked DEPRECATED

1. **src/utils/themes.py** - Lines 3, 21, 23, 25, 129, 133, 136, 138, 164-170, 180, 184, 229, 233
   - Status: ✅ Already marked DEPRECATED
   - Action: Keep for backward compatibility, no active usage

2. **src/utils/theme_manager.py** - Line 2
   - Status: ✅ Already marked DEPRECATED
   - Action: Keep for backward compatibility

3. **src/ui/theme.py**
   - Status: ⚠️ Has fallback but not explicitly deprecated
   - Action: Mark DEPRECATED, redirect to `src/ui/theme_manager.py`

---

## Module-Specific Findings

### src/modules/ Analysis

#### Clientes Module (Partially Migrated)
- ✅ Toolbar: Migrated to CTkToolbar (`toolbar_ctk.py`)
- ✅ ActionBar: Migrated to CTkActionBar (`actionbar_ctk.py`)
- ✅ Form: Migrated to CTkForm (`client_form_view_ctk.py`)
- ⚠️ Obligations: Still uses ttkbootstrap (`client_obligations_frame.py`, `obligation_dialog.py`)
- ⚠️ Pickers: Still uses ttkbootstrap (`client_picker.py`)

**Action:** Migrate obligations and pickers in Phase 3

---

#### Hub Module (Not Migrated)
**Files with ttkbootstrap:** 8 files
- `hub_screen.py`, `hub_dashboard_view.py`, `hub_notes_view.py`
- `hub_quick_actions_view.py`, `hub_dialogs.py`
- `dashboard_center.py`, `modules_panel.py`, `notes_panel_view.py`

**Widgets:** `tb.Frame`, `tb.Label`, `tb.Button`, `tb.Labelframe`  
**Bootstyles:** `primary`, `secondary`, `info`, `warning`, `danger`

**Action:** Migrate in Phase 2 (high priority - dashboard)

---

#### Uploads Module (✅ Fully Migrated)
- All UI uses CustomTkinter
- Only ttk.Treeview for file browser (correct!)

---

#### Anvisa Module (Not Migrated)
**Files:** 3 files with ttkbootstrap  
**Challenge:** Heavy use of `ttk.DateEntry` (no CTk equivalent)  
**Action:** Migrate in Phase 5, keep DateEntry or create custom widget

---

#### Tasks Module (Not Migrated)
**Files:** `task_dialog.py`  
**Challenge:** Uses `tb.DateEntry`  
**Action:** Migrate in Phase 5

---

#### Passwords Module (Not Migrated)
**Files:** 3 files with ttkbootstrap  
**Action:** Migrate in Phase 5

---

#### Lixeira Module (Not Migrated)
**Files:** `lixeira.py`  
**Bootstyles:** `success`, `danger`, `secondary`  
**Action:** Migrate in Phase 6

---

#### Cashflow Module (Not Migrated)
**Files:** `dialogs.py`, `fluxo_caixa_frame.py`  
**Challenge:** Uses `ttkbootstrap.DateEntry`  
**Action:** Migrate in Phase 5

---

## Widget Frequency Analysis

### ttkbootstrap Widgets in Active Code

| Widget | Count | Status | CTk Equivalent |
|--------|-------|--------|----------------|
| `tb.Frame` | 50+ | ⚠️ Migrate | `ctk.CTkFrame` |
| `tb.Label` | 40+ | ⚠️ Migrate | `ctk.CTkLabel` |
| `tb.Button` | 35+ | ⚠️ Migrate | `ctk.CTkButton` |
| `tb.Entry` | 15+ | ⚠️ Migrate | `ctk.CTkEntry` |
| `tb.Combobox` | 10+ | ⚠️ Migrate | `ctk.CTkOptionMenu` or ttk fallback |
| `tb.Progressbar` | 5+ | ⚠️ Migrate | `ctk.CTkProgressBar` |
| `tb.Labelframe` | 5+ | ⚠️ Migrate | CTkFrame + CTkLabel |
| `tb.Toplevel` | 5+ | ⚠️ Migrate | `ctk.CTkToplevel` |
| `tb.Scrollbar` | 3+ | ⚠️ Migrate | `ctk.CTkScrollbar` |
| `tb.DateEntry` | 5+ | ⚠️ Problem | No equivalent - custom widget needed |
| `tb.Separator` | 2+ | ⚠️ Migrate | `ctk.CTkFrame` (thin line) |
| `tb.Checkbutton` | 2+ | ⚠️ Migrate | `ctk.CTkCheckBox` |

---

## Bootstyle Usage Analysis

### Bootstyle → CTk Color Mapping

| Bootstyle | Usage Count | Semantic | CTk Color (light, dark) |
|-----------|-------------|----------|-------------------------|
| `primary` | 15+ | Primary action | `("#1f77b4", "#1f77b4")` (blue) |
| `secondary` | 20+ | Secondary action | `("#6c757d", "#6c757d")` (gray) |
| `success` | 10+ | Positive/create | `("#28a745", "#1e7e34")` (green) |
| `danger` | 15+ | Destructive | `("#dc3545", "#bd2130")` (red) |
| `warning` | 8+ | Caution | `("#ffc107", "#e0a800")` (yellow) |
| `info` | 15+ | Informational | `("#17a2b8", "#117a8b")` (cyan) |

**Action:** Create `src/ui/ctk_colors.py` with bootstyle mapping helpers

---

## Risk Assessment

### High Risk (P0 - Must Fix)
- ❌ splash.py - First impression
- ❌ login_dialog.py - Authentication gate
- ❌ topbar.py - Main navigation
- ⚠️ main_window_actions.py - Core actions

### Medium Risk (P1 - Phase 2-4)
- ⚠️ UI components (buttons, inputs, progress)
- ⚠️ Hub module (dashboard)
- ⚠️ Clientes obligations

### Low Risk (P2-P3)
- ✅ ttk.Treeview (correct usage)
- ✅ Tests (update after production)
- ✅ Scripts (can remain tb)

---

## Implementation Sequence (From Plan)

### Phase 1: Foundation (2-3 days) - P0
1. ✅ topbar_nav.py (DONE)
2. ✅ notifications_button.py (DONE)
3. ⬜ splash.py
4. ⬜ login_dialog.py
5. ⬜ topbar.py
6. ⬜ main_window_actions.py

### Phase 2: Dashboard (3-5 days)
1. ⬜ Hub module (8 files)
2. ⬜ Dashboard components

### Phase 3: Clientes (2-3 days)
1. ⬜ Obligations (3 files)
2. ⬜ Pickers (3 files)

### Phase 4: Components (4-6 days)
1. ⬜ buttons.py
2. ⬜ inputs.py
3. ⬜ progress_dialog.py
4. ⬜ notifications_popup.py
5. ⬜ misc.py
6. ⬜ scrollable_frame.py

### Phase 5: Secondary Modules (3-4 days)
1. ⬜ Tasks (DateEntry challenge)
2. ⬜ Passwords
3. ⬜ Anvisa (DateEntry challenge)
4. ⬜ Cashflow (DateEntry challenge)

### Phase 6: Placeholders (1-2 days)
1. ⬜ placeholders.py
2. ⬜ custom_dialogs.py

---

## Critical Challenges

### 1. DateEntry Widget (5+ files)
**Problem:** CustomTkinter has no date picker  
**Affected Files:**
- `src/features/cashflow/dialogs.py`
- `src/modules/clientes/views/obligation_dialog.py`
- `src/modules/tasks/views/task_dialog.py`
- `src/modules/anvisa/views/anvisa_screen.py` (multiple)

**Solution Options:**
1. Keep `ttkbootstrap.DateEntry` isolated
2. Create custom `CTkDatePicker` widget
3. Use third-party library (tkintercalendar)
4. Use CTkEntry with date validation

**Recommended:** Option 1 (short-term) + Option 2 (medium-term)

---

### 2. Labelframe (5+ files)
**Problem:** CTk has no Labelframe  
**Solution:** CTkFrame + CTkLabel on top

```python
def create_ctk_labelframe(parent, text):
    frame = ctk.CTkFrame(parent)
    label = ctk.CTkLabel(frame, text=text, anchor="w")
    label.pack(side="top", fill="x", padx=10, pady=(5, 0))
    return frame
```

---

### 3. Combobox vs OptionMenu
**Problem:** CTkOptionMenu != ttk.Combobox (no autocomplete)  
**Solution:** Use ttk.Combobox for complex cases (search, filtering)

---

### 4. Shutdown Errors
**Problem:** "invalid command name ... after script" on close  
**Root Cause:** Uncanceled after() jobs  
**Solution:** Implement defensive shutdown in Phase B

---

## Validation Checklist

After each phase:
- [ ] python scripts/validate_ctk_policy.py (0 violations)
- [ ] python main.py (manual test: start, theme toggle, navigate, close)
- [ ] python -m pytest (relevant tests pass)
- [ ] pre-commit run --all-files (hooks pass)
- [ ] No "invalid command name" errors on shutdown

---

## Next Steps

1. **Immediate:** Fix shutdown errors (Phase B)
2. **Next:** Migrate P0 files (splash, login, topbar)
3. **Then:** Follow PLANO_MIGRACAO_CUSTOMTKINTER.md phases

---

**Report Generated:** 2026-01-16  
**Audit Tool:** ripgrep (rg)  
**Coverage:** 100% of src/, tests/, scripts/, tools/
