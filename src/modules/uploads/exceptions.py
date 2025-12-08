"""Exceções específicas do módulo de Uploads.

FASE 7 - Exceções semânticas para erros de upload, permitindo
mensagens claras na UI sem expor detalhes técnicos.

Hierarquia:
    UploadError (base)
    ├── UploadValidationError (arquivo inválido antes do upload)
    ├── UploadNetworkError (falha de conexão/timeout)
    └── UploadServerError (5xx, servidor fora, RLS bloqueou)

Cada exceção carrega:
    - message: mensagem amigável para o usuário
    - detail: detalhes técnicos para log (opcional)

CONTRATO DE ERROS (Opção A - UP-01):
    A API de domínio (repository.py, upload_retry.py) expõe apenas exceções
    de domínio (UploadError e subclasses). Exceções brutas (RuntimeError,
    TypeError, etc.) são preservadas em __cause__ para debug/logging, mas
    não vazam diretamente para o chamador.

    Tratamento de HTTP 409 (duplicado): Classificado como UploadServerError
    via make_server_error("duplicate"), mas em upload_items_with_adapter
    é tratado como operação bem-sucedida (arquivo já existe = não é falha).
"""

from __future__ import annotations


class UploadError(Exception):
    """Exceção base para erros de upload.

    Atributos:
        message: Mensagem amigável para exibição na UI.
        detail: Detalhes técnicos para logging (não mostrar ao usuário).
    """

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or ""

    def __str__(self) -> str:
        return self.message


class UploadValidationError(UploadError):
    """Erro de validação do arquivo antes do upload.

    Exemplos:
        - Extensão não permitida
        - Arquivo muito grande
        - Arquivo corrompido/ilegível
    """

    pass


class UploadNetworkError(UploadError):
    """Erro de rede durante upload.

    Exemplos:
        - Timeout de conexão
        - ConnectionError
        - DNS não resolvido
    """

    pass


class UploadServerError(UploadError):
    """Erro do servidor durante upload.

    Exemplos:
        - HTTP 5xx
        - RLS bloqueou a operação
        - Bucket não encontrado
    """

    pass


# Mensagens padronizadas para UX consistente
ERROR_MESSAGES = {
    "extension": "Tipo de arquivo não permitido. Apenas arquivos PDF são aceitos.",
    "size": "O arquivo é muito grande. O tamanho máximo permitido é {max_mb} MB.",
    "empty": "O arquivo está vazio ou não pôde ser lido.",
    "not_found": "Arquivo não encontrado: {path}",
    "network": "Falha de conexão. Verifique sua internet e tente novamente.",
    "timeout": "A conexão demorou muito. Tente novamente em alguns instantes.",
    "server": "Erro temporário no servidor. Tente novamente em alguns minutos.",
    "permission": "Sem permissão para enviar arquivos. Contate o administrador.",
    "duplicate": "Este arquivo já existe no servidor.",
    "unknown": "Ocorreu um erro inesperado ao enviar o arquivo.",
}


def make_validation_error(
    error_type: str,
    **kwargs: str | int | float,
) -> UploadValidationError:
    """Cria UploadValidationError com mensagem padronizada.

    Args:
        error_type: Chave em ERROR_MESSAGES (extension, size, empty, not_found).
        **kwargs: Valores para interpolação na mensagem.

    Returns:
        UploadValidationError com mensagem formatada.
    """
    template = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"])
    message = template.format(**kwargs) if kwargs else template
    return UploadValidationError(message, detail=f"validation:{error_type}")


def make_network_error(
    error_type: str = "network",
    *,
    original: Exception | None = None,
) -> UploadNetworkError:
    """Cria UploadNetworkError com mensagem padronizada.

    Args:
        error_type: Chave em ERROR_MESSAGES (network, timeout).
        original: Exceção original para logging.

    Returns:
        UploadNetworkError com mensagem e detalhes técnicos.
    """
    message = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["network"])
    detail = f"{type(original).__name__}: {original}" if original else error_type
    return UploadNetworkError(message, detail=detail)


def make_server_error(
    error_type: str = "server",
    *,
    original: Exception | None = None,
    status_code: int | None = None,
) -> UploadServerError:
    """Cria UploadServerError com mensagem padronizada.

    Args:
        error_type: Chave em ERROR_MESSAGES (server, permission, duplicate).
        original: Exceção original para logging.
        status_code: Código HTTP se disponível.

    Returns:
        UploadServerError com mensagem e detalhes técnicos.
    """
    message = ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["server"])
    parts = [error_type]
    if status_code:
        parts.append(f"HTTP {status_code}")
    if original:
        parts.append(f"{type(original).__name__}: {original}")
    detail = " | ".join(parts)
    return UploadServerError(message, detail=detail)


__all__ = [
    "UploadError",
    "UploadValidationError",
    "UploadNetworkError",
    "UploadServerError",
    "ERROR_MESSAGES",
    "make_validation_error",
    "make_network_error",
    "make_server_error",
]
