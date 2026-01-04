# tests/test_infra_storage_client_fase36.py
"""
Testes para o módulo infra/supabase/storage_client.py (COV-INFRA-001).
Objetivo: Aumentar cobertura de ~14% para ≥ 50%.
"""

from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch
from requests import exceptions as req_exc

import pytest


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def mock_session():
    """Mock de sessão HTTP com get() configurável."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_response_zip():
    """Mock de response HTTP bem-sucedido com Content-Type ZIP."""
    response = MagicMock()
    response.status_code = 200

    # 3 chunks de 6 bytes cada = 18 bytes total
    chunks = [b"chunk1", b"chunk2", b"chunk3"]
    total_size = sum(len(c) for c in chunks)

    response.headers = {
        "Content-Type": "application/zip",
        "Content-Disposition": 'attachment; filename="pasta.zip"',
        "Content-Length": str(total_size),  # 18 bytes
    }
    response.iter_content = MagicMock(return_value=chunks)
    response.raw = MagicMock()
    response.raw.decode_content = True
    response.close = MagicMock()
    return response


@pytest.fixture
def mock_supabase_client():
    """Mock do cliente Supabase para testes de ensure_client_storage_prefix."""
    client = MagicMock()
    bucket_ref = MagicMock()
    bucket_ref.upload = MagicMock(return_value=MagicMock(data="uploaded"))

    # Mock do storage.from_(bucket_name)
    client.storage.from_ = MagicMock(return_value=bucket_ref)

    return client


# ========================================
# Testes de helpers internos
# ========================================


def test_downloads_dir_retorna_downloads_se_existir():
    """Testa que _downloads_dir retorna ~/Downloads se existir."""
    from src.infra.supabase.storage_client import _downloads_dir

    result = _downloads_dir()

    # Deve ser um Path válido
    assert isinstance(result, Path)
    # Deve existir (Downloads ou temp)
    assert result.exists()


def test_pick_name_from_cd_extrai_filename():
    """Testa extração de filename do Content-Disposition."""
    from src.infra.supabase.storage_client import _pick_name_from_cd

    cd = 'attachment; filename="documento.pdf"'
    result = _pick_name_from_cd(cd, "fallback.pdf")

    assert result == "documento.pdf"


def test_pick_name_from_cd_com_filename_utf8():
    """Testa extração de filename* UTF-8."""
    from src.infra.supabase.storage_client import _pick_name_from_cd

    cd = "attachment; filename*=UTF-8''relat%C3%B3rio.pdf"
    result = _pick_name_from_cd(cd, "fallback.pdf")

    assert result == "relatório.pdf"


def test_pick_name_from_cd_retorna_fallback_quando_vazio():
    """Testa que retorna fallback quando CD é vazio."""
    from src.infra.supabase.storage_client import _pick_name_from_cd

    result = _pick_name_from_cd("", "default.zip")

    assert result == "default.zip"


def test_pick_name_from_cd_retorna_fallback_quando_invalido():
    """Testa que retorna fallback quando CD não tem filename."""
    from src.infra.supabase.storage_client import _pick_name_from_cd

    result = _pick_name_from_cd("inline", "fallback.txt")

    assert result == "fallback.txt"


def test_slugify_converte_texto_para_slug():
    """Testa conversão de texto para slug."""
    from src.infra.supabase.storage_client import _slugify

    assert _slugify("Razão Social LTDA") == "razao-social-ltda"
    assert _slugify("Empresa & Cia.") == "empresa-cia"
    assert _slugify("  Multiple   Spaces  ") == "multiple-spaces"


def test_slugify_remove_acentos():
    """Testa remoção de acentos."""
    from src.infra.supabase.storage_client import _slugify

    assert _slugify("José & Irmãos") == "jose-irmaos"
    assert _slugify("Café Açúcar") == "cafe-acucar"


def test_slugify_com_string_vazia():
    """Testa slugify com string vazia."""
    from src.infra.supabase.storage_client import _slugify

    assert _slugify("") == ""
    assert _slugify("   ") == ""


# ========================================
# Testes de baixar_pasta_zip
# ========================================


def test_baixar_pasta_zip_sucesso(tmp_path, mock_response_zip):
    """Testa download bem-sucedido de pasta como ZIP."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    with (
        patch("src.infra.supabase.storage_client._sess") as mock_sess,
        patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
    ):
        mock_sess.return_value.get.return_value.__enter__.return_value = mock_response_zip

        result = baixar_pasta_zip(bucket="documentos", prefix="cliente123/docs", out_dir=str(tmp_path))

        assert result.exists()
        assert result.suffix == ".zip"
        assert result.parent == tmp_path


