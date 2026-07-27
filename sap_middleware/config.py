"""Configuration loaded from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


class SAPConfig:
    ASHOST = _env("SAP_ASHOST", "")
    SYSNR = _env("SAP_SYSNR", "00")
    CLIENT = _env("SAP_CLIENT", "800")
    USER = _env("SAP_USER", "")
    PASSWD = _env("SAP_PASSWD", "")
    LANG = _env("SAP_LANG", "EN")

    @classmethod
    def as_connection_params(cls) -> dict:
        return {
            "ashost": cls.ASHOST,
            "sysnr": cls.SYSNR,
            "client": cls.CLIENT,
            "user": cls.USER,
            "passwd": cls.PASSWD,
            "lang": cls.LANG,
        }


class DBConfig:
    MARIADB_URL = _env("MARIADB_URL", "mysql+pymysql://sap:sap@localhost:3306/sap_middleware")
    POSTGRES_URL = _env("POSTGRES_URL", "postgresql+psycopg2://sap:sap@localhost:5432/sap_middleware")


MOCK_MODE = _env("SAP_MOCK_MODE", "true").lower() in ("1", "true", "yes")
