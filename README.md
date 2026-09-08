# Sales Repository

Offline product inventory & sales management app for small businesses, built with **Python + Kivy + KivyMD**, backed by a local **SQLite** database. No internet connection, cloud account, or server is required at any point.

---

## 1. Project Structure

```
product_inventory/
├── main.py                     # App entry point: wires DB, services, screens
├── requirements.txt             # Desktop dev dependencies
├── buildozer.spec               # Android APK build configuration
├── README.md
│
├── database/
│   ├── database.py              # Connection, schema, transactions, reset
│   ├── models.py                # Product / Category / Transaction dataclasses
│   └── migrations.py            # Forward-only schema migration runner
│
├── services/
│   ├── inventory_service.py     # Products, categories, stock movements (core logic)
│   ├── report_service.py        # Today/product/category/low-stock reports
│   ├── backup_service.py        # Backup, restore, auto-backup
│   ├── export_service.py        # CSV export
│   └── settings_service.py      # App settings + admin PIN (hashed)
│
├── screens/                     # One MDScreen subclass per app screen
│   ├── dashboard.py
│   ├── products.py
│   ├── add_product.py
│   ├── product_details.py
│   ├── categories.py
│   ├── transactions.py
│   ├── reports.py
│   ├── daily_summary.py
│   ├── admin_login.py
│   ├── admin.py
│   └── settings.py
│
├── widgets/                     # Reusable UI components
│   ├── statistic_card.py        # Dashboard stat tile
│   ├── product_card.py          # Product list row + quick actions
│   ├── transaction_item.py      # Transaction history row
│   ├── admin_action_tile.py     # Admin hub menu row
│   └── bottom_nav.py            # Custom bottom navigation bar
│
├── utils/
│   ├── validation.py            # Input validation (ValidationError)
│   ├── formatting.py            # Date/price/product-code formatting
│   └── security.py              # PBKDF2 PIN hashing
│
├── tests/                       # unittest suite (no Kivy required to run)
│   ├── test_inventory_service.py
│   ├── test_backup_service.py
│   └── test_settings_and_utils.py
│
├── assets/
│   ├── icons/icon.png            # App icon (placeholder - replace with your own)
│   └── images/presplash.png      # Splash screen (placeholder)
│
├── backups/                      # Local .db backups (gitignored, created at runtime)
└── exports/                      # CSV exports (gitignored, created at runtime)
```

**Architecture** (offline-first, no backend):

```
Kivy/KivyMD UI (screens/, widgets/)
        │
        ▼
Services (services/*.py)   <-- all business rules & validation live here
        │
        ▼
Database (database/database.py)  <-- one SQLite connection, WAL mode
        │
   ┌────┴────┐
   ▼         ▼
Backup file   CSV export
```

Screens never touch SQLite directly - they only call `InventoryService` / `ReportService` / `BackupService` / `ExportService` / `SettingsService`, which are attached to the running `App` instance (`MDApp.get_running_app()`). This keeps validation and the audit-trail rule ("every stock change is a transaction") in one place.

---

## 2. Database Schema

SQLite, 4 tables, WAL journaling, foreign keys enforced. See [database/database.py](database/database.py) for the exact DDL.

```
categories                        products
─────────────                     ─────────────────────────
id            INTEGER PK          id              INTEGER PK
name          TEXT UNIQUE         product_code    TEXT UNIQUE
created_at    TEXT                name            TEXT
                                   category_id     INTEGER FK -> categories.id
                                   quantity        INTEGER  (>= 0)
transactions                      minimum_stock   INTEGER  (>= 0)
─────────────────────────         price           REAL
id                 INTEGER PK     status          TEXT  ACTIVE | ARCHIVED
product_id         INTEGER FK     created_at      TEXT
product_name       TEXT           updated_at      TEXT
transaction_type   TEXT
quantity            INTEGER       settings
previous_quantity   INTEGER       ─────────────
new_quantity        INTEGER       id     INTEGER PK
reason              TEXT          key    TEXT UNIQUE
created_at          TEXT          value  TEXT
```