def test_baixar_pasta_zip_valida_parametros_obrigatorios():
    """Testa validação de parâmetros obrigatórios."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    with pytest.raises(ValueError, match="bucket é obrigatório"):
        baixar_pasta_zip(bucket="", prefix="pasta", out_dir="/tmp")

    with pytest.raises(ValueError, match="prefix é obrigatório"):
        baixar_pasta_zip(bucket="docs", prefix="", out_dir="/tmp")


def test_baixar_pasta_zip_http_error_levanta_runtime_error(tmp_path):
    """Testa que erro HTTP levanta RuntimeError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    error_response = MagicMock()
    error_response.status_code = 500
    error_response.json.return_value = {"error": "Internal Server Error"}
    error_response.__enter__ = MagicMock(return_value=error_response)
    error_response.__exit__ = MagicMock(return_value=False)

    with patch("src.infra.supabase.storage_client._sess") as mock_sess:
        mock_sess.return_value.get.return_value = error_response

        with pytest.raises(RuntimeError, match="Erro do servidor"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path))


def test_baixar_pasta_zip_content_type_errado_levanta_erro(tmp_path):
    """Testa que Content-Type não-ZIP levanta RuntimeError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    json_response = MagicMock()
    json_response.status_code = 200
    json_response.headers = {"Content-Type": "application/json"}
    json_response.json.return_value = {"error": "Arquivo não encontrado"}
    json_response.__enter__ = MagicMock(return_value=json_response)
    json_response.__exit__ = MagicMock(return_value=False)

    with patch("src.infra.supabase.storage_client._sess") as mock_sess:
        mock_sess.return_value.get.return_value = json_response

        with pytest.raises(RuntimeError, match="Resposta inesperada"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path))


def test_baixar_pasta_zip_timeout_levanta_timeout_error(tmp_path):
    """Testa que timeout levanta TimeoutError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    with patch("src.infra.supabase.storage_client._sess") as mock_sess:
        mock_sess.return_value.get.side_effect = req_exc.ReadTimeout("Timeout de leitura")

        with pytest.raises(TimeoutError, match="Tempo esgotado"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", timeout_s=10, out_dir=str(tmp_path))


def test_baixar_pasta_zip_connect_timeout_levanta_timeout_error(tmp_path):
    """Testa que connect timeout levanta TimeoutError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    with patch("src.infra.supabase.storage_client._sess") as mock_sess:
        mock_sess.return_value.get.side_effect = req_exc.ConnectTimeout("Timeout de conexão")

        with pytest.raises(TimeoutError, match="Tempo esgotado"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path))


def test_baixar_pasta_zip_request_exception_levanta_runtime_error(tmp_path):
    """Testa que RequestException genérica levanta RuntimeError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    with patch("src.infra.supabase.storage_client._sess") as mock_sess:
        mock_sess.return_value.get.side_effect = req_exc.RequestException("Erro de rede")

        with pytest.raises(RuntimeError, match="Falha de rede"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path))


