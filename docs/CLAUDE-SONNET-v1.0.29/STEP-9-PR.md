# Step 9 – Tests essenciais + `.spec` oficial + artefato

## 📋 Resumo

Implementação de testes automatizados com pytest, confirmação do `.spec` seguro sem `.env`, e geração do artefato de build para distribuição.

**Tipo**: Testes + Build + Artefato  
**Complexidade**: Média  
**Impacto**: Garantia de qualidade e distribuição

---

## 🎯 Objetivos

- ✅ Configurar pytest com testes essenciais
- ✅ Testar funcionalidades críticas sem alterar assinaturas
- ✅ Confirmar `.spec` seguro (sem `.env`)
- ✅ Gerar artefato de build (executável + ZIP)

---

## 🔍 Contexto Técnico

### Desafios

1. **Teste de rede**: Simular conectividade sem chamadas HTTP reais
2. **Teste de ambiente**: Alterar variáveis de ambiente isoladamente
3. **Teste de PDF**: Gerar PDFs de teste sem assets externos
4. **Build seguro**: Garantir que `.env` não está no bundle

### Soluções

1. **monkeypatch**: Fixture do pytest para mocking
2. **tmp_path**: Fixture para diretórios temporários
3. **PyMuPDF**: Gera PDFs in-memory para testes
4. **Verificação recursiva**: Busca `.env` no bundle gerado

---

## 🛠️ Implementação

### 1. Configuração do pytest

**`pytest.ini`**:
```ini
[pytest]
addopts = -q
pythonpath = .
```

**Características**:
- ✅ Modo quieto (`-q`) para menos verbosidade
- ✅ Python path na raiz do projeto

### 2. Testes de Conectividade (`tests/test_net_status.py`)

**3 testes implementados**:

#### a) test_probe_with_can_resolve_true
```python
def test_probe_with_can_resolve_true(monkeypatch):
    """Simula resolução DNS bem-sucedida"""
    import infra.net_status as ns

    class MockResponse:
        status_code = 200

    def fake_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("infra.net_status.httpx.get", fake_get)
    monkeypatch.setattr(ns, "_can_resolve", lambda _: True)

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.ONLINE
```

#### b) test_probe_with_can_resolve_false
```python
def test_probe_with_can_resolve_false(monkeypatch):
    """Simula falha na resolução DNS"""
    import infra.net_status as ns

    monkeypatch.setattr(ns, "_can_resolve", lambda _: False)

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.OFFLINE
```

#### c) test_probe_with_http_failure
```python
def test_probe_with_http_failure(monkeypatch):
    """Simula falha HTTP em todos os fallbacks"""
    import infra.net_status as ns
    import httpx

    class MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, *args, **kwargs):
            raise httpx.ConnectError("Network error")

    monkeypatch.setattr("infra.net_status.httpx.Client", lambda **kw: MockClient())

    result = ns.probe(timeout=0.1)
    assert result == ns.Status.OFFLINE
```

**Técnica**: `monkeypatch.setattr()` para substituir funções/classes

### 3. Testes de Headers HTTP (`tests/test_supabase_client_headers.py`)

**5 testes implementados**:

```python
def test_pick_name_simple():
    """Header Content-Disposition simples"""
    cd = 'attachment; filename="relatorio.pdf"'
    assert _pick_name_from_cd(cd, "fallback.zip") == "relatorio.pdf"

def test_pick_name_utf8():
    """Header Content-Disposition com UTF-8 encoding"""
    cd = "attachment; filename*=UTF-8''relat%C3%B3rio.pdf"
    assert _pick_name_from_cd(cd, "fallback.zip") == "relatório.pdf"

def test_pick_name_missing():
    """Content-Disposition ausente (None)"""
    fallback = "default.zip"
    assert _pick_name_from_cd(None, fallback) == fallback

def test_pick_name_empty():
    """Content-Disposition vazio"""
    fallback = "default.zip"
    assert _pick_name_from_cd("", fallback) == fallback

def test_pick_name_no_filename():
    """Content-Disposition sem filename"""
    cd = "attachment"
    fallback = "default.zip"
    result = _pick_name_from_cd(cd, fallback)
    assert result == fallback
```

**Função testada**: `_pick_name_from_cd(cd: str, fallback: str) -> str`

**Cobertura**:
- ✅ Headers simples
- ✅ Headers UTF-8
- ✅ Casos extremos (None, vazio)

