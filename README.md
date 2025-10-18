# RC-Gestor v1.0.34

Sistema de gestão de clientes com integração Supabase, interface gráfica em Python/tkinter e suporte a upload de documentos.

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.13+
- pip (gerenciador de pacotes)
- Git

### Instalação

```powershell
# 1. Clonar o repositório
git clone https://github.com/fharmacajr-a11y/rcv1.3.13.git
cd rcv1.3.13

# 2. Criar ambiente virtual
python -m venv .venv
.\.venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis de ambiente
# Copie o template e edite com suas credenciais:
copy ajuda\.env.example.template .env
# Edite .env com suas credenciais Supabase

# 5. Executar aplicação
python app_gui.py
```

---

## 📚 Documentação Completa

Toda a documentação detalhada está organizada na pasta [`ajuda/`](ajuda/):

- **[README_PROJETO.md](ajuda/README_PROJETO.md)** - Documentação completa do projeto
- **[SETUP_VENV_GUIA.md](ajuda/SETUP_VENV_GUIA.md)** - Guia detalhado de instalação
- **[CHANGELOG_HISTORICO.md](ajuda/CHANGELOG_HISTORICO.md)** - Histórico de mudanças
- **[INDICE.md](ajuda/INDICE.md)** - Índice de toda documentação

### Outros Recursos em `ajuda/`

- **Relatórios de auditoria:** análise de código, dependências, UTF-8
- **Ferramentas de desenvolvimento:** scripts de análise e manutenção
- **Configurações de CI/CD:** workflows e hooks

---

## 🏗️ Estrutura do Projeto

```
RC-Gestor/
├── app_gui.py              # 🚀 Entrypoint principal (GUI)
├── app_core.py             # ⚙️ Lógica core
├── app_status.py           # 📊 Monitor de status
├── app_utils.py            # 🛠️ Utilitários
├── config.yml              # ⚙️ Configuração da aplicação
├── .env                    # 🔐 Variáveis de ambiente (não versionado)
├── rc.ico                  # 🎨 Ícone da aplicação
│
├── application/            # 🎮 Controllers e casos de uso
├── gui/                    # 🖼️ Interface gráfica (tkinter)
├── ui/                     # 🎨 Componentes UI
├── core/                   # 💼 Lógica de negócio
├── infra/                  # 🔌 Integração Supabase
├── utils/                  # 🧰 Utilitários gerais
├── adapters/               # 🔄 Adaptadores de infraestrutura
├── shared/                 # 📦 Código compartilhado
├── config/                 # ⚙️ Configurações do sistema
├── detectors/              # 🔍 Detectores (CNPJ, etc.)
│
├── scripts/                # 📜 Scripts de manutenção
│   ├── make_runtime.py     # 📦 Gerador de runtime
│   ├── smoke_runtime.py    # 🧪 Testes de smoke
│   └── ...
│
└── ajuda/                  # 📚 Documentação e ferramentas
    ├── README_PROJETO.md   # 📖 Documentação completa
    ├── _ferramentas/       # 🛠️ Scripts de análise/dev
    └── _scripts_dev/       # 🔧 Scripts de desenvolvimento
```

---

## 🎯 Funcionalidades Principais

- ✅ **Gestão de Clientes** - CRUD completo com busca e filtros
- ✅ **Upload de Documentos** - Suporte a PDF, imagens e análise OCR
- ✅ **Integração Supabase** - Storage e banco de dados
- ✅ **Interface Gráfica** - Design moderno com ttkbootstrap
- ✅ **Logs de Auditoria** - Rastreamento de operações
- ✅ **Lixeira** - Recuperação de registros excluídos
- ✅ **Detecção de CNPJ** - Extração automática de documentos

---

## 🧪 Testes

```powershell
# Executar todos os testes
pytest

# Smoke test (verifica imports e dependências)
python scripts\smoke_runtime.py
```

---

## 📝 Changelog

Veja [ajuda/CHANGELOG_HISTORICO.md](ajuda/CHANGELOG_HISTORICO.md) para histórico completo de mudanças.

**Última versão:** v1.0.34 (18/10/2025)
- ✅ Padronização UTF-8 completa
- ✅ Ajustes finos de encoding
- ✅ Reorganização de documentação

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📄 Licença

Este projeto está sob licença privada. Todos os direitos reservados.

---

## 👥 Autores

- **Farmácia Jr. A11y** - Desenvolvimento e manutenção

---

## 🆘 Suporte

Para dúvidas, problemas ou sugestões:

1. Consulte a [documentação completa](ajuda/README_PROJETO.md)
2. Veja o [guia de setup](ajuda/SETUP_VENV_GUIA.md)
3. Abra uma issue no repositório

---

**Made with ❤️ by Farmácia Jr. A11y**