Transaction types: `STOCK_IN`, `SALE`, `STOCK_ADJUSTMENT`, `PRODUCT_CREATED`, `PRODUCT_ARCHIVED`, `PRODUCT_RESTORED`.

Indexes on `products(name, category_id, status, product_code)` and `transactions(product_id, created_at, transaction_type)` keep search/filter/sort fast up to several thousand products.

**Audit rule**: every write that changes `products.quantity` happens inside `Database.transaction()` together with the matching `transactions` insert, so a crash mid-write can never leave stock changed without a recorded reason (see `InventoryService.increase_stock` / `sell_stock` / `adjust_stock`).

**Nothing is hard-deleted** by normal app operations. "Delete Product" does not exist - only **Archive** (`products.status = 'ARCHIVED'`), which hides it from the active list while keeping every transaction. Categories can only be deleted when zero products (active or archived) reference them.

---

## 3. Local Installation & Testing (Windows/Mac/Linux desktop)

The **business logic** (`database/`, `services/`, `utils/`) has zero Kivy dependency and is unit-tested directly. The **UI** (`screens/`, `widgets/`, `main.py`) needs Kivy + KivyMD installed to run.

### 3.1 Run the logic tests (no Kivy needed)

```bash
python -m unittest discover -s tests -v
```

All 29 tests should pass. This is the fastest way to verify the core rules (stock never goes negative, archiving preserves history, PIN is hashed, backup/restore round-trips, etc.) without installing any GUI dependency.

### 3.2 Run the full app on desktop

> **Note on this build environment:** Kivy's Windows wheels (`kivy_deps.sdl2` / `gstreamer`) do not yet publish binaries for very new Python releases (this machine has Python 3.14, and Kivy 2.2.1/2.3.1 currently only ship Windows wheels up to ~3.12). **Use Python 3.10, 3.11, or 3.12** for the desktop GUI. If you only have 3.14 available, either install a second Python via the [python.org installer](https://www.python.org/downloads/) side-by-side, or test via WSL (section 4).

```bash
# from a Python 3.10-3.12 environment
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
python main.py
```

The app creates its database at `./data/sales_repository.db` (relative to the project) when run this way. On a real Android install it instead uses the app's private storage directory automatically - no code changes needed.

### 3.3 What "done" looks like on first run

1. Dashboard shows all-zero stats and the 7 default categories exist (Food, Drinks, Electronics, Clothing, Stationery, Medicine, Other).
2. Add a product from the **Products** tab (`+` FAB) - it appears immediately with a `P001`-style code.
3. Use **+ Stock** / **- Sell** on the product card - dashboard numbers update on next visit.
4. Try selling more than available stock - you get the "Not enough stock available" message, and stock is unchanged.
5. Close the app (or `Ctrl+C` the process) and reopen it - the product and its history are still there.

---

## 4. Android APK Build (via WSL - required on Windows)

**Buildozer cannot run on native Windows.** It depends on Linux-only tooling (the Android NDK toolchain, Cython builds of SDL2, etc.). Use **WSL2 with Ubuntu**.

### 4.1 One-time WSL setup

```powershell
# In PowerShell (as Administrator), from Windows:
wsl --install -d Ubuntu
```

Restart if prompted, then open the "Ubuntu" app from the Start menu and finish the Linux user setup.

### 4.2 Install build dependencies (inside WSL/Ubuntu)

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv build-essential git zip unzip \
    openjdk-17-jdk libssl-dev libffi-dev python3-dev \
    autoconf automake libtool pkg-config cmake

pip3 install --user buildozer cython==0.29.33
```

### 4.3 Copy the project into WSL and build

Buildozer works far more reliably on the Linux filesystem than on the Windows-mounted `/mnt/d/...` path, so copy the project in rather than building it in place:

```bash
mkdir -p ~/projects
cp -r "/mnt/d/Sadik/product Management app" ~/projects/sales_repository
cd ~/projects/sales_repository

buildozer android debug
```

The first build downloads the Android SDK/NDK (several GB) and can take 20-60+ minutes. Subsequent builds are much faster (incremental).

On success, the APK is at:

```
~/projects/sales_repository/bin/salesrepository-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

### 4.4 Install the APK on your phone

