# sap_middleware_rfc

Middleware Python sederhana yang menarik data dari SAP lewat **RFC** (Remote
Function Call) dan mensinkronkannya ke **MariaDB** dan/atau **PostgreSQL**.

Dilengkapi **mode mock** (data contoh ala SAP IDES) sehingga seluruh pipeline
bisa dicoba tanpa punya akses ke SAP sungguhan.

## Arsitektur

```
 SAP System (RFC)                 Python Middleware                 Database
┌─────────────────┐   RFC_READ_TABLE   ┌───────────────────┐  SQLAlchemy   ┌───────────┐
│  KNA1 (customer) │ ─────────────────▶ │  SAPConnector      │ ───────────▶ │  MariaDB  │
│  MARA (material) │   BAPI_...         │  (pyrfc / mock)    │              └───────────┘
│  BAPI_COMPANY...  │ ─────────────────▶ │        │           │ ───────────▶ ┌───────────┐
└─────────────────┘                    │  sync_service.py    │              │ PostgreSQL│
                                        └───────────────────┘              └───────────┘
```

- `sap_middleware/sap_connector.py` — koneksi RFC ke SAP (pakai `pyrfc`), atau
  baca fixture JSON di `examples/` kalau `SAP_MOCK_MODE=true`.
- `sap_middleware/sync/sync_service.py` — upsert data ke MariaDB/PostgreSQL
  lewat SQLAlchemy (`ON DUPLICATE KEY UPDATE` / `ON CONFLICT DO UPDATE`).
- `main.py` — CLI untuk test koneksi dan menjalankan sync.

## Prasyarat

