"""Test CTkTreeview API"""

from CTkTreeview import CTkTreeview
from src.ui.ctk_config import ctk

# Test basic API
root = ctk.CTk()
root.geometry("400x300")

tree = CTkTreeview(root, columns=("type",))
tree.pack(fill="both", expand=True, padx=10, pady=10)

# Test methods available
print("Methods:", [m for m in dir(tree) if not m.startswith("_") and callable(getattr(tree, m))])

# Try to insert items (similar to ttk.Treeview API)
try:
    # Test if insert method exists
    if hasattr(tree, "insert"):
        tree.insert("", "end", text="Test Item 1", values=("type1",))
        tree.insert("", "end", text="Test Item 2", values=("type2",))
        print("✓ insert() works")
    else:
        print("✗ No insert() method")

    # Test heading
    if hasattr(tree, "heading"):
        tree.heading("#0", text="Name")
        print("✓ heading() works")
    else:
        print("✗ No heading() method")

    # Test column
    if hasattr(tree, "column"):
        tree.column("#0", width=200)
        print("✓ column() works")
    else:
        print("✗ No column() method")

except Exception as e:
    print(f"Error: {e}")

root.destroy()
print("Test complete")
