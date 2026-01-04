# -*- coding: utf-8 -*-
"""Testes unitários para contratos de db_schemas.

Verifica consistência dos contratos de colunas para prevenir schema drift.
"""

import unittest

from src.infra.db_schemas import (
    CLIENTS_SELECT_FIELDS,
    CLIENTS_SELECT_FIELDS_COUNT,
    CLIENTS_SELECT_FIELDS_SAFE,
    CLIENT_COLUMNS,
    MEMBERSHIPS_SELECT_FIELDS,
    MEMBERSHIPS_SELECT_FIELDS_SAFE,
    MEMBERSHIPS_SELECT_ORG_ID,
    MEMBERSHIPS_SELECT_ORG_ROLE,
    MEMBERSHIPS_SELECT_ROLE,
    ORG_NOTIFICATIONS_SELECT_FIELDS,
    ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT,
    ORG_NOTIFICATIONS_SELECT_FIELDS_LIST,
    ORG_NOTIFICATIONS_SELECT_FIELDS_SAFE,
    RC_NOTES_SELECT_FIELDS,
    RC_NOTES_SELECT_FIELDS_LIST,
    RC_NOTES_SELECT_FIELDS_SAFE,
    is_schema_drift_error,
    select_fields,
)


class TestDbSchemaContracts(unittest.TestCase):
    """Testes para contratos de colunas de banco."""

    def test_rc_notes_select_fields_has_minimum_columns(self):
        """Verifica que RC_NOTES_SELECT_FIELDS contém campos mínimos."""
        fields_set = set(RC_NOTES_SELECT_FIELDS.split(","))

        required = {"id", "org_id", "author_email", "body", "created_at"}

        self.assertTrue(required.issubset(fields_set), f"RC_NOTES_SELECT_FIELDS deve conter: {required}")

    def test_rc_notes_safe_is_subset_of_full(self):
        """Verifica que RC_NOTES_SELECT_FIELDS_SAFE é subconjunto do completo."""
        full_set = set(RC_NOTES_SELECT_FIELDS.split(","))
        safe_set = set(RC_NOTES_SELECT_FIELDS_SAFE.split(","))

        self.assertTrue(safe_set.issubset(full_set), "SAFE deve ser subconjunto de FULL")

    def test_rc_notes_list_is_subset_of_full(self):
        """Verifica que RC_NOTES_SELECT_FIELDS_LIST é subconjunto do completo."""
        full_set = set(RC_NOTES_SELECT_FIELDS.split(","))
        list_set = set(RC_NOTES_SELECT_FIELDS_LIST.split(","))

        self.assertTrue(list_set.issubset(full_set), "LIST deve ser subconjunto de FULL")

    def test_org_notifications_select_fields_has_minimum_columns(self):
        """Verifica que ORG_NOTIFICATIONS_SELECT_FIELDS contém campos mínimos."""
        fields_set = set(ORG_NOTIFICATIONS_SELECT_FIELDS.split(","))

        required = {"id", "org_id", "module", "event", "message", "is_read", "created_at"}

        self.assertTrue(required.issubset(fields_set), f"ORG_NOTIFICATIONS_SELECT_FIELDS deve conter: {required}")

    def test_org_notifications_safe_is_subset_of_full(self):
        """Verifica que ORG_NOTIFICATIONS_SELECT_FIELDS_SAFE é subconjunto do completo."""
        full_set = set(ORG_NOTIFICATIONS_SELECT_FIELDS.split(","))
        safe_set = set(ORG_NOTIFICATIONS_SELECT_FIELDS_SAFE.split(","))

        self.assertTrue(safe_set.issubset(full_set), "SAFE deve ser subconjunto de FULL")

    def test_org_notifications_list_is_subset_of_full(self):
        """Verifica que ORG_NOTIFICATIONS_SELECT_FIELDS_LIST é subconjunto do completo."""
        full_set = set(ORG_NOTIFICATIONS_SELECT_FIELDS.split(","))
        list_set = set(ORG_NOTIFICATIONS_SELECT_FIELDS_LIST.split(","))

        self.assertTrue(list_set.issubset(full_set), "LIST deve ser subconjunto de FULL")

    def test_org_notifications_count_contains_id(self):
        """Verifica que ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT contém id."""
        self.assertEqual(ORG_NOTIFICATIONS_SELECT_FIELDS_COUNT, "id", "COUNT deve ter apenas 'id'")

    def test_select_fields_helper(self):
        """Verifica que helper select_fields funciona corretamente."""
        result = select_fields("id", "name", "email")

        self.assertEqual(result, "id,name,email")

    def test_select_fields_with_single_column(self):
        """Verifica que helper funciona com uma coluna."""
        result = select_fields("id")

        self.assertEqual(result, "id")

    def test_is_schema_drift_error_detects_42703(self):
        """Verifica que is_schema_drift_error detecta erro 42703."""
        from postgrest.exceptions import APIError

        # Mock de erro 42703 com formato correto (dict)
        mock_error = APIError({"message": "column does not exist", "code": "42703"})

        self.assertTrue(is_schema_drift_error(mock_error))

    def test_is_schema_drift_error_ignores_other_errors(self):
        """Verifica que is_schema_drift_error ignora outros erros."""
        error = ValueError("Some other error")

        self.assertFalse(is_schema_drift_error(error))

    def test_rc_notes_no_duplicate_columns(self):
        """Verifica que RC_NOTES_SELECT_FIELDS não tem colunas duplicadas."""
        fields_list = RC_NOTES_SELECT_FIELDS.split(",")
        fields_set = set(fields_list)

        self.assertEqual(len(fields_list), len(fields_set), "Não deve haver colunas duplicadas")

    def test_org_notifications_no_duplicate_columns(self):
        """Verifica que ORG_NOTIFICATIONS_SELECT_FIELDS não tem colunas duplicadas."""
        fields_list = ORG_NOTIFICATIONS_SELECT_FIELDS.split(",")
        fields_set = set(fields_list)

        self.assertEqual(len(fields_list), len(fields_set), "Não deve haver colunas duplicadas")

    # ==============================================================================
    # CLIENTS - Testes de contratos (P1.1)
    # ==============================================================================

    def test_clients_select_fields_has_minimum_columns(self):
        """Verifica que CLIENTS_SELECT_FIELDS contém campos mínimos."""
        fields_set = set(CLIENTS_SELECT_FIELDS.split(","))

        required = {"id", "org_id", "cnpj"}

        self.assertTrue(required.issubset(fields_set), f"CLIENTS_SELECT_FIELDS deve conter: {required}")

    def test_clients_safe_is_subset_of_full(self):
        """Verifica que CLIENTS_SELECT_FIELDS_SAFE é subconjunto do completo."""
        full_set = set(CLIENTS_SELECT_FIELDS.split(","))
        safe_set = set(CLIENTS_SELECT_FIELDS_SAFE.split(","))

        self.assertTrue(safe_set.issubset(full_set), "SAFE deve ser subconjunto de FULL")

    def test_clients_count_contains_id(self):
        """Verifica que CLIENTS_SELECT_FIELDS_COUNT contém id."""
        self.assertEqual(CLIENTS_SELECT_FIELDS_COUNT, "id", "COUNT deve ter apenas 'id'")

    def test_clients_no_duplicate_columns(self):
        """Verifica que CLIENTS_SELECT_FIELDS não tem colunas duplicadas."""
        fields_list = CLIENTS_SELECT_FIELDS.split(",")
        fields_set = set(fields_list)

        self.assertEqual(len(fields_list), len(fields_set), "Não deve haver colunas duplicadas")

    def test_client_columns_alias_equals_clients_select_fields(self):
        """Verifica que CLIENT_COLUMNS é alias de CLIENTS_SELECT_FIELDS."""
        self.assertEqual(CLIENT_COLUMNS, CLIENTS_SELECT_FIELDS, "CLIENT_COLUMNS deve ser igual a CLIENTS_SELECT_FIELDS")

    # ==============================================================================
    # MEMBERSHIPS - Testes de contratos (P1.1)
    # ==============================================================================

    def test_memberships_select_fields_has_minimum_columns(self):
        """Verifica que MEMBERSHIPS_SELECT_FIELDS contém campos mínimos."""
        fields_set = set(MEMBERSHIPS_SELECT_FIELDS.split(","))

        required = {"user_id", "org_id"}

        self.assertTrue(required.issubset(fields_set), f"MEMBERSHIPS_SELECT_FIELDS deve conter: {required}")

    def test_memberships_safe_is_subset_of_full(self):
        """Verifica que MEMBERSHIPS_SELECT_FIELDS_SAFE é subconjunto do completo."""
        full_set = set(MEMBERSHIPS_SELECT_FIELDS.split(","))
        safe_set = set(MEMBERSHIPS_SELECT_FIELDS_SAFE.split(","))

        self.assertTrue(safe_set.issubset(full_set), "SAFE deve ser subconjunto de FULL")

    def test_memberships_no_duplicate_columns(self):
        """Verifica que MEMBERSHIPS_SELECT_FIELDS não tem colunas duplicadas."""
        fields_list = MEMBERSHIPS_SELECT_FIELDS.split(",")
        fields_set = set(fields_list)

        self.assertEqual(len(fields_list), len(fields_set), "Não deve haver colunas duplicadas")

    def test_memberships_select_org_id_is_valid(self):
        """Verifica que MEMBERSHIPS_SELECT_ORG_ID é 'org_id'."""
        self.assertEqual(MEMBERSHIPS_SELECT_ORG_ID, "org_id")

    def test_memberships_select_role_is_valid(self):
        """Verifica que MEMBERSHIPS_SELECT_ROLE é 'role'."""
        self.assertEqual(MEMBERSHIPS_SELECT_ROLE, "role")

    def test_memberships_select_org_role_contains_both(self):
        """Verifica que MEMBERSHIPS_SELECT_ORG_ROLE contém org_id e role."""
        # Remover espaços para comparação
        fields = [f.strip() for f in MEMBERSHIPS_SELECT_ORG_ROLE.split(",")]
        self.assertIn("org_id", fields)
        self.assertIn("role", fields)


if __name__ == "__main__":
    unittest.main()