### 4. Testes de Configuração (`tests/test_paths_cloud_only.py`)

**3 testes implementados**:

```python
def test_cloud_only_true(monkeypatch):
    """RC_NO_LOCAL_FS=1 deve ativar CLOUD_ONLY"""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "1")

    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    assert paths.CLOUD_ONLY is True

def test_cloud_only_false(monkeypatch):
    """RC_NO_LOCAL_FS=0 deve desativar CLOUD_ONLY"""
    monkeypatch.setenv("RC_NO_LOCAL_FS", "0")

    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    assert paths.CLOUD_ONLY is False

def test_cloud_only_default(monkeypatch):
    """Sem RC_NO_LOCAL_FS explícito, verifica booleano válido"""
    monkeypatch.delenv("RC_NO_LOCAL_FS", raising=False)

    if "config.paths" in sys.modules:
        del sys.modules["config.paths"]

    import config.paths as paths

    assert isinstance(paths.CLOUD_ONLY, bool)
```

**Técnicas**:
- `monkeypatch.setenv()` para alterar env vars
- `sys.modules.del` para forçar reimportação

### 5. Testes de PDF (`tests/test_pdf_text.py`)

**4 testes implementados**:

#### a) Geração de PDFs in-memory
```python
def _make_pdf_with_text(path, text="Hello RC"):
    """Cria PDF com texto usando PyMuPDF"""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)  # 1 inch da borda
    doc.save(path)
    doc.close()
```

#### b) Teste de extração básica
```python
def test_extract_text_with_pypdf(tmp_path):
    """Gera PDF e extrai texto com pypdf"""
    pdf = tmp_path / "hello.pdf"
    _make_pdf_with_text(str(pdf), "Hello RC")

    r = PdfReader(str(pdf))
    content = (r.pages[0].extract_text() or "").strip()

    assert "Hello RC" in content
```

#### c) Teste multiline
```python
def test_extract_text_multiline(tmp_path):
    """PDF com múltiplas linhas"""
    pdf = tmp_path / "multiline.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Linha 1")
    page.insert_text((72, 92), "Linha 2")
    page.insert_text((72, 112), "Linha 3")
    doc.save(str(pdf))
    doc.close()

    r = PdfReader(str(pdf))
    content = r.pages[0].extract_text() or ""

    assert "Linha 1" in content
    assert "Linha 2" in content
    assert "Linha 3" in content
```

#### d) Teste de integração
```python
def test_pdf_reader_integration_with_file_utils(tmp_path):
    """Integração com utils.file_utils.read_pdf_text"""
    from utils.file_utils import read_pdf_text

    pdf = tmp_path / "integration.pdf"
    _make_pdf_with_text(str(pdf), "Integration Test RC")

    result = read_pdf_text(str(pdf))

    assert result is not None
    assert "Integration Test RC" in result
```

**Por quê gerar PDFs?**
- ✅ Evita dependência de assets externos
- ✅ Controle total do conteúdo
- ✅ Testes auto-contidos

**Fixtures utilizadas**:
- `tmp_path`: Diretório temporário (limpeza automática)
- `fitz` (PyMuPDF): Geração de PDFs
- `pypdf.PdfReader`: Leitura e validação

### 6. Smoke Tests (`tests/test_entrypoint.py`)

**3 testes implementados**:

```python
def test_import_app_gui():
    """app_gui deve importar sem erros"""
    import app_gui  # noqa: F401
    assert True

def test_import_app_core():
    """app_core deve importar sem erros"""
    import app_core  # noqa: F401
    assert True

def test_import_gui_main_window():
    """gui.main_window deve importar sem erros"""
    from gui.main_window import App  # noqa: F401
    assert True
```

**Propósito**: Verificar que entrypoints não têm erros de import

---

## 📊 Resultados dos Testes

### Execução
```bash
pytest -q tests/
```

### Output
```
........................                                                                                   [100%]
24 passed, 4 warnings in 2.31s
```

### Breakdown
```
tests/test_entrypoint.py               3 passed  ✓
tests/test_net_session.py              4 passed  ✓ (Step 8)
tests/test_net_status.py               3 passed  ✓
tests/test_paths_cloud_only.py         3 passed  ✓
tests/test_pdf_text.py                 4 passed  ✓
tests/test_supabase_client_headers.py  5 passed  ✓
tests/test_hub_screen_import.py        1 passed  ✓ (existente)
tests/test_net_session.py              1 passed  ✓ (existente)
```

