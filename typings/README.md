# Type Stubs Directory

Este diretório contém **type stubs** locais (PEP 561-style) para bibliotecas que não fornecem stubs completos ou onde os stubs upstream estão incompletos.

## Estrutura

```
typings/
├── customtkinter/      # Stubs para customtkinter (Microfase 7)
├── tkinter/            # Stubs complementares para tkinter/ttk (CompatPack-15)
├── ttkbootstrap/       # Stubs para ttkbootstrap
├── openpyxl/           # Stubs para openpyxl
├── supabase/           # Stubs para supabase
└── postgrest/          # Stubs para postgrest
```

## Como Funciona

### Resolução de Imports pelo Pyright/Pylance

O Pyright resolve imports na seguinte ordem de prioridade:

1. **stubPath** (definido em `pyrightconfig.json` → `./typings`)
2. **extraPaths** (caminhos adicionais de código)
3. **venv/site-packages** (pacotes instalados)
4. **typeshed** (stubs bundled do Pyright)

Quando um import é encontrado, o Pyright procura primeiro por arquivos `.pyi` no `stubPath`.

### Por Que Stubs Locais?

- **Resolver reportMissingTypeStubs**: quando a biblioteca não fornece stubs oficiais
- **Complementar stubs incompletos**: adicionar métodos/atributos que faltam
- **Corrigir false positives**: quando o Pyright infere tipos incorretamente
- **Controle de versão**: manter stubs no repo para consistência entre devs

## Manutenção

### Adicionar Novo Widget/Método (customtkinter)

1. Abra [typings/customtkinter/__init__.pyi](customtkinter/__init__.pyi)
2. Adicione a classe ou método seguindo o padrão existente:

```python
class NovoWidget(CTkBaseClass):
    """Descrição breve."""
    def __init__(
        self,
        master: Misc | None = ...,
        # Parâmetros específicos
        **kwargs: Any,
    ) -> None: ...

    def pack(self, **kwargs: Any) -> None: ...
    def grid(self, **kwargs: Any) -> None: ...
    # Outros métodos usados no projeto
```

3. Não precisa ser perfeito: apenas o suficiente para eliminar os erros do Pylance
4. Salve e recarregue o VS Code (`Ctrl+Shift+P` → "Reload Window")

### Adicionar Método em Widget Existente

Se o Pylance reclamar de um método que existe mas não está no stub:

```python
class CTkButton(CTkBaseClass):
    # ... código existente ...

    def novo_metodo(self, param: str) -> None: ...  # Adicionar aqui
```

### Verificar se Stub Foi Carregado

1. Abra o arquivo Python que importa a biblioteca
2. Hover sobre o import: `import customtkinter as ctk`
3. Pylance deve mostrar: `(module) customtkinter` sem "Arquivo stub não encontrado"

## Referências

- [PEP 561 - Distributing and Packaging Type Information](https://peps.python.org/pep-0561/)
- [Pyright Configuration - stubPath](https://github.com/microsoft/pyright/blob/main/docs/configuration.md#stubPath)
- [Typing Best Practices](https://typing.readthedocs.io/en/latest/source/stubs.html)

## Histórico

- **2026-01-14**: Criados stubs para `customtkinter` (Microfase 7)
- **2025-11-13**: Criados stubs para `tkinter`, `ttk`, `ttkbootstrap` (CompatPack-15)
