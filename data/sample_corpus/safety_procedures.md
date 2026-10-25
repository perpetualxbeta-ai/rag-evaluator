# Kestrel Safety Procedures

> **Note:** This is fictional sample data for rag-evaluator. It is not real safety guidance for any product.

These procedures apply to every site where Kestrel K2 robots operate. Site managers are responsible for making sure that everyone who works near the robots has read them.

## Operator certification

Anyone who operates, loads, or works alongside Kestrel robots must complete the **Kestrel Operator Certification**. The certification is a two-hour course, delivered on site by Halcyon trainers during deployment and afterwards through an online module. It covers emergency stops, shared zones, loading limits, and what to do after a collision. Certification is valid for two years and must then be renewed.

Visitors who have not been certified may enter areas with robots only when accompanied by a certified operator.

## Emergency stops

Every Kestrel K2 has four red emergency stop buttons, one on each corner of the chassis. Pressing any of them cuts power to the drive motors immediately and engages the brakes. The robot will not move again until the button has been released by twisting it **and** an operator has confirmed the restart in Halcyon Fleet or on the robot's touch panel.

Halcyon Fleet also has a site-wide stop that halts every robot at once. Use it if there is a fire, a medical emergency, or a person lying on the floor in a robot area.

## Shared zones and safe distance

A shared zone is any area where robots and people work side by side, such as picking stations and packing areas. In shared zones:

- Robots travel at the shared-zone speed limit, which is 1.2 m/s by default and never more than 1.5 m/s (see the Technical Specifications).
- People should keep at least 0.5 m away from a moving robot and must never step in front of one to stop it.
- Robots must not carry loads that overhang the chassis by more than 100 mm, because overhangs are outside the scanners' protective field.

Each robot's safety laser scanners maintain a protective field around it. If a person or object enters the field, the robot slows down; if the object comes closer, the robot performs a safety-rated stop. A robot that stops repeatedly in the same place usually indicates a blocked aisle or a dirty scanner window, and should be reported to the site's Halcyon contact.

## Loading

Never load a robot beyond its 300 kg maximum payload. Loads must be centred on the top plate or in an approved cart. Robots detect overweight loads and refuse to move, but operators should not rely on this check.

## Maintenance lockout

Before any maintenance work, the robot must be locked out:

1. Send the robot to a maintenance bay using Halcyon Fleet, and set it to *Maintenance* mode so it receives no new tasks.
2. Press an emergency stop button.
3. Switch off the main power switch under the rear cover and attach a personal padlock.

Only technicians who hold the separate Kestrel Maintenance Certification may open the robot's covers.

## Battery incidents

The K2's LiFePO4 battery is much less prone to thermal runaway than other lithium chemistries, but damaged batteries can still overheat. If a robot gives off smoke, a burning smell, or a hissing sound:

1. Trigger the site-wide stop in Halcyon Fleet.
2. Evacuate the area and call the local emergency services.
3. Do not touch or try to move the robot.

After any battery incident, contact Halcyon support. Damaged batteries must be handled only by Halcyon technicians.
