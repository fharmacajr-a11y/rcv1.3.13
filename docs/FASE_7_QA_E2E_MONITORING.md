# FASE 7 - QA/E2E/Monitoring

**Data:** 2026-02-01  
**Status:** ⏳ Planejamento  
**Dependência:** FASE 5A concluída  
**Próximo:** PASSO 1 - Smoke Automatizado

---

## 🎯 Objetivo

Estabelecer infraestrutura de qualidade, observabilidade e monitoring para o RC Gestor, garantindo detecção precoce de bugs e visibilidade de problemas em produção.

---

## 📊 Escopo da FASE 7

### Fora de Escopo
- **Testes E2E web-based** (Selenium/Playwright): Incompatível com desktop Tkinter
- **Load testing**: Aplicação desktop single-user
- **A/B testing**: Não aplicável ao contexto

### Dentro de Escopo
- **Smoke test automatizado**: Tkinter headless com mocks
- **Crash reporting**: Sentry integration
- **Performance telemetria**: Timings + counters chave
- **Auto-update (planejamento)**: ADR e design apenas

---

## ✅ PASSO 1 - Smoke Test Automatizado (Tkinter Headless)

### Objetivo

Criar harness de teste E2E para validar fluxos críticos sem interação humana, executável em CI.

### Implementações

#### 1.1 Tkinter Test Harness

**Arquivo:** `tests/e2e/tkinter_harness.py`

**Funcionalidade:**
- Cria root Tkinter em modo headless (sem display real)
- `root.update()` / `root.update_idletasks()` para processar event loop
- `after()` callbacks são executados via `root.update()`
- Mocks de Supabase/API para evitar dependências externas

**Conceito:**
Tkinter não requer display real para testes. `root.update()` processa eventos pendentes, permitindo validar callbacks e state changes.

**API:**
```python
import tkinter as tk
from tests.e2e.tkinter_harness import TkinterTestHarness

def test_hub_loads():
    with TkinterTestHarness() as root:
        hub = HubScreen(root)
        root.update()  # Processa after(0) do deferred build

        # Validações
        assert hub.winfo_exists()
        assert "Carregando" not in hub.get_text()
```

#### 1.2 Smoke Tests E2E

**Arquivo:** `tests/e2e/test_smoke_critical_flows.py`

**Casos de Teste:**
1. **Login Flow:**
   - Mock autenticação
   - Validar transição para MainWindow
   - Footer exibe email do usuário

2. **Hub Loading:**
   - Placeholder aparece
   - Deferred build executa via after(0)
   - Destroy cancela callbacks pendentes

3. **Clientes CRUD:**
   - Lista carrega (mock DB)
   - Busca filtra resultados
   - Exportação gera arquivo

**Validação:**
```bash
pytest tests/e2e/ -v
# ✅ 15 passed
```

### Critérios de Aceite

- [ ] Harness Tkinter headless funcional
- [ ] 15+ smoke tests E2E cobrindo fluxos críticos
- [ ] Executável em CI (GitHub Actions)
- [ ] Tempo de execução <5min
- [ ] Mocks de Supabase/API isolam testes de rede

---

## 📡 PASSO 2 - Crash Reporting (Sentry)

### Objetivo

Capturar exceções não tratadas em produção e enviar para Sentry para análise e triage.

### Implementações

#### 2.1 Sentry SDK Integration

**Arquivo:** `src/infra/monitoring/sentry_config.py`

**Funcionalidade:**
- Inicializa Sentry SDK com DSN do ambiente
- Captura exceções globais (sys.excepthook)
- Breadcrumbs para rastreamento de ações do usuário
- Context: versão do app, SO, user ID anonimizado

**ENV Vars:**
```bash
RC_SENTRY_DSN=https://...@sentry.io/...
RC_SENTRY_ENVIRONMENT=production  # ou staging/dev
```

**Código:**
```python
import sentry_sdk
from src.version import __version__

def init_sentry():
    if dsn := os.getenv("RC_SENTRY_DSN"):
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("RC_SENTRY_ENVIRONMENT", "production"),
            release=f"rcgestor@{__version__}",
            traces_sample_rate=0.1,  # 10% de performance traces
        )
```

#### 2.2 Breadcrumbs Estratégicos

**Locais:**
- Login (success/failure)
- Navegação de telas (router)
- CRUD operations (criar/editar/deletar)
- Exportação de arquivos
- Erros de rede (API calls)

**API:**
```python
from sentry_sdk import add_breadcrumb

add_breadcrumb(
    category="navigation",
    message="User navigated to Hub",
    level="info"
)
```

### Critérios de Aceite

- [ ] Sentry SDK integrado e inicializado no startup
- [ ] Exceções não tratadas enviadas para Sentry
- [ ] Breadcrumbs registram ações críticas
- [ ] Context inclui: versão, SO, user_id (anonimizado)
- [ ] Opt-out via `RC_SENTRY_DSN` vazio (privacy)

---

## 📊 PASSO 3 - Telemetria de Performance

### Objetivo

Coletar métricas de performance críticas e agregar para análise de tendências.

### Implementações

#### 3.1 Performance Counters

**Arquivo:** `src/infra/monitoring/telemetry.py`

