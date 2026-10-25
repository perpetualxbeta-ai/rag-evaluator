# Kestrel K2 Maintenance Guide

> **Note:** Fictional sample data for rag-evaluator.

Following this schedule keeps Kestrel K2 robots reliable and is a condition of the warranty (see Warranty and Support). Daily and weekly tasks can be done by certified operators. Tasks that require opening the robot's covers must be carried out by a technician with the Kestrel Maintenance Certification, after the robot has been locked out as described in the Safety Procedures.

Operating hours are counted by HalcyonOS and shown for each robot in Halcyon Fleet.

## Daily

- Walk around the robot and check for visible damage, loose parts, or debris wrapped around the wheels.
- Clean both laser scanner windows and the depth camera lens. Use a lint-free cloth and isopropyl alcohol. **Do not use ammonia-based glass cleaners**: they leave a film that degrades the scanners' range.
- Check that all four emergency stop buttons are undamaged and spring back after being released.

## Weekly

- Inspect the two drive wheels for cuts, flat spots, or embedded objects such as staples and stretch-wrap.
- Wipe down the DockPoint charger contacts with a dry cloth.
- Test one emergency stop button on each robot, rotating through the four buttons from week to week.

## Every 500 operating hours

- Measure the drive wheel tread. Replace both drive wheels if the tread is thinner than 4 mm; wheels are always replaced as a pair.
- Check the torque of the drive wheel bolts.
- Inspect the caster wheels for play or noise.

## Every 2,000 operating hours

- Replace all four caster wheels.
- Run the brake test from the robot's service menu. The robot must stop from 1.0 m/s, carrying its full 300 kg payload, within 0.4 m.
- Verify the calibration of the safety laser scanners using the Halcyon calibration target.

A robot that fails the brake test or the scanner calibration must be taken out of service until it has been repaired.

## Battery health

From HalcyonOS 3.3, every robot reports its battery state of health (SoH) to Halcyon Fleet, and Halcyon Fleet sends an alert when SoH drops below 75%. Plan a replacement at that point. A battery must be replaced once its SoH falls below 70%, because below that level the robot can no longer complete a full shift between opportunity charges.

Robots running HalcyonOS 3.2 or earlier do not report SoH. On those robots, have a technician measure SoH manually every 1,000 operating hours, or update the firmware.

Battery replacement is a technician task. Used batteries must be returned to Halcyon for recycling; do not dispose of them as general waste.

## Firmware updates

Keep robots on a current version of HalcyonOS. Updates are installed over the air from Halcyon Fleet, one robot at a time, while the robot is docked. Halcyon support only covers robots running HalcyonOS 3.1 or later.

## Spare parts

Use only genuine Halcyon spare parts. Third-party wheels, batteries, or scanners void the warranty for the affected component and can compromise the safety functions.
