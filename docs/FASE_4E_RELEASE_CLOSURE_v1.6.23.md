# Fase 4E — Fechamento Visual e Contrato de Distribuição v1.6.23

**Data**: 2026-03-19
**Escopo**: Polimento final do EXE — paridade visual, assets, paths, contrato de release.
**Risco**: Mínimo. 0 linhas de lógica de negócio alteradas.

---

## 1. Resumo Executivo

### Corrigido nesta fase
| # | Correção | Arquivo | Linhas |
|---|----------|---------|--------|
| 1 | Logs redirecionados para `%LOCALAPPDATA%/RCGestor/logs` em frozen mode | `src/core/logs/configure.py` | +6 |
| 2 | Fallback de log em `logger.py` idem | `src/core/logs/logger.py` | +7 |
| 3 | Bootstrap procura `.env` ao lado do EXE | `src/core/bootstrap.py` | +5 |
| 4 | `rc.png` incluído no bundle PyInstaller | `rcgestor.spec` | +1 |
| 5 | Warnings de `sites.png`/`chatgpt.png` rebaixados para debug | `src/ui/components/topbar_nav.py` | 2 |

### O que restou
- Warning esperado: "Cliente Supabase não disponível" — aparece **somente** quando `.env` não acompanha o EXE (comportamento correto).
- Ícones `sites.png` e `chatgpt.png` não existem fisicamente. Botões usam texto-only (ícones estão comentados no código). Os warnings foram rebaixados para `debug`.

### Risco
**Zero impacto em lógica de negócio.** Todas as mudanças são paths, nível de log e inclusão de asset no bundle. 1035 testes passando.

---

## 2. Paridade Visual — Splash

### Análise do fluxo de splash

| Aspecto | Source (`python main.py`) | EXE frozen |
|---------|--------------------------|------------|
| Janela  | `CTkToplevel` com `overrideredirect(True)` | Idêntico |
| Logo    | `rc.png` via `resource_path()` → CWD | `rc.png` via `_MEIPASS` (bundled) |
| Texto   | "Gestor de Clientes 1.6.23" | Idêntico |
| Barra   | Progressbar determinada, 5s mínimo | Idêntico |
| Ícone   | `rc.ico` via `resource_path()` | `rc.ico` (bundled) |
| Cantos  | Transparência via `-transparentcolor` | Idêntico |
| Tamanho | 480×320 centralizado | Idêntico |

### Diferença encontrada (corrigida na Fase 4D)
`rc.png` **não estava no bundle** → splash aparecia sem logo no EXE. Corrigido adicionando `add_file(BASE / "rc.png", ".")` ao spec.

### Estado final
Splash no EXE é **visualmente idêntico** ao source. Logo presente, 480×320, centralizado, progress bar 5s, cantos transparentes.

---

## 3. Assets

### Referências de assets inspecionadas

| Asset | Existe no disco? | Bundled? | Usado em runtime? | Ação |
|-------|:-:|:-:|:-:|------|
| `rc.ico` | ✅ | ✅ | ✅ Ícone de todas as janelas | Nenhuma |
| `rc.png` | ✅ | ✅ (Fase 4D) | ✅ Splash logo | Adicionado ao spec |
| `assets/login/email.png` | ✅ | ✅ | ✅ Tela de login | Nenhuma |
| `assets/login/senha.png` | ✅ | ✅ | ✅ Tela de login | Nenhuma |
| `assets/topbar/inicioblack.png` | ✅ | ✅ | ✅ Botão Início light | Nenhuma |
| `assets/topbar/iniciolight.png` | ✅ | ✅ | ✅ Botão Início dark | Nenhuma |
| `assets/topbar/atualizarblack.png` | ✅ | ✅ | ✅ Botão Atualizar | Nenhuma |
| `assets/topbar/atualizarhigt.png` | ✅ | ✅ | ✅ Botão Atualizar dark | Nenhuma |
| `assets/topbar/sites.png` | ❌ | N/A | ❌ (ícone comentado) | Warning → debug |
| `assets/topbar/chatgpt.png` | ❌ | N/A | ❌ (ícone comentado) | Warning → debug |
| `assets/modulos/clientes/topbar clientes/procurar.png` | ✅ | ✅ | ✅ Busca | Nenhuma |

### Warnings eliminados
- `sites.png` → `_log.warning` rebaixado para `_log.debug` (asset nunca existiu, botão usa texto-only)
- `chatgpt.png` → idem
- Confirmado no log da execução mais recente (startup `5d277609`): **zero warnings de assets**

---

## 4. Paths Finais do App Congelado

### Verificação explícita