def test_baixar_pasta_zip_cancelamento_via_event(tmp_path, mock_response_zip):
    """Testa cancelamento de download via threading.Event."""
    from src.infra.supabase.storage_client import baixar_pasta_zip, DownloadCancelledError

    cancel_event = threading.Event()
    cancel_event.set()  # Cancelar imediatamente

    with (
        patch("src.infra.supabase.storage_client._sess") as mock_sess,
        patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
    ):
        mock_sess.return_value.get.return_value.__enter__.return_value = mock_response_zip

        with pytest.raises(DownloadCancelledError, match="cancelada"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path), cancel_event=cancel_event)


def test_baixar_pasta_zip_progress_callback_e_chamado(tmp_path, mock_response_zip):
    """Testa que progress_cb é chamado durante download."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    progress_calls = []

    def progress_cb(chunk_size):
        progress_calls.append(chunk_size)

    with (
        patch("src.infra.supabase.storage_client._sess") as mock_sess,
        patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
    ):
        mock_sess.return_value.get.return_value.__enter__.return_value = mock_response_zip

        baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path), progress_cb=progress_cb)

        # Callback deve ter sido chamado para cada chunk
        assert len(progress_calls) == 3  # 3 chunks no mock
        assert sum(progress_calls) > 0


def test_baixar_pasta_zip_evita_sobrescrever_arquivo_existente(tmp_path, mock_response_zip):
    """Testa que arquivo existente recebe sufixo (1), (2), etc."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    # Criar arquivo que seria o primeiro resultado
    existing = tmp_path / "pasta.zip"
    existing.write_bytes(b"existing")

    with (
        patch("src.infra.supabase.storage_client._sess") as mock_sess,
        patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
    ):
        mock_sess.return_value.get.return_value.__enter__.return_value = mock_response_zip

        result = baixar_pasta_zip(bucket="docs", prefix="pasta", zip_name="pasta", out_dir=str(tmp_path))

        # Arquivo deve ter sufixo (1)
        assert result.name == "pasta (1).zip"


def test_baixar_pasta_zip_download_truncado_levanta_io_error(tmp_path):
    """Testa que download truncado levanta IOError."""
    from src.infra.supabase.storage_client import baixar_pasta_zip

    truncated_response = MagicMock()
    truncated_response.status_code = 200
    truncated_response.headers = {
        "Content-Type": "application/zip",
        "Content-Disposition": 'attachment; filename="pasta.zip"',
        "Content-Length": "9999",  # Espera 9999 bytes
    }
    truncated_response.iter_content = MagicMock(return_value=[b"small"])  # Retorna apenas 5 bytes
    truncated_response.raw = MagicMock()
    truncated_response.raw.decode_content = True
    truncated_response.__enter__ = MagicMock(return_value=truncated_response)
    truncated_response.__exit__ = MagicMock(return_value=False)

    with (
        patch("src.infra.supabase.storage_client._sess") as mock_sess,
        patch("src.infra.supabase.storage_client.CLOUD_ONLY", False),
    ):
        mock_sess.return_value.get.return_value = truncated_response

        with pytest.raises(IOError, match="Download truncado"):
            baixar_pasta_zip(bucket="docs", prefix="pasta", out_dir=str(tmp_path))


# ========================================
# Testes de build_client_prefix
# ========================================


def test_build_client_prefix_formato_correto():
    """Testa que build_client_prefix retorna formato {org_id}/{client_id}."""
    from src.infra.supabase.storage_client import build_client_prefix

    result = build_client_prefix(org_id="org-123", cnpj="12345678000190", razao_social="Empresa LTDA", client_id=456)

    assert result == "org-123/456"


def test_build_client_prefix_sem_client_id_levanta_erro():
    """Testa que client_id é obrigatório."""
    from src.infra.supabase.storage_client import build_client_prefix

    with pytest.raises(ValueError, match="client_id obrigatório"):
        build_client_prefix(org_id="org-123", cnpj="12345678000190", client_id=None)


def test_build_client_prefix_com_client_id_zero():
    """Testa que client_id=0 levanta erro (não é permitido)."""
    from src.infra.supabase.storage_client import build_client_prefix

    # client_id=0 é tratado como falsy, levanta ValueError
    with pytest.raises(ValueError, match="client_id obrigatório"):
        build_client_prefix(org_id="org-999", cnpj="00000000000000", client_id=0)


