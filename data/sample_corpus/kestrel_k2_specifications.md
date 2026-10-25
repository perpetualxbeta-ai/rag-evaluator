# Kestrel K2 Technical Specifications

> **Note:** The Kestrel K2 is a fictional product used as sample data for rag-evaluator.

The Kestrel K2 is Halcyon Robotics' second-generation autonomous mobile robot. It was launched in March 2025 with HalcyonOS 3.0 and replaces the Kestrel K1. It is designed to move carts, roll cages and pallets of up to 300 kg between storage, picking and shipping areas.

## Physical characteristics

| Property | Value |
|---|---|
| Dimensions (L × W × H) | 1100 × 750 × 350 mm |
| Weight (without payload) | 165 kg |
| Maximum payload | 300 kg |
| Ingress protection | IP54 |
| Operating temperature | 0 °C to 40 °C |
| Maximum floor gradient | 3% |
| Maximum gap or threshold | 20 mm |

The IP54 rating means the K2 is protected against dust and water splashes. It is suitable for ambient and chilled warehouses but not for freezer areas, which fall below its 0 °C minimum operating temperature.

## Motion

The K2 has a top speed of 2.0 m/s in open areas. In shared zones, where robots and people work side by side, the default speed limit is 1.2 m/s. From HalcyonOS 3.2 onwards the shared-zone limit can be configured anywhere between 0.8 m/s and 1.5 m/s per zone, but it can never exceed 1.5 m/s.

The robot uses a differential drive with two powered drive wheels and four passive caster wheels. It can turn on the spot, which lets it operate in aisles as narrow as 1.0 m.

## Sensors and navigation

- Two safety-rated laser scanners (lidar), mounted on opposite corners, each with a 270° field of view, together giving full 360° coverage.
- A forward-facing 3D depth camera for detecting overhanging obstacles such as forklift tines and shelf edges.
- Wheel encoders and an inertial measurement unit for odometry.

Navigation is natural-feature based: the robot localises itself against a map of the building's walls, racks and columns, so no floor markers, reflectors or tape are needed.

## Battery and charging

| Property | Value |
|---|---|
| Chemistry | Lithium iron phosphate (LiFePO4) |
| Nominal voltage | 48 V |
| Capacity | 2.4 kWh |
| Typical runtime | 10 hours |
| Charging | DockPoint charger, 0–80% in 45 minutes |
| Rated cycle life | 3,000 full charge cycles |

The K2 supports opportunity charging: whenever it is idle for a few minutes, Halcyon Fleet can send it to a DockPoint for a short top-up. With opportunity charging enabled, most sites can run K2 robots around the clock without swapping batteries.

The battery's state of health (SoH) is reported to Halcyon Fleet from HalcyonOS 3.3 onwards. A battery should be replaced when its SoH falls below 70%; see the Maintenance Guide.

## Connectivity

The K2 connects to Halcyon Fleet over Wi-Fi 6. A 5G modem is available as a factory-fitted option for sites with poor Wi-Fi coverage. If the connection to Halcyon Fleet is lost, the robot finishes its current task and then stops at the nearest safe waiting point until the connection returns.
