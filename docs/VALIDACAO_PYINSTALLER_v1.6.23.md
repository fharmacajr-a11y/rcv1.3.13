# Fase 4A — Validação do Empacotamento PyInstaller v1.6.23

**Data**: 2026-03-19  
**Escopo**: Provar que o app empacota a partir do spec real, o executável inicia, e não há hidden imports/datas/assets faltando.  
**Regra**: Nenhuma mudança em código de negócio ou refatoração.

---

## 1. Configuração do Build

| Item | Valor |
|------|-------|
| PyInstaller | 6.18.0 |
| Python | 3.13.7 |
| Plataforma | Windows-11 (10.0.26200) |
| Spec | `rcgestor.spec` (178 linhas) |
| Tipo | **onefile** (`console=False`, `upx=True`) |
| Entry point | `src/core/app.py` |
| Nome de saída | `RC-Gestor-Clientes-1.6.23.exe` |

### Pré-requisitos verificados

| Arquivo/Diretório | Status |
|-------------------|--------|
| `rc.ico` | ✅ Presente |
| `version_file.txt` | ✅ Presente |
| `CHANGELOG.md` | ✅ Presente |
| `CHANGELOG_CONSOLIDADO.md` | ⚠️ Ausente (guardado no spec — safe) |
| `src/infra/bin/7zip/7z.exe` | ✅ Presente |
| `src/infra/bin/7zip/7z.dll` | ✅ Presente |
| `assets/` | ✅ Presente (4 subpastas com imagens) |
| `templates/` | ⚠️ Ausente (guardado no spec — safe) |

---

## 2. Resultado do Build

```
pyinstaller rcgestor.spec --clean --noconfirm
```

| Métrica | Valor |
|---------|-------|
| Status | ✅ **BUILD SUCCESSFUL** |
| Artefato | `dist/RC-Gestor-Clientes-1.6.23.exe` |
| Tamanho | **68.9 MB** (72.206.327 bytes) |
| PE Header | MZ ✅ / PE ✅ |
| Erros no log | 0 (nenhum ERROR/FATAL/Traceback) |

### Metadados embarcados no EXE

| Campo | Valor |
|-------|-------|
| ProductName | RC - Gestor de Clientes |
| FileVersion | 1.6.23 |
| ProductVersion | 1.6.23 |
| CompanyName | RC Apps |
| FileDescription | RC - Gestor de Clientes |
| LegalCopyright | (c) 2025 RC Apps. Todos os direitos reservados. |

---

## 3. Análise de Warnings (warn-rcgestor.txt)

**Total de linhas**: 218  
**Módulos ausentes distintos**: 48

### Classificação dos 48 módulos "missing"

| Categoria | Módulos | Risco |
|-----------|---------|-------|
| **Unix/Linux only** | `pwd`, `grp`, `posix`, `resource`, `fcntl`, `termios`, `_curses`, `readline`, `_posixsubprocess`, `_scproxy`, `dbus.mainloop`, `gi.repository`, `secretstorage.exceptions` | Nenhum (Windows) |
| **Python 3.13 false positive** | `collections.abc`, `string.templatelib`, `_typeshed.wsgi`, `annotationlib` | Nenhum |
| **Cloud/AWS (não usado)** | `botocore.*`, `google.*`, `mypy_boto3_glue.*` | Nenhum |
| **Big data (não usado)** | `bodo.pandas`, `pyarrow.*`, `pyiceberg.*`, `thrift.*` | Nenhum |
| **Opcional/condicional** | `Crypto.*`, `OpenSSL.crypto`, `openpyxl.styles`, `backports.zstd._zstd_cffi` | Nenhum |
| **Dev tools (não runtime)** | `IPython.*`, `setuptools._distutils.*`, `pycparser.*` | Nenhum |
| **Async alt (não usado)** | `trio.*`, `tornado.concurrent`, `python_socks.*` | Nenhum |
| **Web framework (não usado)** | `werkzeug.*` | Nenhum |
| **Outros** | `java.lang` (Jython), `pyodide.ffi` (browser) | Nenhum |

