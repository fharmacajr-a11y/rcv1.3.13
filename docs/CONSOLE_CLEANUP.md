# Limpeza de Console: Redução de Ruído

**Data:** 2026-02-01  
**Tipo:** Melhoria de UX (Developer Experience)  
**Status:** ✅ Implementado

---

## 🎯 Objetivo

Reduzir ruído no console durante execução da aplicação, removendo warnings cosmétidos que não afetam funcionalidade.

---

## 🔧 Implementações

### 1. Filtro de Linhas em Tempo Real

**Arquivo:** [src/core/utils/stdio_line_filter.py](../src/core/utils/stdio_line_filter.py)

**Funcionalidade:**
- Stream wrapper que filtra linhas baseado em regex patterns
- Processa linha por linha sem captura/replay completo
- Preserva tracebacks e outros outputs importantes

**Classe Principal:**
```python
class LineFilterStream:
    """Stream wrapper que filtra linhas baseado em patterns regex."""
    
    def write(self, text: str) -> int:
        # Bufferiza até '\n'
        # Descarta linhas que matcham patterns
        # Escreve outras normalmente
```

**API:**
```python
def install_line_filters(
    drop_patterns: list[str],
    streams: tuple[str, ...] = ("stdout", "stderr"),
) -> None:
    """Instala filtros de linha em sys.stdout/stderr."""
```

### 2. Supressão de Warning do Storage

**Arquivo:** [src/core/app.py](../src/core/app.py)

**Warning Suprimido:**
```
Storage endpoint URL should have a trailing slash.
```

**Implementação:**
```python
if os.getenv("RC_SUPPRESS_STORAGE_WARNING", "1") == "1":
    from src.core.utils.stdio_line_filter import install_line_filters
    install_line_filters(
        drop_patterns=[
            r"Storage endpoint URL should have a trailing slash\.",
        ],
        streams=("stdout", "stderr"),
    )
```

**Controle via ENV:**
- `RC_SUPPRESS_STORAGE_WARNING=1` (padrão): Warning suprimido
- `RC_SUPPRESS_STORAGE_WARNING=0`: Warning visível (debug)

**Instalação:**
- Logo no início do `if __name__ == "__main__":`
- ANTES de qualquer import que possa importar Supabase/storage3
- Garante captura desde o boot

### 3. Redução de Logs de Performance

**Arquivo:** [src/modules/clientes/ui/views/client_files_dialog.py](../src/modules/clientes/ui/views/client_files_dialog.py)

**Função:** `log_slow()`

**Mudanças:**
1. **Threshold aumentado:** 250ms → 1000ms
   - Operações de rede até 1s são consideradas normais
   - Reduz ruído em conexões lentas

2. **Controle via ENV:**
   ```python
   debug_enabled = os.getenv("RC_DEBUG_SLOW_OPS", "0") == "1"
   ```
   - `RC_DEBUG_SLOW_OPS=0` (padrão): Logs desabilitados
   - `RC_DEBUG_SLOW_OPS=1`: Logs habilitados (debug)

**Antes:**
```
[ClientFiles] Operação lenta: list_files levou 540ms (>250ms)
```

**Depois:**
- Nada (a menos que >1000ms E RC_DEBUG_SLOW_OPS=1)

---

## ✅ Validações

### Testes Executados

1. ✅ **Compilação:** `python -m compileall src -q`
2. ✅ **Guards FASE 4D:** 4/4 passando
3. ✅ **Smoke test UI:** 4/4 passando
4. ✅ **Teste isolado:** Filtro suprime warning corretamente
5. ✅ **App inicializa:** Sem warnings no console

### Teste do Filtro

```python
# Antes do filtro:
print("Storage endpoint URL should have a trailing slash.")
# → Linha aparece no console

# Depois do filtro:
print("Storage endpoint URL should have a trailing slash.")
# → Linha NÃO aparece no console (suprimida)
```

**Resultado:** ✅ Filtro funciona como esperado

---

## 📊 Impacto

### Antes (Console Ruidoso)

```
Storage endpoint URL should have a trailing slash.
2026-02-01 10:00:00 | INFO | startup | Logging level ativo: INFO
Storage endpoint URL should have a trailing slash.
2026-02-01 10:00:01 | WARNING | [ClientFiles] Operação lenta: list_files levou 540ms (>250ms)
```

### Depois (Console Limpo)

```
2026-02-01 10:00:00 | INFO | startup | Logging level ativo: INFO
```

**Redução de Ruído:** ~70% menos linhas no console durante uso normal

---

## 🔧 Como Usar

### Para Usuários Finais

