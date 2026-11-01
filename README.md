# Energy Costs for Home Assistant

<img src="custom_components/energy_costs/brand/icon.png" alt="Energy Costs" width="96" height="96">

An independent custom integration for household electricity costs. Grid import
and export are tracked separately, with no dependency on a particular supplier
or meter manufacturer.

## Requirements

- Home Assistant **2026.1 or newer**; **2026.3 or newer** to display the bundled icon.
- A cumulative grid import sensor in Wh or kWh.
- Optionally, a separate cumulative grid export sensor in Wh or kWh.
- Recorder long-term energy statistics if you want to import historical readings.

Use cumulative meter readings, such as 1.8.0 for import and 2.8.0 for export.
Power sensors in W, daily-reset consumption sensors, and net import-minus-export
sensors are not suitable. PV self-consumption is not grid import. Sources such
as ESPHome, Shelly, Modbus, or MQTT can be used when they provide suitable sensors.

## Installation with HACS

Energy Costs is prepared for installation as a **HACS custom repository**. It is
not included in the HACS default catalog. The GitHub repository must first be
pushed and made **public** before these installation steps can work.

1. Install and configure [HACS](https://www.hacs.dev/) if needed.
2. Open **HACS** in Home Assistant.
3. Open the **⋮** menu in the upper-right corner and select **Custom repositories**.
4. Enter `https://github.com/matzem79/home-assistant-energy-costs`.
5. Select **Integration** as the repository type and click **Add**.
6. Find **Energy Costs** in HACS, open it, and download it.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**, search for
   **Energy Costs**, and enter your meters and tariffs.

HACS downloads the files; adding the integration in Home Assistant is a separate
step. See the [HACS custom repository instructions](https://hacs.dev/docs/faq/custom_repositories/).

### Updates and existing manual installations

Download updates through HACS, then restart Home Assistant. Keep the existing
Energy Costs configuration entry: deleting and recreating it starts new accounting.

If you installed manually, add this repository to HACS and download the integration
to let HACS manage the same `custom_components/energy_costs` directory. Restart
Home Assistant and keep your existing integration entry. HACS does not import
meter history; that is controlled separately in Energy Costs settings.

### Manual installation without HACS

1. Download a source archive or the manual-install ZIP from a GitHub release.
2. Copy its entire `custom_components/energy_costs` directory to
   `/config/custom_components/energy_costs`, including the `brand/` directory.
3. Restart Home Assistant.
4. Add **Energy Costs** under **Settings → Devices & services → Add integration**.

The resulting path must include `/config/custom_components/energy_costs/manifest.json`.
For updates, replace the integration files and restart; keep the existing entry.

## Configuration

| Setting | Meaning |
| --- | --- |
| Grid import counter | Cumulative imported energy in Wh or kWh |
| Grid export counter | Optional separate cumulative exported energy in Wh or kWh |
| Import price per kWh | Price in the HA currency/kWh, e.g. `0.30` for 30 cents in EUR |
| Export compensation per kWh | Earned export compensation in the HA currency/kWh |
| Monthly standing charge | Fixed monthly amount on the import side |
| Monthly import advance payment | Scheduled monthly payment to the electricity supplier |
| Monthly export credit received | Scheduled monthly payout from the export provider |
| Count monthly export credits from | Optional earliest included payout date, independent of the billing-year start |
| Valid from | Effective date for prices, standing charge, and monthly payment amounts; blank means today |
| Import billing-year start | Annual billing anchor for grid import |
| Export billing-year start | Independent annual billing anchor for grid export |
| Import historical meter data from each billing start | Reconstruct energy from each source's Recorder long-term statistics |
| Opening import/export balance | Optional balance in money at the initial tracking start |

Import and export must use different source entities. Currency is taken from
Home Assistant during setup and retained for this entry; there is no currency
conversion. Negative per-kWh prices are supported. Standing charges and monthly
payments cannot be negative. The interface includes English and German translations.

## Tariff history and backdated changes

Open **Energy Costs → Configure** to save a dated tariff. Saving the same effective
date replaces that tariff; other entries remain. The options dialog displays the
number of saved tariffs and a table of all effective dates and amounts.

- **No effective date:** applies from today at midnight in the HA time zone.
- **Future date:** the previous tariff applies until that date.
- **Past date:** recorded daily energy is recalculated using the applicable tariff.

A later tariff is never applied arbitrarily to earlier days. A backdated tariff
can only reprice energy already recorded or imported. Existing Recorder statistics
are not rewritten, so current recalculated totals may differ from older graphs.

All monetary values in a tariff share its effective date, including monthly
payments. When changing only one field, retain the correct values for the other
fields at that date. Later tariff entries retain their own amounts.

### Historical energy import

Enable **Import historical meter data from each billing start** in the options.
For example:

1. Set the import billing start to **2026-10-26**.
2. Set the export billing start to **2026-04-01**.
3. Enter prices, the standing charge, and monthly payment amounts.
4. Set **Valid from** to **2026-04-01** if these amounts have been unchanged since
   then. Import energy and standing charges still start on October 26 in this example.
5. Enable history import and save. Add further dated tariffs for subsequent changes.

This requires **long-term statistics with an energy sum** for each source. A
current meter reading or a short state history alone is not enough. Check the
sources under **Developer tools → Statistics**. Recorder must be available;
raw state histories and CSV files are not imported directly.

For each direction, existing energy is replaced by a reconstruction beginning at
its configured start date. The import uses reset-adjusted hourly sum differences
normalized to kWh and searches up to 31 days before the start for a baseline.
The remaining interval is bridged to the current raw meter reading. Local day
boundaries follow the HA time zone. Allocation within intervals is an estimate.

Completed imports are saved and are not repeated on restart or when only prices
change. Changing a source or billing start triggers a new import. Older imports
are rebuilt once when upgrading to the corrected importer introduced in 0.2.1.
Failed or incomplete imports are retried when the integration is reloaded. If no
usable statistics are available, existing live energy data is retained.

Gaps between cumulative statistics do not by themselves make the known total
incomplete. Their energy is distributed over time and flagged with
`distribution_estimated`. A long bridge to the live reading is flagged likewise.
If no baseline is available before the start, part of the period is missing. If
an interval spans the billing start, the starting reading is estimated and the
import remains incomplete. Falling sums or a reset during the live handover also
make the import incomplete.

Attributes expose the details:

| Attribute/reason | Meaning |
| --- | --- |
| `history_import` | Per-direction import status and reconstruction details |
| `tracking_since` | Actual start of accounting for this direction |
| `statistics_gaps`, `longest_gap_seconds` | Gaps in the statistics timeline |
| `estimated_start_boundary` | The meter reading at the billing start was estimated |
| `missing_start_baseline`, `missing_period_start` | The beginning of the requested period is missing |
| `decreasing_sum_or_counter_reset` | A falling sum or counter reset occurred during reconstruction/handover |
| `missing_tariff` | A price or standing-charge tariff is missing for recorded energy/time |
| `missing_payment_tariff` | No tariff is available for a scheduled payment date |
| `history_unavailable_or_incomplete` | History import is unavailable or incomplete |

Settlement sensors list reasons in `incomplete_reasons`. `period_complete` or
`complete` indicates coverage. When a whole billing period is imported, an
opening balance is not added. For a partial import, any opening balance refers
to its actual tracking start; review balances entered before enabling history import.

## Sensors

The integration creates 26 sensors on one service device:

- Imported energy: today, month, import billing year, total.
- Exported energy: today, month, export billing year, total.
- Import energy costs: today, month, import billing year, total.
- Earned export compensation: today, month, export billing year, total.
- Accrued standing charges: today, month, import billing year, total.
- For each independent billing year: scheduled payments, balance, and status.

**Import cost sensors exclude standing charges**, including the total and
billing-year sensors. Standing charges have separate sensors. The import balance
subtracts both energy costs and standing charges from advance payments.

**Total** means since tracking began, including imported history if enabled,
rather than the physical meter's lifetime total. The first reading establishes
a baseline. Unavailable readings do not become zero. Counter resets establish a
new baseline; unknown energy around a reset or meter replacement is not guessed.

Days, months, and billing years follow the HA time zone. A timer updates
time-dependent values even without meter changes. Energy and balances are stored
in HA `.storage` independently of entity state. Normal shutdown/unload saves
explicitly; an abrupt power loss may lose up to five seconds of pending changes.

## Standing charges and scheduled payments

Standing charges accrue over time: the monthly charge is divided by the month's
calendar days and prorated within the current day. A fully tracked month adds
exactly one monthly charge, including leap years and daylight-saving changes.
Charges begin at the import tracking start, including any imported history.

Monthly advances and export payouts are booked **in full**, on the day of the
month specified by the corresponding billing-year start. A start on April 15
means payments on the 15th of every month. Dates missing from a month are clamped
to its last day. A billing year contains at most twelve monthly payments.

Use **Count monthly export credits from** to exclude earlier payouts without
changing the billing year. For example, a billing start of **2026-01-01**, a
monthly payout of **EUR 10**, and a payout start of **2026-04-01** result in
**EUR 80** paid from April through November, rather than EUR 110.

This optional date is a lower bound on the existing payment dates; it does not
change their day of the month. It is independent of a tariff's effective date.
Leaving it blank retains the original behavior. It does not change energy,
earned compensation, or the billing-year start, and does not record a separate
settlement payment for an earlier invoice.

Settlement sensor attributes include `tariff_count`, `tariffs`, `payment_start`,
and `payment_schedule`. The schedule lists each included date, amount, and the
tariff effective date used. Inspect them under **Developer tools → States**.

**Scheduled payments are assumed to have been made.** There is no bank connection,
missed-payment detection, or individual payment entry.

## Separate balances

```text
Import balance = opening balance + advance payments − import energy costs − standing charges
Export balance = opening balance + earned compensation − monthly payouts received
```

| Balance | Import | Export |
| --- | --- | --- |
| Positive | Credit owed to you | Earned compensation still owed to you |
| Negative | Expected additional payment | Expected repayment of excess payouts |
| Near zero | Balanced | Balanced |

Balances describe recorded costs/earnings and scheduled payments to date, not a
forecast of the year-end result. The import and export billing years may start
on different dates and roll over independently. An opening balance applies only
to the initial partial billing year and is not carried into the next year; the
previous year's settlement is assumed to have been handled separately. The
integration does not make payments.

An opening balance is money, not a meter reading or monthly payment. Without
historical data or a known opening balance, a partial year is marked incomplete.
For example, EUR 50 credit when tracking starts means an opening import balance
of `50`. New costs and payments are added from that point. This does not recreate
unknown earlier energy consumption.

## Icon

The integration bundles `brand/icon.png` (256 × 256) and `brand/icon@2x.png`
(512 × 512), suitable for light and dark interfaces. Local brand images require
**HA 2026.3 or newer**; earlier supported versions can run the integration but do
not automatically display the bundled icon.

After updating, restart HA and fully reload the browser (macOS: **⌘⇧R**) or try a
private window. Do not delete the integration to update its icon. Check
`/config/custom_components/energy_costs/brand/icon.png` if the icon is missing.
Icon display has been confirmed after a manual HA installation.

The vector source is [docs/icon.svg](docs/icon.svg). Run
`python3 scripts/build_brand.py` to regenerate the SVG and PNGs without additional
packages. Code and artwork are covered by the [MIT license](LICENSE).
See [Home Assistant brand image documentation](https://contributors.home-assistant.io/core/integrations/brands/).

## Accuracy and limitations

Energy between changing readings is distributed over local days in proportion
to elapsed time. Sparse updates spanning midnight therefore introduce estimates.
Frequent cumulative readings improve time allocation. Missing tariff coverage is
reported through `unpriced_energy_kwh` or `unpriced_days` and `cost_complete`.
Settlement attributes also include `actual`, `advances`, `opening_balance`, and
`cycle_start`.

A supplier may use different rounding, dates, payment plans, or billing rules.
This is an ongoing overview, not an official bill. The integration does not
change source entities or perform transfers or physical actions.

## Development and publishing

Current integration version: **0.2.3**.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_release.py
```

67 isolated tests cover meters, units, tariffs, historical import, persistence,
calendar boundaries, standing charges, independent billing years, balances,
payment dates, configuration flows, and sensor attributes. They use HA boundary
doubles; a full HA/hassfest run and a live HACS installation remain outstanding.
Manual HA feedback is available, including confirmation of the icon.

The ZIP builder writes `dist/energy-costs-0.2.3.zip`. GitHub Actions run tests and
build the package on pushes and pull requests. A version tag creates a **draft**
GitHub release with the manual-install ZIP. HACS installs the integration from
the repository/tag layout, not from that ZIP.

See [Publishing to GitHub and HACS](docs/PUBLISHING.md) for authentication,
creating the public repository, the first push, and releasing a version.
Repository preparation does not itself publish to GitHub or add the project to
the HACS default catalog.
