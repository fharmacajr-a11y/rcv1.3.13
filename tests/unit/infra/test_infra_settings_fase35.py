# tests/test_infra_settings_fase35.py
"""
Testes para o módulo infra/settings.py (COV-INFRA-001).
Objetivo: Aumentar cobertura para 100%.

Histórico:
- Fase 35: Cobertura inicial ~0% → 97.3%
- Atual: 97.3% → 100% (cobrindo linhas 93-94: cache update e error handling)
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def temp_settings_file(tmp_path):
    """Cria um arquivo settings.json temporário para testes."""
    settings_file = tmp_path / "settings.json"
    return settings_file


@pytest.fixture
def mock_cloud_only_false(monkeypatch):
    """Mock de CLOUD_ONLY = False (modo normal, persiste em disco)."""
    monkeypatch.setattr("src.infra.settings.CLOUD_ONLY", False)


@pytest.fixture
def mock_cloud_only_true(monkeypatch):
    """Mock de CLOUD_ONLY = True (modo memória, não persiste)."""
    monkeypatch.setattr("src.infra.settings.CLOUD_ONLY", True)


@pytest.fixture
def clear_settings_cache():
    """Limpa cache global antes de cada teste."""
    import src.infra.settings as settings_mod

    settings_mod._CACHE = None
    settings_mod._MEMORY_STORE.clear()
    yield
    settings_mod._CACHE = None
    settings_mod._MEMORY_STORE.clear()


# ========================================
# Testes de get_value
# ========================================


def test_get_value_retorna_default_quando_arquivo_nao_existe(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value retorna default quando settings.json não existe."""
    from src.infra import settings

    # Garantir que arquivo não existe
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)
    assert not temp_settings_file.exists()

    result = settings.get_value("window_width", default=800)

    assert result == 800


