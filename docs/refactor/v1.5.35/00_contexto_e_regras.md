# 00 - Contexto e Regras da Refatoração

> **Versão de referência:** v1.5.35  
> **Data:** 2025-01-02

---

## 🏆 Regras de Ouro

### 1. NÃO QUEBRAR O APP
- O aplicativo **deve funcionar** após cada fase
- Testes (`pytest`) devem passar
- Build (`pyinstaller rcgestor.spec`) deve gerar executável funcional

### 2. REFATORAÇÃO INCREMENTAL
- Uma fase por vez
- Cada fase é um commit isolado
- Se algo quebrar, fácil de fazer rollback

### 3. COMMITS PEQUENOS
- Um commit por fase concluída
- Mensagem clara descrevendo a mudança
- **IMPORTANTE:** NÃO commitar durante a documentação baseline

### 4. DOCUMENTAÇÃO PRIMEIRO
- Antes de mover código, documentar o estado atual
- Registrar todos os imports afetados
- Mapear dependências entre módulos

---

## 📐 Rationale: src-layout vs Código Espalhado

### Situação Atual (código espalhado)
```
projeto/
├── main.py           # entrypoint
├── src/              # código principal
├── infra/            # infraestrutura (FORA de src)
├── data/             # repositórios (FORA de src)
├── adapters/         # adaptadores (FORA de src)
├── security/         # criptografia (FORA de src)
└── tests/
```

**Problemas:**
1. Imports inconsistentes (`from infra...` vs `from src.infra...`)
2. `sitecustomize.py` precisa manipular `sys.path` para funcionar
3. Dificulta empacotamento (PyInstaller precisa coletar de múltiplas raízes)
4. Risco de conflito de nomes com pacotes instalados

### Situação Alvo (src-layout)
```
projeto/
├── main.py           # entrypoint
├── src/              # TODO o código aqui
│   ├── infra/
│   ├── data/
│   ├── adapters/
│   ├── security/
│   └── ...
└── tests/
```

**Benefícios:**
1. Imports consistentes (`from src.infra...`)
2. `sitecustomize.py` simplificado ou removido
3. PyInstaller coleta tudo de `src/`
4. Sem risco de conflito de nomes

---

## ⚠️ Nota sobre sitecustomize.py

O arquivo `sitecustomize.py` na raiz do projeto **manipula `sys.path`** para permitir imports das pastas fora de `src/`.

### Conteúdo atual (relevante):

```python
"""Project-level sitecustomize to expose src-style packages on sys.path."""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
for rel_path in ("src", "infra", "adapters"):
    abs_path = os.path.join(_ROOT, rel_path)
    if os.path.isdir(abs_path) and abs_path not in sys.path:
        sys.path.insert(0, abs_path)
```

### Impacto nos Imports

Este arquivo faz com que:
- `from infra.xxx` funcione (mesmo `infra/` estando fora de `src/`)
- `from adapters.xxx` funcione
- `from src.xxx` funcione

**Após a refatoração:**
- O `sitecustomize.py` poderá ser simplificado
- Apenas `src` precisará estar no path
- Todos os imports serão `from src.xxx`

---

## 📋 Checklist Pré-Refatoração

- [x] Documentação baseline criada
- [x] Árvore de diretórios mapeada
- [x] Imports atuais levantados
- [x] Entrypoints identificados
- [x] Arquivos grandes listados
- [ ] Backup/branch de segurança criado
- [ ] Testes passando no estado atual
