"""Configuração de fixtures para testes do ClientesV2.

FASE 3.1: Setup de ambiente de testes com ttkbootstrap e CustomTkinter.
CORREÇÃO: Fixtures de session scope para evitar crash do ttkbootstrap Style singleton.
"""

import pytest


@pytest.fixture(scope="session")
def tk_root_session():
    """Cria um root Tk ÚNICO para toda a sessão de testes.

    Esta fixture resolve o problema de crash ao rodar múltiplos arquivos de teste,
    pois ttkbootstrap.Style() é um singleton e não pode ser recriado.

    Yields:
        tk.Tk: Root window compartilhado para todos os testes
    """
    # Criar root usando ttkbootstrap.Window para inicializar Style corretamente
    try:
        import ttkbootstrap as tb

        # Usar tb.Window que já inicializa o Style singleton
        root = tb.Window(themename="flatly")
        root.withdraw()  # Ocultar janela
    except Exception:
        # Fallback: tk.Tk padrão
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()

    yield root

    # Cleanup no final da sessão
    try:
        root.quit()
        root.destroy()
    except Exception:
        pass


@pytest.fixture(scope="function")
def tk_root(tk_root_session):
    """Fixture de função que usa o root da sessão.

    Cada teste recebe o mesmo root, mas pode criar seus próprios widgets filhos.
    O cleanup dos widgets filhos é feito automaticamente quando são destruídos.

    Yields:
        tk.Tk: Root window compartilhado
    """
    # Retornar o root da sessão
    yield tk_root_session

    # Cleanup de widgets filhos criados pelo teste
    try:
        for child in list(tk_root_session.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
    except Exception:
        pass


# Alias para manter compatibilidade com testes existentes que usam 'root'
@pytest.fixture(scope="function")
def root(tk_root):
    """Alias para tk_root mantendo compatibilidade."""
    return tk_root


@pytest.fixture(scope="function")
def clientes_v2_frame(tk_root):
    """Cria uma instância de ClientesV2Frame para testes.

    Args:
        tk_root: Fixture do root Tk

    Yields:
        ClientesV2Frame: Frame instanciado e pronto para testes
    """
    from src.modules.clientes_v2 import ClientesV2Frame

    # Criar frame (sem app para testes isolados)
    frame = ClientesV2Frame(tk_root, app=None)

    yield frame

    # Cleanup
    try:
        frame.destroy()
    except Exception:
        pass
