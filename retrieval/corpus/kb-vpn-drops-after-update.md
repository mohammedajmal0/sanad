# VPN disconnects every few minutes after the GlobalConnect 6.2 update

## Symptoms

Since Monday 19 October 2026, users working from home report that the VPN connects normally but drops every few minutes, then reconnects by itself. Teams calls freeze and ERP sessions time out. Users in the office are not affected.

## Cause

The GlobalConnect client updated itself to version 6.2.0 on Monday 19 October 2026. Version 6.2.0 turns on a new setting called Adaptive MTU. Many home routers drop the larger packets it sends, so the tunnel breaks and rebuilds every few minutes.

## Fix

Install the GlobalConnect 6.2.1 hotfix from the Software Center. It turns Adaptive MTU off by default. Restart the laptop after installing.

## Workaround if the hotfix cannot be installed

1. Open GlobalConnect, then Settings, then Advanced.
2. Turn off Adaptive MTU and set the MTU to 1380.
3. If the drops continue, change the protocol from UDP to TCP 443.

## For the service desk

Link every ticket with these symptoms to incident INC-2026-1019 and send the customer this article. Do not reinstall the client or reset the user's password: neither fixes the problem.
