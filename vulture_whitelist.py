# vulture_whitelist.py
# Whitelist para o Vulture - itens que parecem não usados mas são necessários.
# Uso: python -m vulture src vulture_whitelist.py --min-confidence 100

# Protocol methods (NotificationsRepository) - parâmetros são parte da interface
exclude_actor_email  # noqa: F821 - usado em Protocol methods
hidden_before_iso  # noqa: F821 - usado em Protocol methods
before_iso  # noqa: F821 - usado em Protocol methods

# Fallback function parameters (archives.py)
out_dir  # noqa: F821 - parâmetro de fallback, função só levanta exceção
