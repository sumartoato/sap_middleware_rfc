from sap_middleware.sap_connector import SAPConnector


def test_mock_ping():
    with SAPConnector(mock=True) as sap:
        assert sap.ping() is True


def test_mock_get_customers():
    with SAPConnector(mock=True) as sap:
        customers = sap.get_customers()
    assert len(customers) == 3
    assert customers[0]["KUNNR"] == "0000001032"


def test_mock_get_materials():
    with SAPConnector(mock=True) as sap:
        materials = sap.get_materials()
    assert len(materials) == 3
    assert materials[0]["MTART"] == "FERT"


def test_mock_get_company_codes():
    with SAPConnector(mock=True) as sap:
        codes = sap.get_company_codes()
    assert {c["BUKRS"] for c in codes} == {"1000", "2000", "3000"}
