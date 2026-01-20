# Healthcheck do Módulo de Clientes

Guia rápido para validar performance, layout e ausência de leaks no módulo de clientes.

## Testes Unitários

```bash
# Rodar todos os testes do módulo clientes
python -m pytest tests/unit/modules/clientes/ -v --tb=short -x

# Rodar apenas testes de contrato de hardening
python -m pytest tests/unit/modules/clientes/test_hardening_contracts.py -v
```

## Performance (Treeview)

```bash
# Teste com 2000 linhas (baseline)
python scripts/perf_clients_treeview.py 2000

# Teste com 5000 linhas
python scripts/perf_clients_treeview.py 5000

# Teste com 10000 linhas (stress de render)
python scripts/perf_clients_treeview.py 10000

# Stress test completo (200 ciclos de criar/destruir)
python scripts/perf_clients_treeview.py --stress --stress-cycles 200
```

## Quickcheck (Validação Rápida)

```bash
# Verificação rápida (5000 linhas + stress curto opcional)
python scripts/clients_quickcheck.py

# Com stress test curto (50 ciclos)
python scripts/clients_quickcheck.py --stress
```

## Critérios de Aceite

| Métrica | Limite | Descrição |
|---------|--------|-----------|
| Render 2k linhas | ≤ 0.1s | Render inicial de 2000 linhas |
| Render 5k linhas | ≤ 0.2s | Render inicial de 5000 linhas |
| Render 10k linhas | ≤ 0.5s | Render inicial de 10000 linhas |
| Refresh parcial | ≤ 0.1s | Update de 50 linhas in-place |
| Stress delta memória | ≤ 10MB | Após 100+ ciclos de criar/destruir |
| Stress estabilidade | Não crescer | Delta deve estabilizar, não crescer linearmente |

## Layout das Colunas

### Colunas Fixas (stretch=False, não crescem com a janela)
| Coluna | Largura | Minwidth | Alinhamento |
|--------|---------|----------|-------------|
| ID | 55px | 45px | center |
| CNPJ | 130px | 120px | center |
| WhatsApp | 115px | 105px | center |
| Última Alteração | 170px | 160px | center |

### Colunas Flex (stretch=True, crescem proporcionalmente)
| Coluna | Largura Base | Minwidth | Peso | Alinhamento |
|--------|--------------|----------|------|-------------|
| Razão Social | 420px | 240px | 5 (36%) | center |
| Status | 300px | 190px | 4 (29%) | center |
| Observações | 260px | 170px | 3 (21%) | center |
| Nome | 200px | 150px | 2 (14%) | center |

### Customização de Alinhamento

Para alterar o alinhamento das colunas, edite `CLIENTS_COL_ANCHOR` em `src/ui/components/lists.py`:

```python
CLIENTS_COL_ANCHOR = {
    "ID": "center",
    "Razao Social": "center",
    "CNPJ": "center",
    "Nome": "center",
    "WhatsApp": "center",
    "Observacoes": "center",
    "Status": "center",
    "Ultima Alteracao": "center",
}
```

## Funcionalidades de UX

### Normalização de Texto
- Valores com quebras de linha (`\n`, `\r\n`) são convertidos para espaço
- Espaços múltiplos são colapsados em um único espaço
- Evita que texto "quebre" em duas linhas dentro de uma célula
- Aplicado em: Razão Social, Nome, Status, Observações, CNPJ, WhatsApp

### Rowheight (Altura da Linha)
- Calculado dinamicamente: linespace da fonte + **14px** de padding
- Mínimo garantido: **34px** (linhas bem espaçadas, sem corte)
- Aplicado apenas no style `Clientes.Treeview`

### Tooltip para Texto Truncado
- Ao passar o mouse sobre células de Razão Social, Nome ou Observações
- Se o texto estiver truncado (maior que a largura da coluna), exibe tooltip com texto completo
- Tooltip tem fundo amarelo claro para destacar

### Redimensionamento Automático
- Colunas flex (Razão Social, Nome, Status, Observações) crescem/encolhem automaticamente com a janela
- Debounce de 50ms para evitar recálculos excessivos durante resize
- Distribuição proporcional por peso: Razão(5) > Status(4) > Obs(3) > Nome(2)
- Respeita minwidth para não encolher demais

### Zebra Striping
- Linhas alternadas com cores ligeiramente diferentes
- Tema claro: cor fixa `#e0e0e0` (cinza bem visível) para linhas ímpares
- Tema escuro: delta de luminosidade +0.18 para contraste
- Workaround aplicado para bug do Tk 8.6.9 (fixed_map)
- Seleção sempre legível via `style.map` com cores do tema

### Tag "has_obs"
- Aplicada em linhas com observações não vazias
- Apenas foreground (azul) e font (negrito) — NÃO define background
- Não interfere com o zebra striping

## Sinais Vermelhos 🚨

### TclError / Invalid Command Name
```
TclError: invalid command name ".!frame.!treeview"
```
**Causa**: Callback executando após widget destruído.  
**Verificar**: `destroy()` cancela todos os `after()` pendentes.

### UI Travando / Lag Perceptível
**Causa**: Renderização síncrona de muitas linhas ou I/O no main thread.  
**Verificar**: `carregar_async` usa ThreadPoolExecutor + polling via `after()`.

### Seleção Ilegível (Invisível sobre Zebra)
**Causa**: Tag de zebra sobrescrevendo cor de seleção.  
**Verificar**: `style.map("Clientes.Treeview", background=[("selected", ...)])` existe.

### Texto Truncado sem Tooltip
**Causa**: Tooltip não configurado ou coluna não está em `tooltip_columns`.  
**Verificar**: `_setup_treeview_tooltip` inclui a coluna desejada.

### Memória Crescendo Linearmente no Stress
**Causa**: Leak de referências (callbacks, closures, widgets não destruídos).  
**Verificar**: Delta de memória deve estabilizar após ~10 ciclos, não crescer indefinidamente.

### ttk::ThemeChanged Errors
```
can't invoke "event" command: application has been destroyed
```
**Causa**: Bug interno do ttkbootstrap ao criar/destruir múltiplas janelas Tk.  
**Mitigação**: Stress test usa única janela raiz com frames internos.

## Arquivos Relevantes

| Arquivo | Responsabilidade |
|---------|------------------|
| `src/ui/components/lists.py` | Factory do Treeview + style + zebra + tooltip + resize |
| `src/config/constants.py` | Larguras das colunas |
| `src/modules/clientes/views/main_screen_dataflow.py` | Async loading + chunked render |
| `src/modules/clientes/views/main_screen_frame.py` | Lifecycle + destroy cleanup |
| `src/modules/clientes/controllers/connectivity.py` | Monitor de conectividade (after) |
| `scripts/perf_clients_treeview.py` | Testes de performance |
| `scripts/clients_quickcheck.py` | Validação rápida automatizada |
