# Setup — RC Gestor de Clientes

Guia mínimo para configurar o ambiente de desenvolvimento.

## Pré-requisitos

| Requisito | Versão | Obrigatório? |
|-----------|--------|--------------|
| **Python** | 3.13.x | Sim |
| **pip** | 24+ (recomendado) | Sim |
| **Tesseract OCR** | 5.x | Não — OCR de PDFs escaneados. Sem ele, `pytesseract` falha silenciosamente. |
| **7-Zip CLI** (`7z`) | 21+ | Não — extração de `.rar` via `subprocess`. Sem ele, `.rar` não é suportado. |

> O Tesseract e o 7-Zip devem estar acessíveis no **PATH** do sistema.

## 1. Clonar e criar o venv

```powershell
git clone <repo-url> rcgestor
cd rcgestor
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 2. Instalar dependências

```powershell
pip install --upgrade pip
pip install -r requirements-dev.txt
```

`requirements-dev.txt` herda automaticamente todas as dependências de produção via `-r requirements.txt`.

## 3. Configurar variáveis de ambiente

```powershell
Copy-Item .env.example .env
```

Edite o `.env` e preencha pelo menos as variáveis **obrigatórias**:

| Variável | Descrição |
|----------|-----------|
| `SUPABASE_URL` | URL do projeto Supabase |
| `SUPABASE_ANON_KEY` | Chave anon (ou `SUPABASE_KEY`) |
| `AUTH_PEPPER` | Pepper para PBKDF2 (ou `RC_AUTH_PEPPER`) |

As demais variáveis possuem defaults seguros documentados no próprio `.env.example`.

## 4. Executar o aplicativo

```powershell
python main.py
```

## 5. Rodar os testes

```powershell
python -m pytest tests/ -q
```

Para cobertura:

```powershell
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Notas

- O arquivo autoritativo de dependências de produção é `requirements.txt`.
- `requirements.in` existe apenas como referência de deps diretas de alto nível.
- `pyproject.toml` declara metadados e configuração de ferramentas, **não** lista dependências.
- O `.venv` **não** é versionado — cada desenvolvedor cria o seu.
