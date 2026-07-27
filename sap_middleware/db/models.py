"""SQLAlchemy ORM models mirroring the SAP data pulled by the connector."""
from sqlalchemy import Column, Date, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Customer(Base):
    """Mirrors SAP table KNA1 (general customer master)."""

    __tablename__ = "sap_customers"

    kunnr = Column("kunnr", String(10), primary_key=True)  # customer number
    name1 = Column("name1", String(35))  # name
    land1 = Column("land1", String(3))  # country
    ort01 = Column("ort01", String(35))  # city
    pstlz = Column("pstlz", String(10))  # postal code
    stras = Column("stras", String(35))  # street


class Material(Base):
    """Mirrors SAP table MARA (general material master)."""

    __tablename__ = "sap_materials"

    matnr = Column("matnr", String(18), primary_key=True)  # material number
    mtart = Column("mtart", String(4))  # material type
    matkl = Column("matkl", String(9))  # material group
    meins = Column("meins", String(3))  # base unit of measure
    ersda = Column("ersda", String(8))  # creation date (YYYYMMDD as returned by RFC_READ_TABLE)


class CompanyCode(Base):
    """Mirrors the result of BAPI_COMPANYCODE_GETLIST."""

    __tablename__ = "sap_company_codes"

    bukrs = Column("bukrs", String(4), primary_key=True)  # company code
    butxt = Column("butxt", String(25))  # company name
    waers = Column("waers", String(35))  # currency / city depending on BAPI version
