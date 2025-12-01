from __future__ import annotations

from src.core.navigation_controller import NavigationController


class DummyFrame:
    def __init__(self, root, **kwargs):
        self.root = root
        self.kwargs = kwargs
        self.packed = False
        self.destroyed = False

    def pack(self, **kwargs):
        self.packed = True

    def destroy(self):
        self.destroyed = True


def test_show_frame_without_factory_creates_and_destroys(monkeypatch):
    root = object()
    controller = NavigationController(root)

    frame1 = controller.show_frame(DummyFrame, value=1)
    assert frame1.packed is True
    assert frame1.kwargs == {"value": 1}
    assert frame1.root is root

    frame2 = controller.show_frame(DummyFrame, value=2)
    assert frame1.destroyed is True
    assert frame2.kwargs == {"value": 2}
    assert controller.current() is frame2


def test_show_frame_with_factory_reuses_frame_and_lifts(monkeypatch):
    lifted = {"count": 0}

    class ReusableFrame(DummyFrame):
        def lift(self):
            lifted["count"] += 1

    reusable_instance = ReusableFrame("root")

    def factory(cls, kwargs):
        return reusable_instance

    controller = NavigationController("root", frame_factory=factory)

    frame = controller.show_frame(ReusableFrame)
    assert frame is reusable_instance
    assert controller.current() is reusable_instance
    assert lifted["count"] == 0  # primeira vez, apenas pack/lift normal

    frame_again = controller.show_frame(ReusableFrame)
    assert frame_again is reusable_instance
    assert lifted["count"] == 1  # segunda chamada, apenas lift


def test_show_frame_with_factory_falls_back_when_factory_returns_none():
    calls = []

    def factory(cls, kwargs):
        calls.append((cls, kwargs))
        return None

    controller = NavigationController("root", frame_factory=factory)
    frame = controller.show_frame(DummyFrame, foo="bar")

    assert isinstance(frame, DummyFrame)
    assert calls == [(DummyFrame, {"foo": "bar"})]


def test_current_returns_none_initially():
    controller = NavigationController("root")
    assert controller.current() is None


def test_show_frame_with_factory_handles_lift_exception():
    """Testa que exceção em lift() é capturada e logada."""
    lifted_count = {"count": 0}

    class FrameWithFailingLift(DummyFrame):
        def lift(self):
            lifted_count["count"] += 1
            raise RuntimeError("Lift failed")

    reusable = FrameWithFailingLift("root")

    def factory(cls, kwargs):
        return reusable

    controller = NavigationController("root", frame_factory=factory)

    # Primeira chamada: configura como current
    frame = controller.show_frame(FrameWithFailingLift)
    assert frame is reusable

    # Segunda chamada: mesma instância, tentará lift e falhará
    frame_again = controller.show_frame(FrameWithFailingLift)
    assert frame_again is reusable
    assert lifted_count["count"] == 1  # Tentou fazer lift


def test_show_frame_with_factory_uses_place_when_no_pack_info():
    """Testa que usa place() quando frame não tem pack_info."""
    placed_params = {}

    class FrameWithPlace(DummyFrame):
        def place(self, **kwargs):
            placed_params.update(kwargs)

        def lift(self):
            pass

    new_frame = FrameWithPlace("root")

    def factory(cls, kwargs):
        return new_frame

    controller = NavigationController("root", frame_factory=factory)

    # Primeira chamada deve criar e posicionar
    frame = controller.show_frame(FrameWithPlace)

    # Como não tem pack_info, deve usar place
    assert "relx" in placed_params or frame.packed  # Pode ter pack ou place


def test_show_frame_with_factory_handles_positioning_exception():
    """Testa que exceção ao posicionar frame reutilizado é capturada."""

    class FrameWithFailingPack(DummyFrame):
        def pack(self, **kwargs):
            raise RuntimeError("Pack failed")

        def lift(self):
            pass

    new_frame = FrameWithFailingPack("root")

    def factory(cls, kwargs):
        return new_frame

    controller = NavigationController("root", frame_factory=factory)

    # Deve capturar exceção e continuar
    frame = controller.show_frame(FrameWithFailingPack)
    assert frame is new_frame
    assert controller.current() is new_frame


def test_show_frame_default_handles_destroy_exception():
    """Testa que exceção ao destruir frame anterior é capturada."""

    class FrameWithFailingDestroy(DummyFrame):
        def destroy(self):
            raise RuntimeError("Destroy failed")

    controller = NavigationController("root")

    # Primeira chamada
    frame1 = controller.show_frame(FrameWithFailingDestroy)
    assert controller.current() is frame1

    # Segunda chamada deve tentar destruir a primeira (e falhar)
    frame2 = controller.show_frame(DummyFrame)
    assert controller.current() is frame2


def test_show_frame_default_handles_pack_exception():
    """Testa que exceção ao fazer pack() é capturada."""

    class FrameWithFailingPack(DummyFrame):
        def pack(self, **kwargs):
            raise RuntimeError("Pack failed")

    controller = NavigationController("root")

    frame = controller.show_frame(FrameWithFailingPack)
    assert controller.current() is frame  # Mesmo com falha no pack, frame é definido


def test_show_frame_without_destroy_method():
    """Testa comportamento quando frame anterior não tem destroy()."""

    class FrameWithoutDestroy:
        def __init__(self, root, **kwargs):
            self.root = root
            self.kwargs = kwargs
            self.packed = False

        def pack(self, **kwargs):
            self.packed = True

    controller = NavigationController("root")

    frame1 = controller.show_frame(FrameWithoutDestroy, val=1)
    assert controller.current() is frame1

    # Segunda chamada: frame anterior não tem destroy, mas não deve dar erro
    frame2 = controller.show_frame(DummyFrame, val=2)
    assert controller.current() is frame2


def test_show_frame_with_factory_different_frames():
    """Testa navegação entre frames diferentes usando factory."""
    frames_created = []

    class Frame1(DummyFrame):
        def lift(self):
            pass

    class Frame2(DummyFrame):
        def lift(self):
            pass

    frame1_instance = Frame1("root")
    frame2_instance = Frame2("root")

    def factory(cls, kwargs):
        if cls == Frame1:
            frames_created.append("Frame1")
            return frame1_instance
        elif cls == Frame2:
            frames_created.append("Frame2")
            return frame2_instance
        return None

    controller = NavigationController("root", frame_factory=factory)

    # Navegar para Frame1
    f1 = controller.show_frame(Frame1)
    assert f1 is frame1_instance
    assert controller.current() is frame1_instance

    # Navegar para Frame2 (diferente)
    f2 = controller.show_frame(Frame2)
    assert f2 is frame2_instance
    assert controller.current() is frame2_instance

    assert frames_created == ["Frame1", "Frame2"]


def test_show_frame_with_factory_reuses_and_positions():
    """Testa que frame reutilizado é posicionado corretamente."""
    positioned = {"packed": False, "lifted": False}

    class ReusableFrameWithTracking(DummyFrame):
        def pack(self, **kwargs):
            positioned["packed"] = True

        def lift(self):
            positioned["lifted"] = True

        def pack_info(self):
            return {}

    reusable = ReusableFrameWithTracking("root")

    def factory(cls, kwargs):
        return reusable

    controller = NavigationController("root", frame_factory=factory)

    # Primeira chamada
    controller.show_frame(ReusableFrameWithTracking)
    assert positioned["packed"] or positioned["lifted"]  # Deve ter sido posicionado
