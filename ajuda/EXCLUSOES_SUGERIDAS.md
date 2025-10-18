# 📦 Exclusões Sugeridas para Otimização de Bundle (PyInstaller)

**Projeto:** RC-Gestor v1.0.34  
**Build Atual:** ONE-FILE (52.49 MB)  
**Data:** 2025-10-18

---

## 🎯 Objetivo

Reduzir o tamanho do executável eliminando módulos/bibliotecas que não são usados pela aplicação, sem comprometer a funcionalidade.

---

## 📊 Análise de Dependências

### **Módulos Potencialmente Desnecessários**

#### 1. **Bibliotecas de Desenvolvimento/Testing** (alta prioridade)
```python
excludes=[
    'pytest',           # Framework de testes (não usado em produção)
    'unittest',         # Testes padrão Python (não usado em produção)
    'doctest',          # Testes em docstrings
    'nose',             # Framework de testes alternativo
    'coverage',         # Análise de cobertura de testes
]
```
**Justificativa:** Ferramentas de desenvolvimento não são necessárias no executável final.

---

#### 2. **Módulos IPython/Jupyter** (média prioridade)
```python
excludes=[
    'IPython',          # Shell interativo
    'jupyter',          # Notebooks Jupyter
    'ipykernel',        # Kernel Jupyter
    'notebook',         # Interface Jupyter Notebook
]
```
**Justificativa:** Aplicação GUI não usa IPython/Jupyter.

---

#### 3. **Bibliotecas de Análise de Dados Não Usadas** (média prioridade)
```python
excludes=[
    'matplotlib',       # Gráficos (verificar se é usado)
    'numpy',            # Arrays numéricos (verificar se é usado)
    'pandas',           # DataFrames (verificar se é usado)
    'scipy',            # Computação científica
]
```
**Justificativa:** Validar se a aplicação realmente usa essas bibliotecas. Se não usa, excluir.

⚠️ **ATENÇÃO:** Antes de excluir, verificar imports com `grep -r "import pandas" .` etc.

---

#### 4. **Módulos de Compilação/Build** (baixa prioridade)
```python
excludes=[
    'distutils',        # Ferramentas de distribuição
    'setuptools',       # Build de pacotes (verificar se PyInstaller precisa)
    'pkg_resources',    # Gerenciamento de recursos de pacotes
]
```
**Justificativa:** Ferramentas de build não são necessárias em runtime.

⚠️ **ATENÇÃO:** `setuptools` pode ser necessário para alguns hooks do PyInstaller.

---

#### 5. **Bibliotecas de Rede/HTTP Redundantes** (baixa prioridade)
```python
excludes=[
    'urllib3.contrib',  # Extensões urllib3 não usadas
    'requests.packages.urllib3.contrib',
]
```
**Justificativa:** Apenas componentes principais de `requests` são necessários.

---

## 🔍 Como Validar Exclusões

### **Método 1: Grep nos Imports**
```powershell
# Verificar se pytest é importado
grep -r "import pytest" .
grep -r "from pytest" .

# Verificar pandas
grep -r "import pandas" .
grep -r "from pandas" .

# Verificar matplotlib
grep -r "import matplotlib" .
grep -r "from matplotlib" .
```

---

### **Método 2: Teste com Exclusões Incrementais**

1. **Adicionar exclusões no `rcgestor.spec`:**
   ```python
   excludes=[
       'pytest',
       'unittest',
       'doctest',
   ],
   ```

2. **Rebuild:**
   ```powershell
   pyinstaller .\rcgestor.spec --clean --noconfirm
   ```

3. **Testar executável:**
   - Abrir interface
   - Testar funcionalidades críticas (lista, cadastro, upload, changelog)
   - Se funcionar, adicionar mais exclusões

4. **Repetir até otimizar sem quebrar funcionalidades**

---

## 📏 Estimativa de Economia

| Módulo(s)               | Tamanho Estimado | Prioridade |
|-------------------------|------------------|------------|
| pytest + unittest       | ~5-8 MB          | Alta       |
| IPython + Jupyter       | ~10-15 MB        | Média      |
| matplotlib (se não usado)| ~8-12 MB        | Média      |
| numpy (se não usado)    | ~15-20 MB        | Média      |
| pandas (se não usado)   | ~20-30 MB        | Média      |
| **Total Potencial**     | **58-85 MB**     | -          |

⚠️ **Nota:** RC-Gestor atual tem **52.49 MB**, então se excluirmos tudo desnecessário, podemos reduzir para **~15-30 MB**.

---

## ✅ Exclusões Recomendadas (Seguras)

```python
# Adicionar no rcgestor.spec -> Analysis()
excludes=[
    # Testing frameworks
    'pytest',
    'unittest',
    'doctest',
    'nose',
    'coverage',

    # IPython/Jupyter
    'IPython',
    'jupyter',
    'ipykernel',
    'notebook',

    # (Adicionar outros após validação manual)
],
```

---

## 🚀 Próximos Passos

1. ✅ **Validar imports** com grep
2. ⏳ **Testar exclusões incrementalmente**
3. ⏳ **Documentar impacto de cada exclusão**
4. ⏳ **Atualizar rcgestor.spec com lista final**
5. ⏳ **Gerar build otimizado e comparar tamanhos**

---

## 📝 Notas de UPX

- **UPX não está disponível** no sistema atual
- **Impacto:** Sem compressão adicional do executável
- **Solução alternativa:** Instalar UPX manualmente:
  ```powershell
  # Download: https://github.com/upx/upx/releases
  # Extrair para C:\Tools\upx\
  # Adicionar ao PATH ou copiar upx.exe para pasta do projeto
  ```

---

**Autor:** GitHub Copilot  
**Data:** 2025-10-18  
**Versão:** 1.0