**Option A - USB (recommended):**
```bash
# with the phone connected via USB and USB debugging enabled:
buildozer android deploy run
```

**Option B - manual transfer:**
1. Copy the `.apk` from `bin/` to your phone (USB cable, or upload somewhere and download it).
2. On the phone, enable **Settings -> Security -> Install unknown apps** for your file manager / browser.
3. Tap the `.apk` file and install.

### 4.5 Release build (signed, for distribution)

```bash
buildozer android release
```

This produces an **unsigned** release APK/AAB under `bin/`. You must sign it yourself before distributing (Google Play or sideloading):

```bash
# generate a keystore once, keep it safe - losing it means you can never update the app again
keytool -genkey -v -keystore sales_repository.keystore -alias sales_repository \
    -keyalg RSA -keysize 2048 -validity 10000

# sign
jarsigner -verbose -sigalg SHA256withRSA -digestalg SHA-256 \
    -keystore sales_repository.keystore bin/salesrepository-*-release-unsigned.apk sales_repository

# align (requires Android build-tools, installed by buildozer under ~/.buildozer)
zipalign -v 4 bin/salesrepository-*-release-unsigned.apk bin/salesrepository-release.apk
```

---

## 5. Backup & Restore

- **Manual backup**: Settings -> Backup & Restore -> **Backup Now**. Creates `inventory_backup_<date>_<time>_manual.db` under the app's private `backups/` folder.
- **Automatic backup**: enabled by default. On every app startup, if the configured interval (default: 1 day) has elapsed since the last automatic backup, one is taken silently and old auto-backups beyond the last 10 are pruned. Toggle this off in Settings.
- **Restore**: Settings -> **Restore From Backup** -> pick a file -> confirm. The current database file is overwritten with the backup's contents; you're asked to confirm first since this replaces current data.
- **CSV export**: available for Products, Transactions, Daily Summary, Category Report, and Low Stock Report - from the Reports and Transactions screens. Files are written to the app's private `exports/` folder.
- **"Reset Database" (Settings -> Advanced)**: development/testing-only, hidden behind a typed `RESET` confirmation. It automatically takes a safety backup first, then wipes products/categories/transactions and reseeds the default categories. It does **not** touch your admin PIN or app settings. This is the only place in the app that intentionally deletes historical data - it is not part of normal day-to-day use.

Because backups are plain copies of the SQLite file, restoring never requires "translating" data - it's just swapping the file back.

---

## 6. Admin PIN

The Admin hub (shield icon, top-right) is PIN-protected. On first tap with no PIN set yet, you're asked to choose one (4-8 digits); afterward you must enter it to re-enter Admin. The PIN is hashed with PBKDF2-HMAC-SHA256 (200,000 iterations, random 16-byte salt) - never stored or logged in plain text (`utils/security.py`).

Day-to-day operations (adding products, recording sales, stock-in, adjustments, viewing products/categories/transactions/reports) are **not** PIN-gated, since gating them would slow down the core "receive stock -> sell -> stock updates" workflow the app is built around. The PIN specifically protects **Backup & Restore, Settings, and the database reset** - the operations with real risk if triggered by mistake or by someone else picking up the phone.

---

## 7. Testing Checklist

Automated (`python -m unittest discover -s tests -v`, 29 tests):

- [x] Add product creates row + `PRODUCT_CREATED` transaction
- [x] Duplicate product code rejected
- [x] Sequential auto-generated product codes (P001, P002, ...)
- [x] Increase stock updates quantity + writes `STOCK_IN`
- [x] Sell reduces stock + writes `SALE`
- [x] Selling more than available stock raises a clear error and leaves stock unchanged
- [x] Stock adjustment cannot take quantity negative
- [x] Stock adjustment requires a non-empty reason
- [x] Archive removes a product from the active list but keeps its transaction history
- [x] Restore brings an archived product back to the active list
- [x] Low-stock / out-of-stock detection and filtering
- [x] Search by name and by product code
- [x] Category delete blocked while products reference it
- [x] Category rename + duplicate-name rejection
- [x] Dashboard stats reflect same-day activity
- [x] Data persists across closing and reopening the database
- [x] Backup file is created and is restorable
- [x] Restore rejects a file that isn't a valid backup
- [x] Auto-backup runs when due, skipped when not due
- [x] PIN is hashed, never stored in plain text; verifies correctly; wrong PIN rejected
- [x] PIN format validation (4-8 digits)
- [x] Changing PIN requires the current PIN

