# HalcyonOS Release Notes

> **Note:** Fictional sample data for rag-evaluator.

HalcyonOS is the firmware that runs on Kestrel robots. Updates are delivered over the air through Halcyon Fleet. This page covers the HalcyonOS 3.x series, which shipped with the Kestrel K2.

## HalcyonOS 3.3.2 — June 2026

**Fixes**
- Fixed an issue where battery state-of-health readings could briefly drop by several percentage points after a firmware update, causing false low-SoH alerts in Halcyon Fleet.
- Improved reconnection to Wi-Fi 6 access points that use band steering.

## HalcyonOS 3.3 — April 2026

**New**
- **Battery health telemetry.** Robots now report battery state of health (SoH) to Halcyon Fleet. Halcyon Fleet raises an alert when SoH drops below 75%.
- **Predictive maintenance alerts.** Halcyon Fleet now warns when a robot is within 50 operating hours of a scheduled maintenance task (500-hour or 2,000-hour service).
- Brake test results from the 2,000-hour service are now stored in Halcyon Fleet and can be exported as maintenance records for warranty claims.

**Changes**
- Opportunity charging now prefers the DockPoint charger with the shortest queue, not the nearest one.

## HalcyonOS 3.2 — November 2025

**New**
- **Configurable shared-zone speed.** Site administrators can set the shared-zone speed limit per zone, between 0.8 m/s and 1.5 m/s. Earlier versions used a fixed limit of 1.2 m/s, which remains the default.
- Overhanging-load detection: the depth camera now flags loads that overhang the chassis by more than 100 mm, and the robot refuses to depart until the load is corrected.

**Fixes**
- Reduced unnecessary safety stops caused by reflective floor tape.

## HalcyonOS 3.1 — June 2025

**New**
- **Multi-floor operation.** Robots can call and ride freight elevators that are integrated with Halcyon Fleet, so one fleet can serve several floors of a building.
- Site-wide stop button in Halcyon Fleet.

**Changes**
- HalcyonOS 3.1 is the minimum version supported by Halcyon support. Robots on 3.0 should be updated.

## HalcyonOS 3.0 — March 2025

Initial release for the Kestrel K2.

- Natural-feature navigation using two 270° safety laser scanners and a forward-facing depth camera.
- Opportunity charging on DockPoint chargers.
- Fixed shared-zone speed limit of 1.2 m/s.

## Update policy

Each minor version (for example 3.2) receives bug fixes and security patches for 12 months after its successor is released. Halcyon recommends that sites stay on the latest minor version.
