# -*- coding: utf-8 -*-
"""Configuração pública de runtime embutida no cliente.

Contém APENAS valores públicos (anon/publishable key do Supabase).
NÃO contém segredos do servidor (service_role, database password, etc.).

A anon key é projetada para ser exposta em clientes (web, mobile, desktop).
A segurança é garantida por Row Level Security (RLS) no servidor Supabase.

Ref: https://supabase.com/docs/guides/api/api-keys
  - anon key  = "publishable" / client-side safe
  - service_role key = server-side secret (NÃO está aqui)
"""

RUNTIME_DEFAULTS: dict[str, str] = {
    "SUPABASE_URL": "https://fnnvuvntcsuqnzsvkvhd.supabase.co",
    "SUPABASE_ANON_KEY": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZubnZ1dm50Y3N1cW56c3ZrdmhkIiwi"
        "cm9sZSI6ImFub24iLCJpYXQiOjE3NTk4NjIwNzksImV4cCI6MjA3NTQzODA3OX0."
        "cNX1QIZjzGrghRIwvs2AcSCKfowMBgOPqJgwHpV3-cE"
    ),
    "SUPABASE_BUCKET": "rc-docs",
    "SUPABASE_DEFAULT_ORG": "0a7c9f39-4b7d-4a88-8e77-7b88a38c6cd7",
}