# ========================================
# Testes de ensure_client_storage_prefix
# ========================================


def test_ensure_client_storage_prefix_cria_placeholder(mock_supabase_client):
    """Testa criação de placeholder .keep no Storage."""
    from src.infra.supabase.storage_client import ensure_client_storage_prefix

    with patch("src.infra.supabase_client.supabase", mock_supabase_client):
        result = ensure_client_storage_prefix(
            bucket="documentos", org_id="org-123", cnpj="12345678000190", razao_social="Empresa", client_id=789
        )

        assert result == "org-123/789"

        # Verificar que upload foi chamado
        bucket_ref = mock_supabase_client.storage.from_.return_value
        bucket_ref.upload.assert_called_once()

        # Verificar que o caminho é correto
        call_args = bucket_ref.upload.call_args
        assert call_args[0][0] == "org-123/789/.keep"


def test_ensure_client_storage_prefix_upsert_como_string(mock_supabase_client):
    """Testa que upsert é passado como string "true"."""
    from src.infra.supabase.storage_client import ensure_client_storage_prefix

    with patch("src.infra.supabase_client.supabase", mock_supabase_client):
        ensure_client_storage_prefix(bucket="docs", org_id="org-1", cnpj="11111111111111", client_id=1)

        bucket_ref = mock_supabase_client.storage.from_.return_value
        call_args = bucket_ref.upload.call_args

        # Terceiro argumento deve ter upsert como string
        options = call_args[0][2]
        assert options["upsert"] == "true"
        assert isinstance(options["upsert"], str)


def test_ensure_client_storage_prefix_erro_levanta_exception(mock_supabase_client):
    """Testa que erro no upload levanta exceção."""
    from src.infra.supabase.storage_client import ensure_client_storage_prefix

    bucket_ref = mock_supabase_client.storage.from_.return_value
    bucket_ref.upload.side_effect = Exception("Erro no Storage")

    with patch("src.infra.supabase_client.supabase", mock_supabase_client):
        with pytest.raises(Exception, match="Erro no Storage"):
            ensure_client_storage_prefix(bucket="docs", org_id="org-1", cnpj="11111111111111", client_id=1)


def test_ensure_client_storage_prefix_limpa_arquivo_temporario(mock_supabase_client):
    """Testa que arquivo temporário é removido após upload."""
    from src.infra.supabase.storage_client import ensure_client_storage_prefix

    created_files = []

    original_mkstemp = tempfile.mkstemp

    def track_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        created_files.append(path)
        return fd, path

    with (
        patch("src.infra.supabase_client.supabase", mock_supabase_client),
        patch("tempfile.mkstemp", side_effect=track_mkstemp),
    ):
        ensure_client_storage_prefix(bucket="docs", org_id="org-1", cnpj="11111111111111", client_id=1)

        # Arquivo temporário deve ter sido criado
        assert len(created_files) == 1

        # E removido
        assert not os.path.exists(created_files[0])


# ========================================
# Testes de _sess (sessão reutilizável)
# ========================================


def test_sess_retorna_mesma_instancia():
    """Testa que _sess() retorna mesma instância (singleton)."""
    from src.infra.supabase.storage_client import _sess
    import src.infra.supabase.storage_client as storage_mod

    # Resetar global
    storage_mod._session = None

    with patch("src.infra.supabase.storage_client.make_session") as mock_make:
        mock_make.return_value = MagicMock()

        sess1 = _sess()
        sess2 = _sess()

        assert sess1 is sess2
        assert mock_make.call_count == 1


def test_downloadcancellederror_e_exception():
    """Testa que DownloadCancelledError pode ser levantada."""
    from src.infra.supabase.storage_client import DownloadCancelledError

    assert issubclass(DownloadCancelledError, Exception)

    with pytest.raises(DownloadCancelledError):
        raise DownloadCancelledError("Teste de cancelamento")