- Python 3.10+
- Untuk koneksi SAP **sungguhan**:
  - Akses ke SAP system (host, system number, client, user RFC, password).
  - **SAP NW RFC SDK** (library C, bukan dari PyPI) — download dari SAP
    Support Portal dengan akun S-user:
    https://support.sap.com/en/product/connectors/nwrfcsdk.html
  - Package `pyrfc` yang di-build/diinstall terhadap SDK tersebut (lihat
    bagian [Koneksi SAP sungguhan](#koneksi-sap-sungguhan) di bawah).
- Untuk sync ke database: MariaDB dan/atau PostgreSQL (disediakan lewat
  `docker-compose.yml` untuk uji coba lokal).

## Tentang SAP IDES (data demo SAP)

**IDES** (Internet Demonstration and Evaluation System) adalah sistem SAP
ECC berisi data contoh perusahaan fiktif (customer, material, company code,
dll) yang biasa dipakai untuk latihan/training. IDES **bukan software yang
bisa didownload bebas** — SAP kini menyediakannya sebagai *appliance* siap
pakai (bayar per jam, di AWS/Azure/GCP) lewat:

- **SAP Cloud Appliance Library (CAL)**: https://cal.sap.com — login dengan
  akun SAP, buka menu *Appliance Templates*, cari image IDES atau
  *SAP S/4HANA Fully-Activated Appliance* (versi lebih ringan & modern,
  sudah terisi data contoh untuk latihan Fiori/functional).
- Info produk CAL: https://www.sap.com/products/technology-platform/cloud-appliance-library.html
- Kalau belum punya akun SAP, ajukan lewat halaman *Request Access* di CAL.

Karena akses IDES butuh akun SAP resmi (dan berbayar per jam untuk resource
cloud-nya), repo ini menyediakan **mode mock** dengan data contoh yang meniru
struktur tabel IDES (`KNA1`, `MARA`, company code) supaya kamu bisa coba
seluruh alur (RFC → sync ke DB) tanpa harus provisioning IDES dulu. Ganti ke
mode real kapan pun sudah punya akses.

## Instalasi

```bash
git clone <repo-ini>
cd sap_middleware_rfc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Cara pakai — mode mock (tanpa SAP sungguhan)

`.env` bawaan sudah `SAP_MOCK_MODE=true`, jadi langsung bisa dicoba.

1. Jalankan database lokal (MariaDB + PostgreSQL) via Docker:

   ```bash
   docker compose up -d
   ```

2. Cek "koneksi" SAP (mock):

   ```bash
   python main.py test-connection
   ```

3. Sync semua data contoh (customer, material, company code) ke kedua database:

   ```bash
   python main.py sync --object all --target both
   ```

   Atau sync satu objek saja ke satu target:

   ```bash
   python main.py sync --object customers --target mariadb
   python main.py sync --object materials --target postgres --max-rows 50
   python main.py sync --object company-codes --target both
   ```

   Perintah ini idempoten — dijalankan berkali-kali hasilnya tetap konsisten
   (upsert berdasarkan primary key SAP: `KUNNR`, `MATNR`, `BUKRS`).

4. Cek hasilnya di database, contoh untuk PostgreSQL:

   ```bash
   psql -h localhost -U sap -d sap_middleware -c "SELECT * FROM sap_customers;"
   ```

### Contoh data (mock, ala IDES)

`examples/sample_customers.json`:

```json
[
  {"KUNNR": "0000001032", "NAME1": "Becker Berlin", "LAND1": "DE", "ORT01": "Berlin", "PSTLZ": "10115", "STRAS": "Motzstr. 34"},
  {"KUNNR": "0000001172", "NAME1": "Auto-Schmidt GmbH", "LAND1": "DE", "ORT01": "Stuttgart", "PSTLZ": "70173", "STRAS": "Konigstr. 12"}
]
```

`examples/sample_materials.json` dan `examples/sample_company_codes.json`
berisi contoh serupa untuk tabel `MARA` dan hasil `BAPI_COMPANYCODE_GETLIST`.

## Koneksi SAP sungguhan

1. Download **SAP NW RFC SDK** (sesuai OS, mis. `nwrfcsdk-linux-x86_64`) dari
   SAP Support Portal, lalu ekstrak dan set environment variable:

   ```bash
   export SAPNWRFC_HOME=/opt/nwrfcsdk
   export LD_LIBRARY_PATH=$SAPNWRFC_HOME/lib:$LD_LIBRARY_PATH   # Linux
   ```

2. Install `pyrfc` (build dari source terhadap SDK di atas — lihat panduan
   resmi di https://github.com/SAP/PyRFC):

   ```bash
   pip install pyrfc
   ```

3. Isi `.env`:

   ```env
   SAP_MOCK_MODE=false
   SAP_ASHOST=<host-atau-ip-application-server>
   SAP_SYSNR=00
   SAP_CLIENT=800
   SAP_USER=<rfc-user>
   SAP_PASSWD=<password>
   SAP_LANG=EN
   ```

   User RFC minimal butuh authorization untuk memanggil `RFC_READ_TABLE`
   (atau BAPI yang dipakai) dan otorisasi baca tabel `S_TABU_DIS` untuk
   tabel yang bersangkutan.

4. Jalankan seperti biasa:

   ```bash
   python main.py test-connection
   python main.py sync --object all --target both
   ```

## Konfigurasi (`.env`)

| Variabel        | Keterangan                                              |
|-----------------|----------------------------------------------------------|
| `SAP_MOCK_MODE` | `true` = pakai data contoh di `examples/`, `false` = RFC asli |
| `SAP_ASHOST`    | Application server SAP                                   |
| `SAP_SYSNR`     | System number (mis. `00`)                                 |
| `SAP_CLIENT`    | Client SAP (mis. `800`)                                   |
| `SAP_USER` / `SAP_PASSWD` | Kredensial user RFC                              |
| `MARIADB_URL`   | SQLAlchemy URL, default `mysql+pymysql://sap:sap@localhost:3306/sap_middleware` |
| `POSTGRES_URL`  | SQLAlchemy URL, default `postgresql+psycopg2://sap:sap@localhost:5432/sap_middleware` |

## Struktur proyek

```
sap_middleware_rfc/
├── main.py                       # CLI (test-connection, sync)
├── sap_middleware/
│   ├── config.py                 # load .env
│   ├── sap_connector.py          # koneksi RFC / mock
│   ├── db/
│   │   ├── base.py                # engine & session per target
│   │   └── models.py              # model SQLAlchemy: Customer, Material, CompanyCode
│   └── sync/
│       └── sync_service.py        # logic upsert ke MariaDB/PostgreSQL
├── examples/                      # data contoh ala SAP IDES (mock mode)
├── tests/                         # unit test mode mock
├── docker-compose.yml             # MariaDB + PostgreSQL untuk uji lokal
└── .env.example
```

## Menambah objek data baru

1. Tambah method di `SAPConnector` (mis. `get_sales_orders`) yang memanggil
   `read_table(...)` atau BAPI terkait, plus fixture mock di `examples/`.
2. Tambah model SQLAlchemy baru di `sap_middleware/db/models.py`.
3. Tambah fungsi `sync_xxx()` di `sync_service.py` dan daftarkan di
   `main.py` (`--object`).

## Testing

```bash
pytest tests/ -v
```

Test yang ada memverifikasi `SAPConnector` mode mock mengembalikan data
sesuai fixture (tidak butuh SAP atau database asli). Pipeline sync sudah
diverifikasi manual end-to-end ke MariaDB dan PostgreSQL sungguhan.
