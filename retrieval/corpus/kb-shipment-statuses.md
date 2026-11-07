# Tracking a shipment and reading delivery statuses

## Statuses

- Booked: the carrier has accepted the shipment but not collected it.
- In transit: the carrier has collected it. The delivered date is still empty.
- Out for delivery: on the vehicle for delivery today.
- Delivered: the customer has signed for it. The delivered date is filled in.
- Failed attempt: nobody was available to receive it. The carrier tries again the next business day, up to 3 attempts.

## Finding a shipment

Search by order number in the ERP's Logistics module. Each shipment shows its carrier, ship date, promised date and delivered date.

## Is it late?

Compare the delivered date with the promised date. A shipment that is still in transit after its promised date will be late, but it only counts in the late rate once it is delivered.
