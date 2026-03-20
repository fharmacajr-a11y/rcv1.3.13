# RC – Gestor de Clientes

![Versão](https://img.shields.io/badge/versão-1.6.23-blue)
![Python](https://img.shields.io/badge/python-3.13-green)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-lightgrey)

Sistema desktop para gestão de clientes, documentos e senhas, voltado para escritórios de contabilidade, consultorias e farmácias que precisam gerenciar informações de múltiplos clientes de forma organizada e segura.

---

## 📋 Visão Geral

O **RC – Gestor de Clientes** é uma aplicação desktop desenvolvida em Python com interface gráfica moderna (Tkinter + CustomTkinter). O sistema oferece:

- **Gestão de Clientes**: Cadastro completo com CNPJ, razão social, contatos e observações
- **Módulo de Senhas**: Armazenamento seguro de credenciais por cliente e serviço
- **Auditoria de Documentos**: Upload e organização de arquivos por cliente (SIFAP, ANVISA, etc.)
- **Hub Central**: Visão unificada com notas e acesso rápido aos módulos
- **Lixeira**: Recuperação de clientes excluídos com exclusão cascata de senhas
- **Fluxo de Caixa**: Controle financeiro básico
- **Integração com IA**: Assistente ChatGPT para consultas rápidas

### Tecnologias Principais

| Componente | Tecnologia |
|------------|------------|
| Interface | Python 3.13, Tkinter, CustomTkinter |
| Backend | Supabase (PostgreSQL + Storage + Auth) |
| Build | PyInstaller, Inno Setup |
| Qualidade | pytest, ruff, pyright, bandit |

📖 **Documentação:**
- [**Setup para Desenvolvimento**](docs/SETUP.md)
- [**Guia de Contribuição**](CONTRIBUTING.md)
- [**Índice de Documentação**](docs/README.md)

---

## 💻 Requisitos

### Para Usuários (executável)
- Windows 10 ou superior (64-bit)
- 4GB RAM mínimo
- Conexão com internet (para sincronização com Supabase)

### Para Desenvolvedores
- Python 3.13.x
- pip (gerenciador de pacotes)
- Git
- Conta Supabase configurada (para backend)
- *(Opcional)* Tesseract OCR 5.x — para OCR de PDFs escaneados
- *(Opcional)* 7-Zip CLI — para extração de `.rar`

---

## 🚀 Instalação para Desenvolvimento

Consulte [docs/SETUP.md](docs/SETUP.md) para o guia completo. Resumo rápido:

```powershell
git clone <repo-url> rcgestor
cd rcgestor
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # editar com credenciais reais
python main.py
```

> ⚠️ **SEGURANÇA**: Nunca commite o `.env` com credenciais reais (já está no `.gitignore`).

---

## 📖 Uso Básico

### Tela Principal (Hub)

Ao abrir o aplicativo, você verá o Hub central com botões de acesso aos módulos:

1. **Clientes** – Cadastro e listagem de clientes
2. **Senhas** – Gerenciamento de credenciais por cliente
3. **Auditoria** – Upload de documentos organizados por cliente
4. **Fluxo de Caixa** – Controle financeiro
5. **Lixeira** – Clientes excluídos (com possibilidade de restauração)

### Módulo de Clientes

- Busca por nome, CNPJ ou telefone
- Filtro por status (Ativo, Inativo, etc.)
- Edição inline de campos
- Acesso rápido a senhas e documentos do cliente

### Módulo de Senhas

- Organização por cliente e serviço
- Filtros por serviço (SIFAP, ANVISA, e-CAC, etc.)
- Copiar senha com um clique
- Histórico de alterações

---

## 🧪 Rodando Testes

```powershell
# Suíte completa
python -m pytest tests/ -q

# Com cobertura
python -m pytest --cov=src --cov-report=term-missing -v
```

---

## 🏗️ Build do Executável

O projeto usa **PyInstaller** para gerar o executável e **Inno Setup** para criar o instalador.

### Gerar executável (PyInstaller)

```powershell
pyinstaller rcgestor.spec --clean
```

O executável será gerado em `dist/RC-Gestor-Clientes-{versão}.exe`.

### Gerar instalador (Inno Setup)

1. Abra o Inno Setup Compiler
2. Carregue o arquivo `installer/rcgestor.iss`
3. Compile (Ctrl+F9)
4. O instalador será gerado em `installer/Output/`

---

## 📁 Estrutura do Projeto

```
rcgestor/
├── main.py                 # Entrypoint (delega para src.core.app)
├── src/                    # Código-fonte principal
│   ├── version.py          # Versão do app
│   ├── core/               # Núcleo (app, auth, db, logs, bootstrap)
│   ├── modules/            # Módulos funcionais
│   │   ├── clientes/       # Gestão de clientes
│   │   ├── passwords/      # Gestão de senhas
│   │   ├── hub/            # Hub central
│   │   ├── lixeira/        # Lixeira
│   │   ├── uploads/        # Upload de documentos
│   │   ├── chatgpt/        # Integração OpenAI
│   │   └── ...
│   ├── ui/                 # Componentes de UI reutilizáveis
│   ├── infra/              # Infraestrutura (supabase, rede, binários)
│   └── adapters/           # Adaptadores de storage
├── tests/                  # Testes automatizados (1035+)
├── assets/                 # Imagens e ícones
├── docs/                   # Documentação
├── installer/              # Scripts do Inno Setup
├── rcgestor.spec           # Configuração PyInstaller
├── requirements.txt        # Dependências de produção
├── requirements-dev.txt    # Dependências de desenvolvimento
├── .env.example            # Template de variáveis de ambiente
└── README.md               # Este arquivo
```

---

## 📄 Licença

Copyright © 2025–2026 RC Apps. Todos os direitos reservados.

Este software é proprietário e seu uso é restrito conforme os termos acordados com RC Apps.

---

## 🔄 Changelog

Veja o histórico completo de alterações em [CHANGELOG.md](CHANGELOG.md).