**Métricas:**
- `startup.duration` - Tempo total de startup (ms)
- `hub.load_time` - Tempo de carregamento do Hub (ms)
- `clientes.list_time` - Tempo de carregamento da lista (ms)
- `exports.duration` - Tempo de exportação (ms)
- `api.response_time` - Latência de chamadas API (ms)

**Storage:**
- Local: JSON file com rolling window (últimos 1000 eventos)
- Opcional: Envio para backend analytics (future)

**API:**
```python
from src.infra.monitoring.telemetry import record_timing

with record_timing("startup.duration"):
    app.mainloop()

# Gera: {"metric": "startup.duration", "value": 1523, "timestamp": "2026-02-01T10:00:00"}
```

#### 3.2 Dashboard Local (Opcional)

**Arquivo:** `tools/telemetry_dashboard.py`

**Funcionalidade:**
- Lê JSON de métricas
- Plota gráficos com matplotlib
- P50/P90/P99 de timings

**Uso:**
```bash
python tools/telemetry_dashboard.py
# Abre janela com gráficos de performance
```

### Critérios de Aceite

- [ ] Telemetria registra timings críticos
- [ ] Storage local (JSON rolling window)
- [ ] Overhead <1% (profiling validation)
- [ ] Dashboard local exibe P50/P90/P99
- [ ] Opt-out via `RC_TELEMETRY_ENABLED=0`

---

## 🚀 PASSO 4 - Auto-Update (Planejamento/ADR)

### Objetivo

Documentar estratégia de auto-update para futuras iterações (não implementar neste ciclo).

### Deliverables

#### 4.1 ADR - Auto-Update Strategy

**Arquivo:** `docs/ADR/adr-007-auto-update-strategy.md`

**Conteúdo:**
- **Context:** Necessidade de updates automáticos sem reinstalação manual
- **Options:**
  - Squirrel (Electron-style, usado por apps desktop)
  - PyUpdater (Python-specific, mas manutenção baixa)
  - Custom solution (GitHub Releases + delta updates)
- **Decision:** TBD após spike técnico
- **Consequences:** Impacto em build/deploy pipeline

#### 4.2 Spike Técnico (Timeboxed)

**Tempo:** 4h
**Objetivo:** Prototipar solução de auto-update e validar viabilidade

**Tarefas:**
1. Testar PyUpdater com RC Gestor
2. Avaliar Squirrel.Windows
3. Prototipar custom solution (GitHub API + requests)
4. Comparar complexidade vs. benefício

**Output:** Relatório de spike com recomendação

### Critérios de Aceite

- [ ] ADR documentado com opções avaliadas
- [ ] Spike técnico executado (4h timeboxed)
- [ ] Recomendação final com prós/contras
- [ ] Plano de implementação (se aprovado) ou decisão de postergar

---

## 🔄 Fluxo de Implementação

### Ordem Sugerida

1. **PASSO 1 (Smoke):** Fundação de qualidade, executa rápido
2. **PASSO 2 (Sentry):** Visibilidade de crashes em produção
3. **PASSO 3 (Telemetria):** Dados para otimizações futuras
4. **PASSO 4 (Auto-update):** Planejamento, não bloqueia outros passos

### Dependências

```
PASSO 1 (Smoke) → PASSO 2 (Sentry) → PASSO 3 (Telemetria) → PASSO 4 (Auto-update ADR)
   ↓                    ↓                    ↓                         ↓
 CI/CD             Produção              Otimização              Design Only
```

---

## ✅ Validação Final

### Comandos de Gate

```bash
# Smoke E2E
pytest tests/e2e/ -v
# ✅ 15+ passed

# Sentry test (mock)
python -c "import sentry_sdk; sentry_sdk.init('test'); sentry_sdk.capture_message('test')"
# ✅ Sem erros

# Telemetria test
python -m src.infra.monitoring.telemetry --self-test
# ✅ Métricas gravadas em telemetry.json

# Compilação
python -m compileall src -q
# ✅ (sem output)
```

### Critérios de Conclusão

- [ ] Todos os 4 passos concluídos
- [ ] Smoke tests executam em CI (<5min)
- [ ] Sentry captura exceções em produção
- [ ] Telemetria coleta métricas sem overhead
- [ ] ADR de auto-update documentado

---

## 📊 Métricas de Sucesso

| Métrica | Baseline (Antes FASE 7) | Target (Depois FASE 7) |
|---------|-------------------------|-------------------------|
| Bugs detectados antes de prod | ~30% | ~70% |
| Tempo de triage de crashes | ~4h (manual repro) | ~30min (Sentry context) |
| Visibilidade de performance | Nenhuma | P50/P90/P99 tracked |
| CI execution time | ~8min | ~13min (+ 5min E2E) |

---

## 🎓 Referências

- **Tkinter Testing:** [Python Tkinter Testing Guide](https://stackoverflow.com/questions/tagged/tkinter+testing)
- **Sentry Python SDK:** [https://docs.sentry.io/platforms/python/](https://docs.sentry.io/platforms/python/)
- **PyUpdater:** [https://www.pyupdater.org/](https://www.pyupdater.org/)

---

**Status Atual:** ⏳ Planejamento  
**Próximo:** Iniciar PASSO 1 - Smoke Test Automatizado  
**Comando:**
```bash
git checkout -b feat/fase-7-smoke-e2e
```