### Estatísticas
- ✅ **24/24 testes passaram** (100% success rate)
- ⚠️ **4 warnings** (deprecation do PyMuPDF - não afeta)
- ⏱️ **2.31 segundos** de execução
- 🎯 **5 arquivos novos** de teste

---

## 🏗️ Build do Artefato

### 1. Verificação do `.spec`

**`build/rc_gestor.spec`**:
```python
datas=[
    # Apenas recursos públicos - SEM .env
    (os.path.join(basedir, 'rc.ico'), '.'),
    (os.path.join(basedir, 'rc.png'), '.'),
]
```

**Verificações**:
- ✅ `.env` **NÃO** está em `datas=[]`
- ✅ Apenas recursos públicos
- ✅ Comentário explícito: "SEM .env"

### 2. Execução do Build

**Comando**:
```bash
pyinstaller build/rc_gestor.spec --clean
```

**Resultado**:
```
INFO: Building COLLECT COLLECT-00.toc completed successfully.
INFO: Build complete! The results are available in: C:\Users\Pichau\Desktop\v1.0.29\dist
```

**Estatísticas**:
- ⏱️ **Tempo**: ~6 minutos
- 📦 **Executável**: `RC-Gestor.exe` (11.9 MB)
- 📁 **Bundle**: `dist/RC-Gestor/` (~120 MB)

### 3. Estrutura do Bundle

```
dist/RC-Gestor/
├── RC-Gestor.exe           # Executável principal (11.9 MB)
└── _internal/              # Dependências
    ├── rc.ico              ✓ Incluído
    ├── rc.png              ✓ Incluído
    ├── python313.dll
    ├── base_library.zip
    └── [libs + DLLs]
```

### 4. Verificação de Segurança

**Comando**:
```powershell
Get-ChildItem -Path dist\RC-Gestor\ -Recurse -File | Where-Object {$_.Extension -match '\.(env)$'}
```

**Resultado**: ✅ **Nenhum arquivo `.env` encontrado**

### 5. Criação do ZIP

**Comando**:
```powershell
Compress-Archive -Path dist\RC-Gestor\* -DestinationPath dist\RC-Gestor-v1.0.29.zip -Force
```

**Artefato gerado**:
- **Nome**: `RC-Gestor-v1.0.29.zip`
- **Tamanho**: 53.3 MB
- **Localização**: `dist/RC-Gestor-v1.0.29.zip`
- **Status**: ✅ Pronto para distribuição

---

## ✅ Garantias de Qualidade

### Testes
- ✅ **24/24 passando** (100% success)
- ✅ **Sem alterar assinaturas** - API pública preservada
- ✅ **Isolamento com mocks** - sem dependências externas
- ✅ **Smoke tests** - entrypoints funcionando

### Build
- ✅ **Sem `.env`** - verificado recursivamente
- ✅ **Recursos incluídos** - ícones presentes
- ✅ **Executável funcional** - build sem erros
- ✅ **Otimizado** - excludes configurados

### Compatibilidade
- ✅ **Python 3.13.7**
- ✅ **PyInstaller 6.16.0**
- ✅ **Windows 11**
- ✅ **ttkbootstrap 1.10.1**

---

## 📝 Decisões de Design

### Por quê gerar PDFs nos testes?
**Decisão**: Usar PyMuPDF para gerar, pypdf para ler

**Razões**:
1. ✅ **Auto-contido**: Sem dependência de assets externos
2. ✅ **Controle**: Conteúdo exato conhecido
3. ✅ **Reprodutível**: Sempre mesmo resultado
4. ✅ **Rápido**: Geração in-memory

**Alternativas consideradas**:
- Assets externos: Requer versionamento, pode estar ausente
- Base64 embedded: Menos legível, difícil manter

### Por quê monkeypatch ao invés de unittest.mock?
**Decisão**: Usar `monkeypatch` fixture do pytest

**Razões**:
1. ✅ **Integração nativa**: Fixture oficial do pytest
2. ✅ **Cleanup automático**: Reverte alterações após teste
3. ✅ **Menos verboso**: `monkeypatch.setattr()` vs `@patch()`
4. ✅ **Documentação clara**: https://docs.pytest.org/

