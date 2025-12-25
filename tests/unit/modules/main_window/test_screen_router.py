# -*- coding: utf-8 -*-
"""Testes unitários do ScreenRouter."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import pytest

from src.modules.main_window.controllers import ScreenRouter


@pytest.fixture
def container():
    """Mock de container Tkinter."""
    return MagicMock()


@pytest.fixture
def router(container):
    """Router com container mockado."""
    return ScreenRouter(container)


@pytest.fixture
def mock_screen():
    """Mock de tela com métodos pack/place/lift/forget."""

    def _create():
        screen = Mock()
        screen.pack = Mock()
        screen.pack_forget = Mock()
        screen.place = Mock()
        screen.place_forget = Mock()
        screen.lift = Mock()
        return screen

    return _create


class TestRegister:
    """Testes do método register()."""

    def test_register_adiciona_factory(self, router):
        """register() deve adicionar factory ao registro."""
        factory = Mock(return_value="screen_instance")

        router.register("test", factory, cache=True)

        assert "test" in router._factories
        assert router._factories["test"] == (factory, True)

    def test_register_cache_false(self, router):
        """register() com cache=False deve marcar como não cacheável."""
        factory = Mock()

        router.register("test", factory, cache=False)

        _, should_cache = router._factories["test"]
        assert should_cache is False


class TestShow:
    """Testes do método show()."""

    def test_show_cria_nova_instancia(self, router, mock_screen):
        """show() deve criar nova instância na primeira chamada."""
        screen = mock_screen()
        factory = Mock(return_value=screen)

        router.register("test", factory)
        result = router.show("test")

        factory.assert_called_once()
        assert result is screen

    def test_show_cacheia_instancia_por_padrao(self, router, mock_screen):
        """show() deve cachear instância por padrão (cache=True)."""
        screen = mock_screen()
        factory = Mock(return_value=screen)

        router.register("test", factory)
        router.show("test")
        router.show("test")  # Segunda chamada

        # Factory deve ser chamada apenas uma vez
        factory.assert_called_once()

    def test_show_nao_cacheia_se_cache_false(self, router, mock_screen):
        """show() não deve cachear se cache=False."""
        factory = Mock(side_effect=[mock_screen(), mock_screen()])

        router.register("test", factory, cache=False)
        screen1 = router.show("test")
        screen2 = router.show("test")

        # Factory deve ser chamada duas vezes
        assert factory.call_count == 2
        assert screen1 is not screen2

    def test_show_esconde_tela_anterior(self, router, mock_screen):
        """show() deve esconder tela anterior ao mostrar nova."""
        screen1 = mock_screen()
        screen2 = mock_screen()

        router.register("screen1", Mock(return_value=screen1))
        router.register("screen2", Mock(return_value=screen2))

        router.show("screen1")
        router.show("screen2")

        # screen1 deve ter sido escondida
        screen1.pack_forget.assert_called_once()

    def test_show_nao_esconde_se_mesma_tela(self, router, mock_screen):
        """show() não deve esconder se mostrar a mesma tela."""
        screen = mock_screen()
        factory = Mock(return_value=screen)

        router.register("test", factory)
        router.show("test")
        router.show("test")  # Mesma tela

        # pack_forget não deve ser chamado (mesma tela)
        screen.pack_forget.assert_not_called()

    def test_show_atualiza_current_name(self, router, mock_screen):
        """show() deve atualizar current_name()."""
        router.register("test", Mock(return_value=mock_screen()))

        router.show("test")

        assert router.current_name() == "test"

    def test_show_atualiza_current_screen(self, router, mock_screen):
        """show() deve atualizar current_screen()."""
        screen = mock_screen()
        router.register("test", Mock(return_value=screen))

        router.show("test")

        assert router.current_screen() is screen

    def test_show_levanta_erro_se_nao_registrada(self, router):
        """show() deve levantar ValueError se tela não registrada."""
        with pytest.raises(ValueError, match="Tela não registrada: unknown"):
            router.show("unknown")

    def test_show_chama_place_para_mostrar(self, router, mock_screen):
        """show() deve chamar place() para mostrar tela."""
        screen = mock_screen()
        router.register("test", Mock(return_value=screen))

        router.show("test")

        screen.place.assert_called_once_with(
            relx=0,
            rely=0,
            relwidth=1,
            relheight=1,
        )

    def test_show_chama_lift_apos_place(self, router, mock_screen):
        """show() deve chamar lift() após place()."""
        screen = mock_screen()
        router.register("test", Mock(return_value=screen))

        router.show("test")

        screen.lift.assert_called_once()

    def test_show_fallback_pack_se_place_falha(self, router, mock_screen):
        """show() deve tentar pack() se place() falhar."""
        screen = mock_screen()
        screen.place.side_effect = Exception("Place error")

        router.register("test", Mock(return_value=screen))
        router.show("test")

        # pack deve ser chamado como fallback
        screen.pack.assert_called_once_with(fill="both", expand=True)


class TestCurrents:
    """Testes de current_name() e current_screen()."""

    def test_current_name_none_antes_de_show(self, router):
        """current_name() deve retornar None antes de qualquer show()."""
        assert router.current_name() is None

    def test_current_screen_none_antes_de_show(self, router):
        """current_screen() deve retornar None antes de qualquer show()."""
        assert router.current_screen() is None


class TestClearCache:
    """Testes do método clear_cache()."""

    def test_clear_cache_sem_nome_limpa_tudo(self, router, mock_screen):
        """clear_cache() sem argumento deve limpar todo o cache."""
        router.register("screen1", Mock(return_value=mock_screen()))
        router.register("screen2", Mock(return_value=mock_screen()))

        router.show("screen1")
        router.show("screen2")

        assert len(router._cache) == 2

        router.clear_cache()

        assert len(router._cache) == 0

    def test_clear_cache_com_nome_limpa_especifica(self, router, mock_screen):
        """clear_cache(name) deve limpar apenas tela específica."""
        router.register("screen1", Mock(return_value=mock_screen()))
        router.register("screen2", Mock(return_value=mock_screen()))

        router.show("screen1")
        router.show("screen2")

        router.clear_cache("screen1")

        assert "screen1" not in router._cache
        assert "screen2" in router._cache


class TestHideScreen:
    """Testes do método _hide_screen()."""

    def test_hide_screen_chama_pack_forget(self, router, mock_screen):
        """_hide_screen() deve chamar pack_forget() primeiro."""
        screen = mock_screen()

        router._hide_screen(screen)

        screen.pack_forget.assert_called_once()

    def test_hide_screen_fallback_place_forget_se_pack_falha(self, router, mock_screen):
        """_hide_screen() deve tentar place_forget() se pack_forget() falhar."""
        screen = mock_screen()
        screen.pack_forget.side_effect = Exception("Pack error")

        router._hide_screen(screen)

        screen.place_forget.assert_called_once()
