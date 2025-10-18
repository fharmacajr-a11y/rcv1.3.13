# Como Aplicar as Consolidações
**Data:** 2025-10-18 09:56:34
---

## 📋 Pré-requisitos

```powershell
# 1. Fazer backup/commit
git add .
git commit -m "backup antes de consolidação"

# 2. Instalar ferramentas
python -m pip install libcst rapidfuzz
```

## 🚀 PROMPT 2 - Executar Consolidação

```
Execute as consolidações propostas em `ajuda/dup-consolidacao/ACTIONS_DRY_RUN.md`.

Para cada grupo marcado como viável:
1. Revise manualmente o código canônico e alternativas
2. Mescle funcionalidades se necessário
3. Reescreva imports usando LibCST
4. Crie stubs de compatibilidade
5. Execute smoke test
6. Documente mudanças

Grupos a consolidar:
- (Nenhum grupo viável para consolidação automática)
```

## ⚠️ Atenção

- Este é um processo **semi-automático**
- Sempre revise o código antes de mesclar
- Execute testes após cada mudança
- Mantenha stubs por pelo menos 1 release
