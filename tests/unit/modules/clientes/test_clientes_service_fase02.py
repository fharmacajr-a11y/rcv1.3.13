"""
Coverage Pack 03 - Testes adicionais para src/modules/clientes/service.py.

Foco em:
- Branches de erro não cobertas
- Edge cases em funções críticas
- Validações de entrada
- Simulação de falhas de storage/database
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from src.modules.clientes.core.service import (
    mover_cliente_para_lixeira,
    restaurar_clientes_da_lixeira,
    excluir_cliente_simples,
    excluir_clientes_definitivamente,
    listar_clientes_na_lixeira,
    get_cliente_by_id,
    fetch_cliente_by_id,
    update_cliente_status_and_observacoes,
    checar_duplicatas_para_form,
    extrair_dados_cartao_cnpj_em_pasta,
    _current_utc_iso,
    _extract_cliente_id,
    _ensure_str,
    _resolve_current_id,
    _conflict_id,
    _filter_self,
    _build_conflict_ids,
    _resolve_current_org_id,
    _gather_paths,
    _remove_cliente_storage,
)


# ============================================================================
# Testes de funções auxiliares privadas
# ============================================================================


def test_current_utc_iso_retorna_string_iso():
    """Verifica que _current_utc_iso retorna timestamp ISO válido."""
    result = _current_utc_iso()
    assert isinstance(result, str)
    assert "T" in result  # formato ISO tem 'T' entre data e hora
    assert len(result) > 10  # deve ter mais que só a data


def test_extract_cliente_id_com_row_none():
    """_extract_cliente_id retorna None quando row é None."""
    assert _extract_cliente_id(None) is None


def test_extract_cliente_id_com_row_vazia():
    """_extract_cliente_id retorna None quando row é tupla vazia."""
    assert _extract_cliente_id(()) is None


def test_extract_cliente_id_com_row_valida():
    """_extract_cliente_id retorna primeiro elemento quando row tem dados."""
    assert _extract_cliente_id((42, "nome", "cnpj")) == 42


def test_ensure_str_converte_int():
    """_ensure_str retorna empty string para não-str."""
    assert _ensure_str(123) == ""


def test_ensure_str_mantem_string():
    """_ensure_str mantém string inalterada."""
    assert _ensure_str("teste") == "teste"


def test_ensure_str_com_none():
    """_ensure_str retorna empty string para None."""
    assert _ensure_str(None) == ""


def test_resolve_current_id_sem_exclude():
    """_resolve_current_id extrai id da row quando exclude_id é None."""
    row = (10, "nome")
    assert _resolve_current_id(row, None) == 10


def test_resolve_current_id_com_exclude_diferente():
    """_resolve_current_id retorna exclude_id quando fornecido."""
    row = (10, "nome")
    assert _resolve_current_id(row, 20) == 20


def test_resolve_current_id_com_exclude_igual():
    """_resolve_current_id retorna exclude_id mesmo se igual ao id da row."""
    row = (10, "nome")
    assert _resolve_current_id(row, 10) == 10


def test_conflict_id_com_dict_valido():
    """_conflict_id extrai 'id' de dict."""
    entry = {"id": 42, "nome": "teste"}
    assert _conflict_id(entry) == 42


def test_conflict_id_com_dict_sem_id():
    """_conflict_id retorna None se dict não tem 'id'."""
    entry = {"nome": "teste"}
    assert _conflict_id(entry) is None


def test_conflict_id_com_objeto_valido():
    """_conflict_id extrai atributo 'id' de objeto."""
    obj = Mock()
    obj.id = 99
    assert _conflict_id(obj) == 99


def test_conflict_id_com_objeto_sem_id():
    """_conflict_id retorna None se objeto não tem 'id'."""
    obj = Mock(spec=[])
    assert _conflict_id(obj) is None


def test_filter_self_remove_current_id():
    """_filter_self remove entradas com id igual a current_id."""
    entries = [{"id": 1}, {"id": 2}, {"id": 3}]
    result = _filter_self(entries, 2)
    assert len(result) == 2
    assert {"id": 2} not in result


def test_filter_self_current_id_none():
    """_filter_self retorna todas entradas quando current_id é None."""
    entries = [{"id": 1}, {"id": 2}]
    result = _filter_self(entries, None)
    assert len(result) == 2


def test_filter_self_entrada_sem_id():
    """_filter_self mantém entradas sem 'id'."""
    entries = [{"id": 1}, {"nome": "sem_id"}]
    result = _filter_self(entries, 1)
    assert len(result) == 1
    assert {"nome": "sem_id"} in result


def test_build_conflict_ids_sem_conflitos():
    """_build_conflict_ids retorna dict com listas vazias quando não há conflitos."""
    result = _build_conflict_ids(None, [], [])
    assert result == {"cnpj": [], "razao": [], "numero": []}


def test_build_conflict_ids_com_cnpj():
    """_build_conflict_ids adiciona 'cnpj' quando há conflito."""
    cnpj_conflict = {"id": 1}
    result = _build_conflict_ids(cnpj_conflict, [], [])
    assert result["cnpj"] == [1]
    assert result["razao"] == []
    assert result["numero"] == []


def test_build_conflict_ids_com_razao():
    """_build_conflict_ids adiciona 'razao' quando há conflitos."""
    razao_conflicts = [{"id": 2}, {"id": 3}]
    result = _build_conflict_ids(None, razao_conflicts, [])
    assert result["cnpj"] == []
    assert result["razao"] == [2, 3]
    assert result["numero"] == []


def test_build_conflict_ids_com_numero():
    """_build_conflict_ids adiciona 'numero' quando há conflitos."""
    numero_conflicts = [{"id": 4}]
    result = _build_conflict_ids(None, [], numero_conflicts)
    assert result["cnpj"] == []
    assert result["razao"] == []
    assert result["numero"] == [4]


def test_build_conflict_ids_combinado():
    """_build_conflict_ids combina múltiplos conflitos."""
    cnpj = {"id": 1}
    razao = [{"id": 2}]
    numero = [{"id": 3}]
    result = _build_conflict_ids(cnpj, razao, numero)
    assert result["cnpj"] == [1]
    assert result["razao"] == [2]
    assert result["numero"] == [3]


# ============================================================================
# Testes de extrair_dados_cartao_cnpj_em_pasta
# ============================================================================


def test_extrair_dados_cartao_cnpj_em_pasta_diretorio_inexistente(tmp_path):
    """Retorna dict com valores None quando diretório não existe."""
    fake_path = str(tmp_path / "inexistente")
    result = extrair_dados_cartao_cnpj_em_pasta(fake_path)
    assert result == {"cnpj": None, "razao_social": None}


def test_extrair_dados_cartao_cnpj_em_pasta_sem_arquivos_validos(tmp_path):
    """Retorna dict com valores None quando não há arquivos .pdf ou .png."""
    (tmp_path / "arquivo.txt").write_text("teste")
    result = extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))
    assert result == {"cnpj": None, "razao_social": None}


@patch("src.utils.file_utils.list_and_classify_pdfs")
def test_extrair_dados_cartao_cnpj_em_pasta_encontra_cnpj_card(mock_list, tmp_path):
    """Extrai dados quando encontra documento tipo cnpj_card."""
    mock_list.return_value = [
        {
            "type": "cnpj_card",
            "meta": {"cnpj": "12345678000190", "razao_social": "Empresa Teste LTDA"},
        }
    ]

    # Usa tmp_path que é um diretório real existente
    result = extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] == "12345678000190"
    assert result["razao_social"] == "Empresa Teste LTDA"


@patch("src.utils.text_utils.extract_company_fields")
@patch("src.utils.pdf_reader.read_pdf_text")
@patch("src.utils.file_utils.find_cartao_cnpj_pdf")
@patch("src.utils.file_utils.list_and_classify_pdfs")
def test_extrair_dados_cartao_cnpj_em_pasta_fallback_extrai_de_pdf(
    mock_list, mock_find, mock_read, mock_extract, tmp_path
):
    """Usa fallback para extrair dados de PDF quando não encontra via classify."""
    mock_list.return_value = []  # nada via classify
    mock_find.return_value = "/path/to/CNPJ_card.pdf"
    mock_read.return_value = "CNPJ: 11.222.333/0001-44\\nEmpresa XYZ LTDA"
    mock_extract.return_value = {"cnpj": "11222333000144", "razao_social": "Empresa XYZ LTDA"}

    # Usa tmp_path que é um diretório real existente
    result = extrair_dados_cartao_cnpj_em_pasta(str(tmp_path))

    assert result["cnpj"] == "11222333000144"
    assert result["razao_social"] == "Empresa XYZ LTDA"


# ============================================================================
# Testes de checar_duplicatas_para_form
# ============================================================================


@patch("src.modules.clientes.service.checar_duplicatas_info")
def test_checar_duplicatas_para_form_sem_conflitos(mock_duplicatas):
    """Retorna dict estruturado quando não há conflitos."""
    mock_duplicatas.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [],
        "numero_conflicts": [],
    }

    valores = {"Razao Social": "Empresa Teste"}
    result = checar_duplicatas_para_form(valores)

    assert result["cnpj_conflict"] is None
    assert result["razao_conflicts"] == []
    assert result["numero_conflicts"] == []
    assert result["blocking_fields"]["cnpj"] is False
    assert result["blocking_fields"]["razao"] is False


@patch("src.modules.clientes.service.checar_duplicatas_info")
def test_checar_duplicatas_para_form_com_conflito_cnpj(mock_duplicatas):
    """Retorna conflito CNPJ quando detectado."""
    mock_duplicatas.return_value = {
        "cnpj_conflict": {"id": 99, "razao_social": "Outro"},
        "razao_conflicts": [],
        "numero_conflicts": [],
    }

    valores = {"CNPJ": "12345678000190"}
    result = checar_duplicatas_para_form(valores)

    assert result["cnpj_conflict"] is not None
    assert result["blocking_fields"]["cnpj"] is True
    assert result["conflict_ids"]["cnpj"] == [99]


@patch("src.modules.clientes.service.checar_duplicatas_info")
def test_checar_duplicatas_para_form_com_conflito_razao(mock_duplicatas):
    """Retorna conflitos de razao quando detectados."""
    mock_duplicatas.return_value = {
        "cnpj_conflict": None,
        "razao_conflicts": [{"id": 10}, {"id": 11}],
        "numero_conflicts": [],
    }

    valores = {"Razao Social": "Empresa Teste"}
    result = checar_duplicatas_para_form(valores)

    assert result["blocking_fields"]["razao"] is True
    assert result["conflict_ids"]["razao"] == [10, 11]


# ============================================================================
# Testes de mover_cliente_para_lixeira
# ============================================================================


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_mover_cliente_para_lixeira_sucesso(mock_supabase, mock_exec):
    """Move cliente para lixeira atualizando deleted_at."""
    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query

    mover_cliente_para_lixeira(123)

    mock_supabase.table.assert_called_once_with("clients")
    mock_query.update.assert_called_once()
    mock_query.eq.assert_called_once_with("id", 123)
    mock_exec.assert_called_once()


@patch("src.modules.clientes.service.exec_postgrest")
def test_mover_cliente_para_lixeira_propaga_erro_postgrest(mock_exec):
    """Propaga exceção quando exec_postgrest falha."""
    mock_exec.side_effect = RuntimeError("Database error")

    with pytest.raises(RuntimeError, match="Database error"):
        mover_cliente_para_lixeira(456)


# ============================================================================
# Testes de restaurar_clientes_da_lixeira
# ============================================================================


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_restaurar_clientes_da_lixeira_lista_vazia(mock_supabase, mock_exec):
    """Não faz nada quando lista de IDs está vazia."""
    restaurar_clientes_da_lixeira([])

    mock_supabase.table.assert_not_called()
    mock_exec.assert_not_called()


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_restaurar_clientes_da_lixeira_sucesso(mock_supabase, mock_exec):
    """Restaura múltiplos clientes removendo deleted_at."""
    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.in_.return_value = mock_query

    restaurar_clientes_da_lixeira([10, 20, 30])

    mock_supabase.table.assert_called_once_with("clients")
    mock_query.update.assert_called_once()
    args = mock_query.in_.call_args[0]
    assert args[0] == "id"
    assert set(args[1]) == {10, 20, 30}
    mock_exec.assert_called_once()


# ============================================================================
# Testes de excluir_cliente_simples
# ============================================================================


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_excluir_cliente_simples_sucesso(mock_supabase, mock_exec):
    """Exclui cliente fisicamente do banco."""
    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.delete.return_value = mock_query
    mock_query.eq.return_value = mock_query

    excluir_cliente_simples(789)

    mock_supabase.table.assert_called_once_with("clients")
    mock_query.delete.assert_called_once()
    mock_query.eq.assert_called_once_with("id", 789)
    mock_exec.assert_called_once()


# ============================================================================
# Testes de listar_clientes_na_lixeira
# ============================================================================


@patch("src.modules.clientes.service._list_clientes_deletados_core")
def test_listar_clientes_na_lixeira_sucesso(mock_core):
    """Retorna lista de clientes deletados via core."""
    mock_core.return_value = [
        {"id": 1, "razao_social": "Cliente 1"},
        {"id": 2, "razao_social": "Cliente 2"},
    ]

    result = listar_clientes_na_lixeira()

    assert len(result) == 2
    assert result[0]["id"] == 1
    mock_core.assert_called_once_with(order_by="id", descending=True)


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
@patch("src.modules.clientes.service._list_clientes_deletados_core")
def test_listar_clientes_na_lixeira_fallback_quando_core_falha(mock_core, mock_supabase, mock_exec):
    """Usa fallback direto ao Supabase quando core levanta exceção."""
    mock_core.side_effect = RuntimeError("Core failure")

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.not_ = Mock()
    mock_query.not_.is_ = Mock(return_value=mock_query)
    mock_query.order.return_value = mock_query

    mock_resp = Mock()
    mock_resp.data = [{"id": 99, "razao_social": "Fallback"}]
    mock_exec.return_value = mock_resp

    result = listar_clientes_na_lixeira(order_by="razao_social", descending=False)

    assert len(result) == 1
    assert result[0]["id"] == 99
    mock_supabase.table.assert_called_once_with("clients")


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
@patch("src.modules.clientes.service._list_clientes_deletados_core")
def test_listar_clientes_na_lixeira_fallback_retorna_dict(mock_core, mock_supabase, mock_exec):
    """Fallback extrai 'data' de dict quando resp não tem atributo."""
    mock_core.side_effect = Exception("error")

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.not_ = Mock()
    mock_query.not_.is_ = Mock(return_value=mock_query)
    mock_query.order.return_value = mock_query

    mock_exec.return_value = {"data": [{"id": 88}]}

    result = listar_clientes_na_lixeira()

    assert len(result) == 1
    assert result[0]["id"] == 88


# ============================================================================
# Testes de get_cliente_by_id e fetch_cliente_by_id
# ============================================================================


@patch("src.modules.clientes.service.core_get_cliente_by_id")
def test_get_cliente_by_id_retorna_objeto(mock_core):
    """get_cliente_by_id retorna objeto do core."""
    mock_obj = Mock()
    mock_obj.id = 42
    mock_core.return_value = mock_obj

    result = get_cliente_by_id(42)

    assert result is mock_obj
    mock_core.assert_called_once_with(42)


@patch("src.modules.clientes.service.core_get_cliente_by_id")
def test_get_cliente_by_id_retorna_none(mock_core):
    """get_cliente_by_id retorna None quando não encontra."""
    mock_core.return_value = None

    result = get_cliente_by_id(999)

    assert result is None


@patch("src.modules.clientes.service.get_cliente_by_id")
def test_fetch_cliente_by_id_retorna_none(mock_get):
    """fetch_cliente_by_id retorna None quando cliente não existe."""
    mock_get.return_value = None

    result = fetch_cliente_by_id(123)

    assert result is None


@patch("src.modules.clientes.service.get_cliente_by_id")
def test_fetch_cliente_by_id_retorna_dict_direto(mock_get):
    """fetch_cliente_by_id retorna dict quando get_cliente retorna dict."""
    mock_get.return_value = {"id": 10, "razao_social": "Teste"}

    result = fetch_cliente_by_id(10)

    assert result == {"id": 10, "razao_social": "Teste"}


@patch("src.modules.clientes.service.get_cliente_by_id")
def test_fetch_cliente_by_id_converte_objeto_para_dict(mock_get):
    """fetch_cliente_by_id converte objeto em dict."""
    mock_obj = Mock()
    mock_obj.id = 15
    mock_obj.razao_social = "Empresa X"
    mock_obj.cnpj = "12345678000100"
    mock_obj.numero = "123"
    mock_obj.observacoes = "Obs teste"
    mock_get.return_value = mock_obj

    result = fetch_cliente_by_id(15)

    assert isinstance(result, dict)
    assert result["id"] == 15
    assert result["razao_social"] == "Empresa X"
    assert result["cnpj"] == "12345678000100"


# ============================================================================
# Testes de update_cliente_status_and_observacoes
# ============================================================================


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
@patch("src.modules.clientes.service.fetch_cliente_by_id")
def test_update_cliente_status_and_observacoes_com_int(mock_fetch, mock_supabase, mock_exec):
    """Aceita cliente_id como int."""
    mock_fetch.return_value = {"id": 50, "observacoes": "Texto antigo"}

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query

    update_cliente_status_and_observacoes(50, "NOVO_STATUS")

    mock_fetch.assert_called_once_with(50)
    mock_supabase.table.assert_called_once_with("clients")
    mock_query.update.assert_called_once()


@patch("src.modules.clientes.service.fetch_cliente_by_id")
def test_update_cliente_status_and_observacoes_cliente_sem_id(mock_fetch):
    """Levanta ValueError quando cliente não tem 'id'."""
    mock_fetch.return_value = None

    with pytest.raises(ValueError, match="id"):
        update_cliente_status_and_observacoes({"nome": "sem_id"}, "STATUS")


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_update_cliente_status_and_observacoes_com_dict(mock_supabase, mock_exec):
    """Aceita cliente como dict."""
    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.update.return_value = mock_query
    mock_query.eq.return_value = mock_query

    cliente = {"id": 60, "observacoes": "[STATUS_ANTIGO] Obs"}

    update_cliente_status_and_observacoes(cliente, "NOVO")

    mock_supabase.table.assert_called_once_with("clients")


# ============================================================================
# Testes de _resolve_current_org_id
# ============================================================================


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_resolve_current_org_id_sucesso(mock_supabase, mock_exec):
    """Resolve org_id corretamente."""
    mock_user = Mock()
    mock_user.id = "user-123"
    mock_resp_user = Mock()
    mock_resp_user.user = mock_user
    mock_supabase.auth.get_user.return_value = mock_resp_user

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_resp_org = Mock()
    mock_resp_org.data = [{"org_id": "org-456"}]
    mock_exec.return_value = mock_resp_org

    result = _resolve_current_org_id()

    assert result == "org-456"


@patch("src.modules.clientes.service.supabase")
def test_resolve_current_org_id_usuario_nao_autenticado(mock_supabase):
    """Levanta RuntimeError quando não há usuário autenticado."""
    mock_supabase.auth.get_user.return_value = None

    with pytest.raises(RuntimeError, match="Falha ao resolver"):
        _resolve_current_org_id()


@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_resolve_current_org_id_organizacao_nao_encontrada(mock_supabase, mock_exec):
    """Levanta RuntimeError quando não encontra org_id."""
    mock_user = Mock()
    mock_user.id = "user-999"
    mock_resp = Mock()
    mock_resp.user = mock_user
    mock_supabase.auth.get_user.return_value = mock_resp

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.select.return_value = mock_query
    mock_query.eq.return_value = mock_query
    mock_query.limit.return_value = mock_query

    mock_resp_org = Mock()
    mock_resp_org.data = []
    mock_exec.return_value = mock_resp_org

    with pytest.raises(RuntimeError, match="Organiza.*ǜo nǜo encontrada"):
        _resolve_current_org_id()


# ============================================================================
# Testes de _gather_paths e _remove_cliente_storage
# ============================================================================


@patch("src.modules.clientes.service.using_storage_backend")
@patch("src.modules.clientes.service.storage_list_files")
@patch("src.modules.clientes.service.SupabaseStorageAdapter")
def test_gather_paths_retorna_lista_vazia_quando_sem_items(mock_adapter, mock_list, mock_using):
    """_gather_paths retorna lista vazia quando não há arquivos."""
    mock_list.return_value = []

    result = _gather_paths("bucket", "prefix")

    assert result == []


@patch("src.modules.clientes.service.using_storage_backend")
@patch("src.modules.clientes.service.storage_list_files")
@patch("src.modules.clientes.service.SupabaseStorageAdapter")
def test_gather_paths_ignora_items_sem_name(mock_adapter, mock_list, mock_using):
    """_gather_paths ignora items sem campo 'name'."""
    mock_list.return_value = [{"metadata": {}}]

    result = _gather_paths("bucket", "prefix")

    assert result == []


@patch("src.modules.clientes.service.using_storage_backend")
@patch("src.modules.clientes.service.storage_list_files")
@patch("src.modules.clientes.service.SupabaseStorageAdapter")
def test_gather_paths_adiciona_arquivos_com_metadata(mock_adapter, mock_list, mock_using):
    """_gather_paths adiciona paths de arquivos (com metadata)."""
    mock_list.return_value = [{"name": "file1.pdf", "metadata": {"size": 1024}}]

    result = _gather_paths("bucket", "prefix")

    assert len(result) == 1
    assert "prefix/file1.pdf" in result


@patch("src.modules.clientes.service.using_storage_backend")
@patch("src.modules.clientes.service.storage_list_files")
@patch("src.modules.clientes.service.SupabaseStorageAdapter")
def test_gather_paths_trata_excecao_list_files(mock_adapter, mock_list, mock_using):
    """_gather_paths continua quando list_files levanta exceção."""
    mock_list.side_effect = RuntimeError("Storage error")

    result = _gather_paths("bucket", "prefix")

    assert result == []


@patch("src.modules.clientes.service._gather_paths")
@patch("src.modules.clientes.service.storage_delete_file")
def test_remove_cliente_storage_sucesso(mock_delete, mock_gather):
    """_remove_cliente_storage remove arquivos com sucesso."""
    mock_gather.return_value = ["org/123/file1.pdf", "org/123/file2.pdf"]
    mock_delete.return_value = True

    errs = []
    _remove_cliente_storage("bucket", "org", 123, errs)

    assert len(errs) == 0
    assert mock_delete.call_count == 2


@patch("src.modules.clientes.service._gather_paths")
@patch("src.modules.clientes.service.storage_delete_file")
def test_remove_cliente_storage_falha_delete(mock_delete, mock_gather):
    """_remove_cliente_storage adiciona erro quando delete_file falha."""
    mock_gather.return_value = ["org/123/file1.pdf"]
    mock_delete.side_effect = RuntimeError("Delete failed")

    errs = []
    _remove_cliente_storage("bucket", "org", 123, errs)

    assert len(errs) == 1
    assert errs[0][0] == 123
    assert "Delete failed" in errs[0][1]


@patch("src.modules.clientes.service._gather_paths")
def test_remove_cliente_storage_falha_gather(mock_gather):
    """_remove_cliente_storage adiciona erro quando _gather_paths falha."""
    mock_gather.side_effect = RuntimeError("Gather failed")

    errs = []
    _remove_cliente_storage("bucket", "org", 456, errs)

    assert len(errs) == 1
    assert errs[0][0] == 456
    assert "Gather failed" in errs[0][1]


# ============================================================================
# Testes de excluir_clientes_definitivamente
# ============================================================================


@patch("src.modules.clientes.service._remove_cliente_storage")
@patch("src.modules.clientes.service._resolve_current_org_id")
@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_excluir_clientes_definitivamente_lista_vazia(mock_supabase, mock_exec, mock_org, mock_remove):
    """Retorna (0, []) quando lista de IDs está vazia."""
    ok, errs = excluir_clientes_definitivamente([])

    assert ok == 0
    assert errs == []
    mock_supabase.table.assert_not_called()


@patch("src.modules.clientes.service._remove_cliente_storage")
@patch("src.modules.clientes.service._resolve_current_org_id")
@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_excluir_clientes_definitivamente_sucesso(mock_supabase, mock_exec, mock_org, mock_remove):
    """Exclui clientes e storage com sucesso."""
    mock_org.return_value = "org-123"

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.delete.return_value = mock_query
    mock_query.in_.return_value = mock_query

    def fake_remove(bucket, org, cid, errs):
        pass  # sucesso sem erros

    mock_remove.side_effect = fake_remove

    ok, errs = excluir_clientes_definitivamente([10, 20])

    assert ok == 2
    assert errs == []
    assert mock_remove.call_count == 2


@patch("src.modules.clientes.service._remove_cliente_storage")
@patch("src.modules.clientes.service._resolve_current_org_id")
@patch("src.modules.clientes.service.exec_postgrest")
@patch("src.modules.clientes.service.supabase")
def test_excluir_clientes_definitivamente_com_callback(mock_supabase, mock_exec, mock_org, mock_remove):
    """Chama progress_cb durante exclusão."""
    mock_org.return_value = "org-123"

    mock_query = Mock()
    mock_supabase.table.return_value = mock_query
    mock_query.delete.return_value = mock_query
    mock_query.in_.return_value = mock_query

    progress_calls = []

    def progress_cb(current, total, cid):
        progress_calls.append((current, total, cid))

    def fake_remove(bucket, org, cid, errs):
        pass

    mock_remove.side_effect = fake_remove

    excluir_clientes_definitivamente([1, 2, 3], progress_cb=progress_cb)

    assert len(progress_calls) == 3
    assert progress_calls[0] == (1, 3, 1)
    assert progress_calls[-1] == (3, 3, 3)


@patch("src.modules.clientes.service._remove_cliente_storage")
@patch("src.modules.clientes.service._resolve_current_org_id")
def test_excluir_clientes_definitivamente_falha_resolve_org(mock_org, mock_remove):
    """Adiciona erro quando _resolve_current_org_id falha."""
    mock_org.side_effect = RuntimeError("Auth failed")

    ok, errs = excluir_clientes_definitivamente([99])

    assert ok == 0
    assert len(errs) == 1
    assert errs[0][0] == 0  # cliente_id=0 indica erro global
    assert "Auth failed" in errs[0][1]