Manual (requires running the UI - see section 3.2/3.3):

- [ ] Add 100+ products and confirm the list scrolls smoothly
- [ ] Add/rename/delete a category from the Categories screen
- [ ] Quick "+ Stock" / "- Sell" from a product card, and from Product Details
- [ ] Stock adjustment dialog with a reason, from Product Details
- [ ] Archive a product from Product Details, confirm it disappears from Products but its history remains under Admin -> Archived Products
- [ ] Restore an archived product
- [ ] Dashboard low-stock / out-of-stock counts and the "View Low Stock" shortcut
- [ ] Daily Summary for today and for a past date (via the date picker in Reports)
- [ ] CSV export for products, transactions, daily summary, category report, low-stock report - confirm files land in `exports/`
- [ ] Backup Now, then Restore From Backup, and confirm data matches
- [ ] Set an Admin PIN, back out, come back in with the correct PIN, then a wrong PIN
- [ ] Close the app (swipe away / kill process) and reopen - all data intact
- [ ] Rotate the phone screen / test on a small and a large device - layout should reflow, not clip

---

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `pip install kivy` fails with `kivy_deps.sdl2_dev` not found | Your Python version is too new for prebuilt Kivy wheels on Windows. Use Python 3.10-3.12, or test via WSL instead. |
| `buildozer android debug` fails with SDK/NDK license errors | Run `yes | ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses` inside WSL to accept licenses, then re-run the build. |
| APK installs but crashes immediately on the phone | Run `buildozer android deploy run logcat` (phone connected via USB) to see the Python traceback in the Android log. Almost always a missing requirement in `buildozer.spec`'s `requirements =` line. |
| "Not enough stock available" when you expect stock to exist | Someone else (or another screen) may have sold/adjusted it first - check Product Details -> Transaction History for the real current stock and its full audit trail. |
| Restore says "not a valid Sales Repository backup" | The chosen file isn't a real backup of this app's database (wrong file, or corrupted). Pick a file from the `backups/` list shown in Settings rather than a manually renamed file. |
| Data seems to have disappeared after a "Reset Database" | Check `backups/` for the automatic `..._pre_reset.db` safety backup taken immediately before the reset, and restore it from Settings. |
| Category won't delete | It (or an archived product) still references that category. Reassign/archive its products first, or leave the category in place - archived data is intentionally never orphaned. |

---

## 9. Future Improvement Ideas

- Barcode scanning (camera) to speed up Add Product / Sell / Stock-In on real hardware.
- True incremental pagination (`InventoryService.list_products(limit=, offset=)` already supports it) for extremely large catalogs (10,000+), rather than loading the full filtered result set into the RecycleView at once.
- Multi-currency / per-product currency override (currently a single app-wide currency symbol in Settings).
- Optional dark theme toggle (the theme is currently fixed to KivyMD's Light style).
- Encrypted backups (e.g. age/GPG-wrapping the `.db` file) for users who back up to shared storage.
- A lightweight in-app changelog/about screen showing app version and last-migration schema version.
- Role-based PINs (e.g. a "view only" PIN vs a "full admin" PIN) if the app is ever used by more than one person on the same device.

---

## Design notes / trade-offs worth knowing about

- **KivyMD 1.1.1**, not the 2.0.x development branch - far more stable buildozer track record and no breaking API churn mid-project.
- **Backups are raw `.db` file copies**, not a custom export format - simplest possible restore path, and trivially inspectable/portable.
- **Admin PIN gates Backup/Restore/Settings/Reset only**, not everyday sales operations - see section 6 for the reasoning.
- **One SQLite connection for the app's lifetime**, WAL journaling, all writes wrapped in `Database.transaction()` - matches the single-user, single-process nature of a local mobile app; no connection-pool complexity needed.
