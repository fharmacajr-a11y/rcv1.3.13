# RC – Gestor de Clientes

![Versão](https://img.shields.io/badge/versão-1.4.52-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![Plataforma](https://img.shields.io/badge/plataforma-Windows-lightgrey)

Sistema desktop para gestão de clientes, documentos e senhas, voltado para escritórios de contabilidade, consultorias e farmácias que precisam gerenciar informações de múltiplos clientes de forma organizada e segura.

---

## 📋 Visão Geral

O **RC – Gestor de Clientes** é uma aplicação desktop desenvolvida em Python com interface gráfica moderna (Tkinter + ttkbootstrap). O sistema oferece:

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
| Interface | Python 3.10+, Tkinter, ttkbootstrap |
| Backend | Supabase (PostgreSQL + Storage + Auth) |
| Build | PyInstaller, Inno Setup |
| Qualidade | pytest, ruff, pyright, bandit |

📖 **Documentação Adicional:**
- [Modelo de Segurança - Criptografia e Gestão de Chaves](docs/SECURITY_MODEL.md)

---

## 💻 Requisitos

### Para Usuários (executável)
- Windows 10 ou superior (64-bit)
- 4GB RAM mínimo
- Conexão com internet (para sincronização com Supabase)

### Para Desenvolvedores
- Python 3.10 ou superior
- pip (gerenciador de pacotes)
- Git
- Conta Supabase configurada (para backend)

---

## 🚀 Instalação para Desenvolvimento

### 1. Clonar o repositório

```bash
git clone https://github.com/fharmacajr-a11y/rcv1.3.13.git
cd rcv1.3.13
```

### 2. Criar e ativar ambiente virtual

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Windows (CMD)
python -m venv .venv
.venv\Scripts\activate.bat

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
# Dependências de produção
pip install -r requirements.txt

# Dependências de desenvolvimento (inclui pytest, ruff, etc.)
pip install -r requirements-dev.txt
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto com as credenciais do Supabase:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon
RC_STORAGE_BUCKET_CLIENTS=rc-docs
RC_CLIENT_SECRET_KEY=<gere-uma-chave-fernet-unica>
```

> ⚠️ **IMPORTANTE - SEGURANÇA**:
> - Nunca commite o arquivo `.env` com credenciais reais (já está no `.gitignore`)
> - O `.env` é usado APENAS em desenvolvimento local
> - O build PyInstaller **NÃO inclui** o `.env` (corrigido em P0-002)
> - Para produção, configure variáveis de ambiente no sistema operacional
> - Para chave OpenAI (módulo ChatGPT), use `OPENAI_API_KEY` via variável de ambiente (veja `config/README.md`)

### 5. Executar o aplicativo

```bash
python -m src.app_gui
```

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

### Testes por módulo (recomendado)

```bash
# Testes do módulo clientes
pytest tests/modules/clientes --no-cov -q

# Testes do módulo passwords
pytest tests/modules/passwords --no-cov -q

# Testes do módulo auditoria
pytest tests/modules/auditoria --no-cov -q

# Testes do módulo hub
pytest tests/modules/hub --no-cov -q
```

### Suíte completa (pode ser demorada)

```bash
pytest tests/ --maxfail=3 -q
```

### Verificação de qualidade de código

```bash
# Lint com ruff
ruff check src/

# Verificação de tipos com pyright
pyright src/

# Análise de segurança com bandit
bandit --ini .bandit -r src adapters infra helpers
```

---

## 🏗️ Build do Executável

O projeto usa **PyInstaller** para gerar o executável e **Inno Setup** para criar o instalador.

### Gerar executável (PyInstaller)

```bash
pyinstaller rcgestor.spec
```

O executável será gerado em `dist/RC-Gestor-Clientes-1.4.52.exe`.

### Gerar instalador (Inno Setup)

1. Abra o Inno Setup Compiler
2. Carregue o arquivo `installer/rcgestor.iss`
3. Compile (Ctrl+F9)
4. O instalador será gerado em `installer/Output/`

> 📚 Para instruções detalhadas, consulte [docs/BUILD.md](docs/BUILD.md).

---

## 📁 Estrutura do Projeto

```
rcv1.3.13/
├── src/                    # Código-fonte principal
│   ├── app_gui.py          # Entrypoint da aplicação
│   ├── version.py          # Versão do app
│   ├── core/               # Núcleo (auth, db, utils)
│   ├── modules/            # Módulos funcionais
│   │   ├── clientes/       # Gestão de clientes
│   │   ├── passwords/      # Gestão de senhas
│   │   ├── auditoria/      # Auditoria de documentos
│   │   ├── hub/            # Hub central
│   │   ├── lixeira/        # Lixeira
│   │   └── ...
│   └── ui/                 # Componentes de UI reutilizáveis
├── tests/                  # Testes automatizados
├── assets/                 # Imagens e ícones
├── docs/                   # Documentação
├── installer/              # Scripts do Inno Setup
├── rcgestor.spec           # Configuração PyInstaller
├── requirements.txt        # Dependências de produção
├── requirements-dev.txt    # Dependências de desenvolvimento
└── README.md               # Este arquivo
```

---

## 📄 Licença

Copyright © 2025 RC Apps. Todos os direitos reservados.

Este software é proprietário e seu uso é restrito conforme os termos acordados com RC Apps.

---

## 📞 Contato e Suporte

- **Issues**: [GitHub Issues](https://github.com/fharmacajr-a11y/rcv1.3.13/issues)
- **E-mail**: suporte@rcapps.com.br

### Reportando Bugs

Ao reportar um bug, inclua:
1. Versão do aplicativo (visível no rodapé da janela principal)
2. Sistema operacional
3. Passos para reproduzir o problema
4. Mensagens de erro (se houver)
5. Screenshots (se aplicável)

---

## 🔄 Changelog

Veja o histórico completo de alterações em [CHANGELOG.md](CHANGELOG.md).

### Última versão: v1.4.52 (2025-12-17)

- Bump de versão para 1.4.52
- Correção de dependência: pluggy (era plugggy)
- Limpeza de artefatos e varredura de qualidade
- Confirmação do módulo ANVISA funcional

### Versão anterior: v1.4.26 (2025-12-11)

- Correção do Hub: Dashboard e Notas agora sempre mostram conteúdo (loading/erro/dados/vazio)
- Melhoria de UX: mensagens amigáveis em caso de erro ou ausencia de dados
- Tratamento robusto de estados de carregamento e autenticação

### Versão anterior: v1.3.92 (2025-12-07)

- Correção de cores dos botões no Hub
- Reordenação de botões (Clientes → Senhas → Auditoria)
- Filtro de serviço somente leitura no módulo Senhas
- Exclusão cascata de senhas ao excluir cliente da Lixeira
- Melhorias de UX no client picker (carregamento assíncrono)