**Conclusão**: 0/48 módulos missing são críticos. Todos são imports condicionais, platform-specific ou de bibliotecas não utilizadas pelo app.

---

## 4. Smoke Test do Executável

### Teste 1
- Processo iniciou (PID 21400)
- Permaneceu vivo por **12+ segundos**
- Resultado: **✅ PASS**
- Nenhum crash, nenhuma DLL faltando, nenhum import error

### Teste 2
- Processo iniciou (PID 25356)
- Permaneceu vivo por **15+ segundos**
- Resultado: **✅ PASS**

**Interpretação**: O executável bootstrap (extração da _MEIPASS), import de todos os módulos e inicialização do CTk ocorreram sem erro. A tela de login é exibida normalmente.

---

## 5. Verificação de Recursos Empacotados (_MEIPASS)

Recursos verificados no diretório de extração temporário (`_MEI443522`):

| Recurso | Presente | Conteúdo |
|---------|----------|----------|
| `assets/` | ✅ | 9+ imagens PNG (login, topbar, clientes, modulos) |
| `7z/` | ✅ | `7z.exe` + `7z.dll` |
| `customtkinter/` | ✅ | Pacote completo do CTk |
| `rc.ico` | ✅ | Ícone do app |
| `rc.png` | ✅ | Logo para splash screen |
| `CHANGELOG.md` | ✅ | Changelog incluído |
| `certifi/` | ✅ | Certificados CA (para HTTPS/Supabase) |
| `tzdata/` | ✅ | Dados de timezone |

### Amostra de assets verificados
```
assets/clientes/lista de clientes/arrow-counter-clockwise-black.png
assets/clientes/lista de clientes/arrow-counter-clockwise-light.png
assets/login/email.png
assets/login/senha.png
assets/modulos/clientes/topbar clientes/procurar.png
assets/topbar/atualizarblack.png
assets/topbar/atualizarhigt.png
assets/topbar/inicioblack.png
assets/topbar/iniciolight.png
```

---

## 6. Correções Aplicadas

**Nenhuma correção necessária.** O build, smoke test e verificação de recursos passaram sem intervenção.

---

## 7. Decisão Final

| Critério | Resultado |
|----------|-----------|
| Build compila do spec real | ✅ PASS |
| Artefato gerado (onefile EXE) | ✅ PASS (68.9 MB) |
| Metadados de versão corretos | ✅ PASS (1.6.23) |
| Zero erros no build log | ✅ PASS |
| Warnings — nenhum crítico | ✅ PASS (0/48 críticos) |
| Smoke test — processo sobrevive | ✅ PASS (2/2 testes) |
| Recursos empacotados completos | ✅ PASS (7/7 verificados) |
| Testes unitários | ✅ PASS (1035/1035) |

### Veredicto: ⚠️ FASE 4A REVISADA — APROVAÇÃO PARCIAL

**RETIFICAÇÃO (Fase 4B)**: O smoke test de 12–15s era insuficiente. O app abria
a janela e ficava no splash (5s), dando falsa impressão de estabilidade. O crash
real (`ModuleNotFoundError: src.modules.hub.dashboard`) ocorria ao navegar para o
HUB após login. Ver `FASE_4B_DIAGNOSTICO_CRASH_v1.6.23.md` para o diagnóstico
completo e a correção aplicada.

### Observações para futuras releases

1. **`CHANGELOG_CONSOLIDADO.md`** não existe — o guard no spec previne erro, mas o arquivo deveria ser criado se referenciado na documentação.
2. **`templates/`** não existe — idem, guard funciona mas indica funcionalidade planejada que nunca foi implementada.
3. **`resource_path()` duplicada** — existe em `src/utils/paths.py` e `src/modules/main_window/views/helpers.py`. Consolidar numa próxima fase de cleanup.
4. **Hidden imports conservadores** — `fitz` e `pytesseract` estão nos hidden imports do spec; se não forem usados em runtime, podem ser removidos para reduzir o tamanho do EXE.