**Modo Normal (padrão):**
- Console limpo, sem warnings cosméticos
- Apenas erros reais aparecem

### Para Desenvolvedores

**Ativar debug de Storage:**
```bash
set RC_SUPPRESS_STORAGE_WARNING=0
python main.py
```

**Ativar debug de performance:**
```bash
set RC_DEBUG_SLOW_OPS=1
python main.py
```

**Ativar ambos:**
```bash
set RC_SUPPRESS_STORAGE_WARNING=0
set RC_DEBUG_SLOW_OPS=1
python main.py
```

---

## 🛡️ Garantias

### O que NÃO foi afetado:

1. ✅ **Erros reais continuam visíveis**
   - Tracebacks preservados
   - Exceptions não filtradas

2. ✅ **Funcionalidade intacta**
   - Storage funciona igual
   - Performance instrumentada igual
   - Apenas visualização mudou

3. ✅ **Logging system preservado**
   - Logger.warning/error/info intocados
   - Apenas print() de biblioteca externa filtrado

---

## 🧪 Casos de Teste

### Teste 1: Warning do Storage

**Antes:**
```bash
$ python main.py
Storage endpoint URL should have a trailing slash.
[App carrega...]
```

**Depois:**
```bash
$ python main.py
[App carrega sem warning]
```

### Teste 2: ClientFilesDialog

**Antes:**
```
[ClientFiles] Operação lenta: list_files levou 540ms (>250ms)
[ClientFiles] Operação lenta: list_files levou 320ms (>250ms)
```

**Depois:**
```
[Nenhum log, a menos que RC_DEBUG_SLOW_OPS=1]
```

### Teste 3: Erro Real

**Antes e Depois (IGUAL):**
```python
Traceback (most recent call last):
  File "...", line X, in <module>
    raise ValueError("Erro real")
ValueError: Erro real
```

**Garantia:** Erros reais SEMPRE aparecem

---

## 📝 Arquivos Modificados

1. **Criado:** `src/core/utils/stdio_line_filter.py`
   - 100 linhas
   - `LineFilterStream` class
   - `install_line_filters()` function

2. **Modificado:** `src/core/app.py`
   - +14 linhas (bloco de instalação do filtro)
   - No início do `if __name__ == "__main__":`

3. **Modificado:** `src/modules/clientes/ui/views/client_files_dialog.py`
   - `log_slow()`: threshold 250ms → 1000ms
   - Adicionado check de `RC_DEBUG_SLOW_OPS`
   - Chamada: `log_slow(..., threshold_ms=250)` → `log_slow(...)`

---

## 🎓 Lições Aprendadas

### 1. Filtros de Stream Devem Ser Line-Based

**Problema:**
- Capturar tudo e fazer replay pode perder outputs em tempo real
- Buffering completo pode quebrar progressbars/spinners

**Solução:**
- Processar linha por linha (`\n` como delimitador)
- Escrever imediatamente no stream original
- Buffering mínimo (apenas linha atual)

### 2. Instalar Filtros o Mais Cedo Possível

**Problema:**
- Se instalar após imports, warnings já foram emitidos

**Solução:**
- Instalar ANTES de qualquer import relevante
- No topo do `if __name__ == "__main__":`

### 3. Sempre Ter Chave de Escape

**Problema:**
- Filtros podem esconder informação útil em debug

**Solução:**
- Variáveis de ambiente para desabilitar filtros
- `RC_SUPPRESS_STORAGE_WARNING=0`
- `RC_DEBUG_SLOW_OPS=1`

---

## ✅ Checklist de Validação

- [x] Compilação OK
- [x] Guards FASE 4D OK
- [x] Smoke test OK
- [x] Filtro funciona isoladamente
- [x] Warning Storage suprimido
- [x] Logs de performance reduzidos
- [x] Erros reais preservados
- [x] ENV vars documentadas
- [x] Funcionalidade intacta

---

**Status:** ✅ **PRONTO PARA COMMIT**

**Commit message:**
```
chore(console): suprimir warning storage + reduzir ruído slow ops

- Cria LineFilterStream para filtro de linhas em tempo real
- Suprime "Storage endpoint URL should have a trailing slash."
- Aumenta threshold de log_slow: 250ms → 1000ms
- Adiciona controle via ENV:
  - RC_SUPPRESS_STORAGE_WARNING=0 (mostra warning)
  - RC_DEBUG_SLOW_OPS=1 (mostra logs performance)
- Reduz ruído no console em ~70%
- Funcionalidade preservada (erros reais visíveis)

Validações: 5/5 passando
```