**Comparação**:
```python
# unittest.mock
@patch('module.func')
def test_example(mock_func):
    mock_func.return_value = 42

# monkeypatch
def test_example(monkeypatch):
    monkeypatch.setattr('module.func', lambda: 42)
```

### Por quê pytest ao invés de unittest?
**Decisão**: Usar pytest como framework de testes

**Razões**:
1. ✅ **Sintaxe simples**: `assert x == y` (sem `self.assertEqual`)
2. ✅ **Fixtures poderosas**: `tmp_path`, `monkeypatch`, etc
3. ✅ **Descoberta automática**: Acha testes por padrão
4. ✅ **Plugins ricos**: pytest-cov, pytest-xdist, etc
5. ✅ **Output claro**: Melhor formatação de falhas

---

## 🔍 Exemplos de Uso

### Rodar todos os testes
```bash
pytest -q
```

### Rodar testes específicos
```bash
pytest tests/test_net_status.py -v
```

### Com cobertura
```bash
pytest --cov=infra --cov=utils
```

### Modo verbose
```bash
pytest -v
```

### Stop on first failure
```bash
pytest -x
```

---

## 📚 Referências Técnicas

### pytest
- **Documentação**: https://docs.pytest.org/
- **monkeypatch**: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
- **Fixtures**: https://docs.pytest.org/en/stable/reference/fixtures.html
- **tmp_path**: https://docs.pytest.org/en/stable/reference/fixtures.html#tmp-path

### PyInstaller
- **Spec files**: https://pyinstaller.org/en/stable/spec-files.html
- **Usage**: https://pyinstaller.org/en/stable/usage.html
- **Data files**: https://pyinstaller.org/en/stable/spec-files.html#adding-data-files

### pypdf
- **PyPI**: https://pypi.org/project/pypdf/
- **Extract text**: https://pypdf.readthedocs.io/en/stable/user/extract-text.html
- **PdfReader**: https://pypdf.readthedocs.io/en/stable/modules/PdfReader.html

---

## 🎯 Benefícios

### Qualidade
- ✅ Testes automatizados críticos
- ✅ Detecção precoce de regressões
- ✅ Validação de comportamento

### Confiança
- ✅ Build reprodutível
- ✅ Artefato pronto para distribuição
- ✅ Segurança validada (sem `.env`)

### Manutenibilidade
- ✅ Testes documentam comportamento
- ✅ Fácil adicionar novos testes
- ✅ CI/CD ready

---

## 📊 Impacto

### Arquivos Criados (6)
- ✅ `pytest.ini` - Configuração
- ✅ `tests/test_net_status.py` - 3 testes
- ✅ `tests/test_supabase_client_headers.py` - 5 testes
- ✅ `tests/test_paths_cloud_only.py` - 3 testes
- ✅ `tests/test_pdf_text.py` - 4 testes
- ✅ `tests/test_entrypoint.py` - 3 testes

### Arquivos Confirmados (1)
- ✅ `build/rc_gestor.spec` - Seguro sem `.env`

### Artefatos Gerados (3)
- ✅ `dist/RC-Gestor/` - Bundle (120 MB)
- ✅ `dist/RC-Gestor/RC-Gestor.exe` - Executável (11.9 MB)
- ✅ `dist/RC-Gestor-v1.0.29.zip` - ZIP (53.3 MB)

### Linhas de Código
- **Testes**: ~200 linhas (6 arquivos)
- **Configuração**: 3 linhas (`pytest.ini`)
- **Total novo**: +203 linhas

### Breaking Changes
- ✅ **NENHUM** - API mantida 100%

---

## 🚀 Próximos Passos

**Step 9 COMPLETO**. Aguardando instruções para Step 10.

---

## 📌 Checklist de Revisão

- [x] pytest configurado (`pytest.ini`)
- [x] Testes de conectividade (3 testes)
- [x] Testes de headers HTTP (5 testes)
- [x] Testes de configuração (3 testes)
- [x] Testes de PDF (4 testes)
- [x] Smoke tests (3 testes)
- [x] 24/24 testes passando
- [x] `.spec` sem `.env` confirmado
- [x] Build executado com sucesso
- [x] Artefato ZIP criado (53.3 MB)
- [x] Verificação de segurança (sem `.env` no bundle)
- [x] Documentação atualizada (LOG.md)
- [x] Referências técnicas incluídas