| Path | Comportamento fonte | Comportamento frozen | Status |
|------|--------------------|--------------------|--------|
| **Logs** | `artifacts/local/logs/` (relativo ao CWD) | `%LOCALAPPDATA%\RCGestor\logs\` | ✅ Verificado |
| **`.env`** | CWD + `resource_path(".env")` | `_MEIPASS` → ao lado do EXE → CWD | ✅ Verificado |
| **Settings** | `APP_DATA/settings.json` (cloud: memory-only) | Memory-only (RC_NO_LOCAL_FS=1) | ✅ Seguro |
| **DB/Docs** | `APP_DATA/db/`, `APP_DATA/clientes_docs/` | `%TEMP%/rc_void/` (cloud-only) | ✅ Seguro |
| **Assets** | `.` (CWD) via `resource_path()` | `_MEIPASS` (temp interno do PyInstaller) | ✅ Verificado |

### Pasta indevida ao lado do EXE
- `dist/artifacts/` — **NÃO é mais criada** (confirmado após execução de 20s)
- Nenhuma outra pasta visível criada ao lado do EXE

---

## 5. Contrato de Distribuição

### Conteúdo da release

```
📁 release/
├── RC-Gestor-Clientes-1.6.23.exe    # Executável principal (≈69 MB)
├── .env                              # OBRIGATÓRIO - credenciais Supabase
└── CHANGELOG.md                      # Opcional - histórico de versões
```

### O que DEVE estar junto do EXE

| Arquivo | Obrigatório | Descrição |
|---------|:-----------:|-----------|
| `.env` | **SIM** | Contém `SUPABASE_URL` e `SUPABASE_KEY` (ou `SUPABASE_ANON_KEY`). Sem ele, o app abre mas não conecta à nuvem. |

### O que NÃO deve ser empacotado/distribuído

| Item | Motivo |
|------|--------|
| `.env` dentro do EXE | P0-002: Nunca embutir credenciais no bundle |
| `.venv/` | Ambiente virtual de desenvolvimento |
| `.git/` | Histórico de versão |
| `build/` | Artefatos intermediários do PyInstaller |
| `artifacts/` | Logs de desenvolvimento |
| `tests/` | Suíte de testes |
| `scripts/` | Scripts de CI/análise |

### Onde o usuário coloca o `.env`

O `.env` deve ficar **no mesmo diretório** que o `RC-Gestor-Clientes-1.6.23.exe`.

Conteúdo mínimo do `.env`:
```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIs...
```

Variáveis opcionais:
```env
RC_LOG_LEVEL=INFO          # INFO (padrão), DEBUG para diagnóstico
RC_LOG_DIR=C:\custom\logs  # Sobrescreve local padrão dos logs
RC_NO_LOCAL_FS=1           # Cloud-only (padrão; 0 para modo local)
```

### Onde ficam os logs

| Modo | Localização |
|------|-------------|
| EXE (frozen) | `%LOCALAPPDATA%\RCGestor\logs\rcgestor.log` |
| Desenvolvimento | `artifacts/local/logs/rcgestor.log` |

Rotação: 10 MB max, 5 backups (`rcgestor.log.1` a `.5`).

### Checklist de teste em máquina limpa

```
□ 1. Copiar RC-Gestor-Clientes-1.6.23.exe para pasta de destino
□ 2. Copiar .env para a mesma pasta
□ 3. Executar o EXE (duplo-clique)
□ 4. Verificar:
     □ 4a. Splash aparece (480×320, logo RC, progress bar)
     □ 4b. Tela de login aparece após splash
     □ 4c. Login com credenciais válidas funciona
     □ 4d. Lista de clientes carrega
     □ 4e. Nenhuma pasta extra criada ao lado do EXE
□ 5. Verificar %LOCALAPPDATA%\RCGestor\logs\rcgestor.log existe
□ 6. Fechar o app (X ou Arquivo > Sair)
□ 7. Reabrir e verificar que sessão persiste
```

---

## 6. Validação Final

### 6.1 Rebuild
```
python -m PyInstaller rcgestor.spec --clean --noconfirm
→ Build complete! RC-Gestor-Clientes-1.6.23.exe (68.9 MB)
→ rc.png: OK (29150 bytes compressed)
→ rc.ico: OK (16503 bytes compressed)
```

### 6.2 EXE real
```
dist/RC-Gestor-Clientes-1.6.23.exe executado por 20s
→ Splash: exibido (logo + progress bar visíveis)
→ dist/artifacts: NÃO criada ✅
→ %LOCALAPPDATA%\RCGestor\logs\rcgestor.log: 7.8 KB ✅
→ Warnings de sites.png/chatgpt.png: ZERO no startup mais recente ✅
→ Warning de Supabase: presente (sem .env na pasta — esperado) ✅
```

### 6.3 Import smoke
```
python -c "import src.core.app; print('OK')"
→ OK ✅
```

### 6.4 Pytest
```
python -m pytest tests/ -x -q --tb=short
→ 1035 passed in 36.01s ✅
```

### 6.5 git diff (apenas esta fase)

| Arquivo | +/- | Mudança |
|---------|-----|---------|
| `rcgestor.spec` | +1 | `rc.png` adicionado ao bundle |
| `src/core/bootstrap.py` | +5 | `.env` ao lado do EXE em frozen |
| `src/core/logs/configure.py` | +6 | Logs → LocalAppData em frozen |
| `src/core/logs/logger.py` | +7 | Idem para `configure_file_logging` |
| `src/ui/components/topbar_nav.py` | 2 alteradas | `warning` → `debug` para ícones ausentes |
| `docs/VALIDACAO_PYINSTALLER_v1.6.23.md` | +1 | Documentar `rc.png` no bundle |

**Total: 5 arquivos de código, ~21 linhas adicionadas, 0 lógica de negócio tocada.**
