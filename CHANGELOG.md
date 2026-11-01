# Changelog

## 0.2.3 — prepared locally

- Bundle an original integration icon as transparent 256/512-pixel PNGs under `brand/`, supported by HA 2026.3 and newer.
- Include editable SVG artwork and a reproducible icon generator with no additional packages.
- Document icon display and clarify that import energy costs exclude standing charges.
- Add the MIT license, publishing instructions, and a clean manual-install ZIP builder.
- Add a tag workflow that validates the version and tests before creating a draft GitHub release with the installation package.
- Ignore local macOS metadata and build outputs in Git.
- Confirm icon display after manual HA installation; document browser refresh and updating without deleting the integration.
- Prepare an HTTPS remote and GitHub CLI authentication for the first push.
- Translate the README, changelog, and publishing guide into English.
- Document HACS custom-repository installation, updates, and migration from manual installation.
- Enable README rendering in HACS metadata and document the public-repository requirement.
- 67 isolated tests passed; no GitHub push, release, or live HACS installation has been confirmed by this preparation.

## 0.2.2 — prepared locally

- Add an optional first export payout date independent of the billing year and tariff effective date.
- A January billing-year start with EUR 10 payouts beginning in April gives EUR 80 through November; earned annual compensation remains independent.
- Show the tariff count and complete tariff table in the options dialog.
- Expose saved tariffs and included payment dates, amounts, and effective tariff dates on settlement sensors.
- 67 isolated tests passed; full live HA verification remained outstanding.

## 0.2.1 — prepared locally

- Search up to 31 days before the billing start for a baseline instead of only two hours.
- Preserve known cumulative energy across statistics gaps and flag its time allocation as estimated.
- Explicitly mark an estimated opening meter reading at the billing boundary as incomplete.
- Add diagnostics for missing baselines, tariffs, payment tariffs, and counter resets.
- Rebuild older imports once after updating while retaining protection against duplicate energy on restart.
- 61 isolated tests passed, including a multi-day gap spanning April 1; live verification remained outstanding.

## 0.2.0 — prepared locally

- Add optional historical energy import from Recorder long-term statistics, using independent import and export billing starts.
- Reconstruct reset-adjusted hourly energy in kWh and bridge to the current meter reading.
- Persist separate tracking starts for energy costs, standing charges, scheduled payments, and balances.
- Expose import status and missing coverage as sensor attributes; retain live data if no usable statistics are available.
- Persist completed imports so restarts do not repeat them; retain backdated tariff recalculation.
- 56 isolated tests passed; live verification remained outstanding.

## 0.1.0 — prepared locally

- Add a standalone Home Assistant integration with UI setup.
- Track grid import and export independently.
- Support import prices, export compensation, and monthly standing charges.
- Maintain dated tariff history with backdated updates.
- Track separate monthly import advances and export payouts.
- Support independent annual billing periods with balances and status.
- Allow opening balances when starting during an existing billing year.
- Provide 26 sensors, persistent accounting, and English/German translations.
- 44 isolated tests passed; live HA verification remained outstanding.
