# Ações Propostas (DRY-RUN)
**Data:** 2025-10-18 09:12:09
**ATENÇÃO:** Nenhuma ação será executada agora.
---

## 🗑️ Remover Órfãos

### Ação 1: Remover `detectors\cnpj_card.py`

**Razão:** Módulo não é importado por ninguém

**Passos:**
1. Verificar se não é usado via `importlib` ou `__import__`
2. Mover para `ajuda/_quarentena/`
3. Testar tudo
4. Remover após confirmação


**Total de ações:** 1