def test_get_value_le_valor_do_arquivo_json(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value lê corretamente valores do settings.json."""
    from src.infra import settings

    # Criar arquivo com dados
    data = {"window_width": 1024, "window_height": 768}
    temp_settings_file.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    result = settings.get_value("window_width")

    assert result == 1024


def test_get_value_retorna_default_para_chave_inexistente(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value retorna default para chave que não existe no arquivo."""
    from src.infra import settings

    data = {"outro_campo": "valor"}
    temp_settings_file.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    result = settings.get_value("campo_inexistente", default="padrao")

    assert result == "padrao"


def test_get_value_retorna_none_por_default_quando_nao_especificado(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value retorna None quando default não é fornecido."""
    from src.infra import settings

    temp_settings_file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    result = settings.get_value("chave_qualquer")

    assert result is None


def test_get_value_com_arquivo_json_invalido_retorna_default(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value retorna default quando JSON é inválido."""
    from src.infra import settings

    # Escrever JSON inválido
    temp_settings_file.write_text("{ isso não é json válido }", encoding="utf-8")
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    result = settings.get_value("qualquer", default="fallback")

    assert result == "fallback"


def test_get_value_com_arquivo_json_nao_dict_retorna_default(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que get_value retorna default quando JSON não é um dict."""
    from src.infra import settings

    # JSON válido mas não é dict
    temp_settings_file.write_text("[1, 2, 3]", encoding="utf-8")
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    result = settings.get_value("campo", default=999)

    assert result == 999


# ========================================
# Testes de set_value
# ========================================


def test_set_value_persiste_em_disco(temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch):
    """Testa que set_value persiste valor em disco (modo não-cloud)."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("tema", "dark")

    # Ler arquivo diretamente
    assert temp_settings_file.exists()
    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data["tema"] == "dark"


def test_set_value_sobrescreve_valor_existente(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que set_value sobrescreve valor existente."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("contador", 10)
    settings.set_value("contador", 20)

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data["contador"] == 20


def test_set_value_com_none_remove_chave(temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch):
    """Testa que set_value(key, None) remove a chave."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("temporario", "valor")
    settings.set_value("temporario", None)

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert "temporario" not in data


def test_set_value_cria_diretorio_se_nao_existir(tmp_path, mock_cloud_only_false, clear_settings_cache, monkeypatch):
    """Testa que set_value cria diretório pai se não existir."""
    from src.infra import settings

    nested_file = tmp_path / "subdir" / "deep" / "settings.json"
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", nested_file)

    settings.set_value("chave", "valor")

    assert nested_file.exists()
    assert nested_file.parent.exists()


def test_set_value_em_modo_cloud_only_usa_memoria(
    temp_settings_file, mock_cloud_only_true, clear_settings_cache, monkeypatch
):
    """Testa que set_value em CLOUD_ONLY=True não persiste em disco."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("memoria_key", "memoria_valor")

    # Arquivo não deve ser criado
    assert not temp_settings_file.exists()

    # Mas valor deve estar disponível via get_value
    assert settings.get_value("memoria_key") == "memoria_valor"


# ========================================
# Testes de update_values
# ========================================


def test_update_values_atualiza_multiplos_campos(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que update_values atualiza múltiplos campos de uma vez."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.update_values({"campo1": "valor1", "campo2": 123, "campo3": True})

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data["campo1"] == "valor1"
    assert data["campo2"] == 123
    assert data["campo3"] is True


def test_update_values_preserva_campos_existentes(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que update_values preserva campos não atualizados."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("existente", "original")
    settings.update_values({"novo": "adicionado"})

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data["existente"] == "original"
    assert data["novo"] == "adicionado"


def test_update_values_com_dict_vazio_nao_altera_nada(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que update_values({}) não altera arquivo."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("original", "valor")
    settings.update_values({})

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data == {"original": "valor"}


def test_update_values_com_parametro_nao_dict_nao_faz_nada(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que update_values com não-dict é ignorado."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("original", "valor")
    settings.update_values("string_invalida")  # type: ignore
    settings.update_values(123)  # type: ignore

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert data == {"original": "valor"}


# ========================================
# Testes de cache
# ========================================


def test_cache_evita_multiplas_leituras_de_disco(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que cache funciona e evita múltiplas leituras do arquivo."""
    from src.infra import settings

    data = {"cached_key": "cached_value"}
    temp_settings_file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Primeira leitura (popula cache)
    val1 = settings.get_value("cached_key")

    # Deletar arquivo (cache deve evitar erro)
    temp_settings_file.unlink()

    # Segunda leitura (usa cache)
    val2 = settings.get_value("cached_key")

    assert val1 == "cached_value"
    assert val2 == "cached_value"


def test_escrita_atualiza_cache(temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch):
    """Testa que set_value atualiza o cache interno."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    settings.set_value("key1", "value1")

    # Ler sem acessar disco (cache deve ter o valor)
    result = settings.get_value("key1")

    assert result == "value1"


# ========================================
# Testes de erros de escrita em disco
# ========================================


def test_set_value_com_erro_de_escrita_nao_levanta_excecao(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que erros ao escrever não levantam exceção (são logados)."""
    from src.infra import settings

    # Simular erro ao escrever
    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    with patch("builtins.open", side_effect=PermissionError("Sem permissão")):
        # Não deve levantar exceção
        settings.set_value("test_key", "test_value")

    # Valor deve estar em cache mesmo que disco tenha falha
    assert settings.get_value("test_key") == "test_value"


# ========================================
# Testes de threading/lock
# ========================================


def test_concurrent_writes_usam_lock(temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch):
    """Testa que escritas concorrentes usam lock (não testa paralelismo real)."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Verificar que _LOCK existe e é RLock
    from src.infra.settings import _LOCK

    assert type(_LOCK).__name__ == "RLock"

    # Teste simples: múltiplas escritas sequenciais devem funcionar
    for i in range(10):
        settings.set_value(f"key_{i}", f"value_{i}")

    data = json.loads(temp_settings_file.read_text(encoding="utf-8"))
    assert len(data) == 10
    assert data["key_5"] == "value_5"


# ========================================
# Testes adicionais para 100% coverage (COV-INFRA-001)
# ========================================
#
# Objetivo: Cobrir as últimas 2 linhas não cobertas (93-94) de infra/settings.py
# - Linha 93: _CACHE = dict(store) após escrita bem-sucedida
# - Linhas 94-95: except Exception + log.debug em erro de escrita
# - Linha 37: log.debug em erro de leitura (_load_from_disk)
#
# Testes adicionados (9 novos):
# 1. test_cache_atualizado_apos_escrita_bem_sucedida - Garante cache atualizado (linha 93)
# 2. test_erro_ao_criar_arquivo_temporario_nao_levanta_excecao - Erro no .with_suffix(".tmp")
# 3. test_erro_json_dump_nao_levanta_excecao - Erro no json.dump
# 4. test_erro_ao_substituir_arquivo_nao_levanta_excecao - Erro no Path.replace
# 5. test_load_from_disk_com_erro_de_leitura_retorna_vazio - Erro de I/O ao ler
# 6. test_load_from_disk_com_json_decode_error_retorna_vazio - JSON inválido ao ler
# 7. test_update_values_em_modo_cloud_only - update_values em modo memória
# 8. test_set_value_atualiza_cache_em_cloud_only_mode - Cache em modo CLOUD_ONLY
# 9. test_erro_escrita_mantem_cache_anterior - Comportamento "mantém cache anterior" no except
#
# Total de testes: 19 (originais) + 9 (novos) = 28 testes
# Cobertura esperada: 97.3% → 100%
# ========================================


def test_cache_atualizado_apos_escrita_bem_sucedida(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que _CACHE é atualizado corretamente após escrita bem-sucedida (linha 93)."""
    from src.infra import settings
    import src.infra.settings as settings_mod

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Primeira escrita - popula cache
    settings.set_value("key1", "value1")

    # Verificar que cache foi atualizado
    assert settings_mod._CACHE is not None
    assert settings_mod._CACHE.get("key1") == "value1"

    # Segunda escrita - atualiza cache existente
    settings.set_value("key2", "value2")

    # Cache deve ter ambas as chaves
    assert settings_mod._CACHE.get("key1") == "value1"
    assert settings_mod._CACHE.get("key2") == "value2"


def test_erro_ao_criar_arquivo_temporario_nao_levanta_excecao(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que erro ao criar arquivo .tmp não levanta exceção (linha 94-95)."""
    from src.infra import settings
    from pathlib import Path

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Primeiro, criar um valor para ter algo no cache
    settings.set_value("existing", "value")

    # Simular erro ao criar arquivo temporário (com suffix)
    original_with_suffix = Path.with_suffix

    def mock_with_suffix(self, suffix):
        if suffix == ".tmp":
            raise OSError("Não é possível criar arquivo temporário")
        return original_with_suffix(self, suffix)

    with patch.object(Path, "with_suffix", mock_with_suffix):
        # Não deve levantar exceção
        settings.set_value("new_key", "new_value")

    # Quando há erro de escrita, o except block é acionado e cache NÃO é atualizado
    # O valor antigo deve permanecer
    assert settings.get_value("existing") == "value"


def test_erro_json_dump_nao_levanta_excecao(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que erro no json.dump não levanta exceção (linha 94-95)."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Criar um valor inicial
    settings.set_value("initial", "data")

    # Simular erro no json.dump
    with patch("json.dump", side_effect=TypeError("Não serializável")):
        # Não deve levantar exceção
        settings.set_value("problematic", "value")

    # Quando há erro, except block captura e cache anterior é mantido
    # Valor anterior deve permanecer
    assert settings.get_value("initial") == "data"


def test_erro_ao_substituir_arquivo_nao_levanta_excecao(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que erro ao fazer replace do arquivo temporário não levanta exceção."""
    from src.infra import settings
    from pathlib import Path

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Criar valor inicial
    settings.set_value("key", "value")

    # Simular erro no replace
    original_replace = Path.replace

    def mock_replace(self, target):
        if str(self).endswith(".tmp"):
            raise OSError("Falha ao substituir arquivo")
        return original_replace(self, target)

    with patch.object(Path, "replace", mock_replace):
        # Não deve levantar exceção
        settings.set_value("another_key", "another_value")

    # Quando há erro, except block captura e cache anterior é mantido
    assert settings.get_value("key") == "value"


def test_load_from_disk_com_erro_de_leitura_retorna_vazio(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que _load_from_disk retorna {} quando há erro ao ler arquivo (linha 37)."""
    from src.infra import settings
    import src.infra.settings as settings_mod
    from pathlib import Path

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # NÃO criar arquivo - queremos testar quando arquivo não existe E há erro ao ler
    # Forçar cache a ser None para forçar leitura
    settings_mod._CACHE = None

    # Simular erro ao verificar se arquivo existe
    with patch.object(Path, "exists", return_value=True):
        with patch("builtins.open", side_effect=IOError("Erro de I/O")):
            result = settings.get_value("test", default="fallback")

    # Deve retornar default porque _load_from_disk captura exceção e retorna {}
    assert result == "fallback"


def test_load_from_disk_com_json_decode_error_retorna_vazio(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que _load_from_disk trata JSONDecodeError e retorna {} (linha 37)."""
    from src.infra import settings
    import src.infra.settings as settings_mod

    # Criar arquivo com JSON inválido
    temp_settings_file.write_text("{ invalid json }", encoding="utf-8")

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Forçar cache a ser None para forçar leitura
    settings_mod._CACHE = None

    # get_value deve retornar default porque _load_from_disk captura exceção
    result = settings.get_value("any_key", default="default_value")

    assert result == "default_value"


def test_update_values_em_modo_cloud_only(temp_settings_file, mock_cloud_only_true, clear_settings_cache, monkeypatch):
    """Testa que update_values funciona corretamente em modo CLOUD_ONLY."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Adicionar valores via update_values
    settings.update_values({"key1": "val1", "key2": "val2"})

    # Arquivo não deve ser criado
    assert not temp_settings_file.exists()

    # Valores devem estar disponíveis
    assert settings.get_value("key1") == "val1"
    assert settings.get_value("key2") == "val2"


def test_set_value_atualiza_cache_em_cloud_only_mode(
    temp_settings_file, mock_cloud_only_true, clear_settings_cache, monkeypatch
):
    """Testa que set_value atualiza _CACHE corretamente em modo CLOUD_ONLY."""
    from src.infra import settings
    import src.infra.settings as settings_mod

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Setar valor em modo cloud
    settings.set_value("cloud_key", "cloud_value")

    # Verificar que _CACHE foi atualizado
    assert settings_mod._CACHE is not None
    assert settings_mod._CACHE.get("cloud_key") == "cloud_value"

    # Verificar que _MEMORY_STORE também tem o valor
    assert settings_mod._MEMORY_STORE.get("cloud_key") == "cloud_value"


def test_erro_escrita_mantem_cache_anterior(
    temp_settings_file, mock_cloud_only_false, clear_settings_cache, monkeypatch
):
    """Testa que erro de escrita mantém cache anterior sem propagar exceção."""
    from src.infra import settings

    monkeypatch.setattr("src.infra.settings._SETTINGS_FILE", temp_settings_file)

    # Criar valores iniciais com sucesso
    settings.set_value("key1", "value1")
    settings.set_value("key2", "value2")

    # Simular erro ao fazer json.dump (erro durante escrita)
    with patch("json.dump", side_effect=OSError("Erro ao escrever")):
        # Tentar adicionar novo valor (deve falhar mas não levantar exceção)
        settings.set_value("key3", "value3")

    # Quando há erro, except block é acionado e mantém cache anterior
    # Valores antigos devem permanecer (cache não foi corrompido)
    assert settings.get_value("key1") == "value1"
    assert settings.get_value("key2") == "value2"
