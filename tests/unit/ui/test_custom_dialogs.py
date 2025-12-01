from src.ui import custom_dialogs


def test_confirm_dialog_labels():
    assert custom_dialogs.OK_LABEL == "Sim"
    assert custom_dialogs.CANCEL_LABEL == "Não"
