# Third-Party Software Notices and Information

This project incorporates material from the projects listed below (collectively, "Third Party Code"). The original copyright notice and license under which we received such Third Party Code are set forth below. This Third Party Code is licensed to you under their original license terms. We reserve all other rights not expressly granted, whether by implication, estoppel or otherwise.

---

## 1. CTkTreeview

**Version:** 0.1.0  
**License:** MIT License  
**Upstream:** https://github.com/JohnDevlopment/CTkTreeview  
**Commit:** 31858b1fbfa503eedbb9379d01ac7ef8e6a555ea  
**Vendorized:** Yes (located at `src/third_party/ctktreeview/`)  
**Date Vendorized:** 2025-01-20  
**Modifications:** Removed `icecream` import from `treeview.py` (debug tool, not used in production)

**License File:** [src/third_party/ctktreeview/LICENSE](src/third_party/ctktreeview/LICENSE)

**Vendor Documentation:** [src/third_party/ctktreeview/README.md](src/third_party/ctktreeview/README.md)

**Purpose:** Provides treeview widget with hierarchical data display for CustomTkinter applications.

---

## License Compliance Notes

### CTkTreeview (MIT License)

Copyright (c) 2024 JohnDevlopment

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## How to Update Third-Party Code

### CTkTreeview

To update the vendorized CTkTreeview:

1. Check for updates:
   ```bash
   git ls-remote https://github.com/JohnDevlopment/CTkTreeview.git refs/heads/main
   ```

2. Clone and checkout specific commit:
   ```bash
   git clone https://github.com/JohnDevlopment/CTkTreeview.git /tmp/ctk
   cd /tmp/ctk
   git checkout <new_commit_hash>
   ```

3. Copy to vendor directory:
   ```bash
   cp -r CTkTreeview/* src/third_party/ctktreeview/
   ```

4. Reapply modifications:
   - Remove `from icecream import ic` from `treeview.py`
   - Remove `example.py` and `__main__.py` if present

5. Test:
   ```bash
   python -m compileall -q src/third_party/ctktreeview
   python scripts/validate_ui_theme_policy.py
   python scripts/smoke_ui.py
   ```

6. Update this file with new commit hash and date

---

## Dependency Audit Trail

| Library | Version | License | Vendorized | Commit Hash | Last Updated |
|---------|---------|---------|------------|-------------|--------------|
| CTkTreeview | 0.1.0 | MIT | Yes | 31858b1 | 2025-01-20 |

---

**Last Updated:** 2025-01-20  
**Audit Contact:** See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
