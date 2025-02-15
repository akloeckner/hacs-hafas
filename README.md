# HAFAS (HaCon Fahrplan-Auskunfts-System)

[![validate with hassfest](https://img.shields.io/github/actions/workflow/status/akloeckner/hacs-hafas/hassfest.yaml?label=validate%20with%20hassfest)](https://github.com/akloeckner/hacs-hafas/actions/workflows/hassfest.yaml)
[![validate with HACS action](https://img.shields.io/github/actions/workflow/status/akloeckner/hacs-hafas/hassfest.yaml?label=validate%20with%20HACS%20action)](https://github.com/akloeckner/hacs-hafas/actions/workflows/hacs.yaml)
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/akloeckner/hacs-hafas/latest)](https://github.com/akloeckner/hacs-hafas/compare/...master)
[![Number of installations](https://img.shields.io/badge/dynamic/json?label=installations&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.hafas.total)](https://analytics.home-assistant.io/custom_integrations.json)

[![Open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=akloeckner&repository=hacs-hafas&category=transport)
[![Show this integration in your Home Assistant.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=hafas)

A custom component for Home Assistant providing a client for the HAFAS API.
It can be used to retrieve connection data for a number of public transport companies in Europe.

Credit goes to [@kilimnik](https://github.com/kilimnik) and [pyhafas](https://github.com/FahrplanDatenGarten/pyhafas).

## Sensor data

Once configured, this integration provides a sensor to show the next connections between two stations.

The `state` of the sensor is the `timestamp` of the next non-cancelled departure including delay. This allows to use the `state` programmatically, e.g., to compute a `timedelta` from it. Also, the sensor will be shown natively in Lovelace as a relative time, such as "in 5 minutes".

The `attributes` will contain the following additional data:
* `connections`: a list of all connections retrieved (see below)
* plus all information from the first non-canceled connection, except its list of `legs`

**Note**: The `connections` attribute is not recorded in history, because it contains a lot of data.
And we don't want to bloat your home assistant database.

Each entry in the `connections` list contains the following data:
* `origin`: name of origin station 
* `departure`: timestamp of planned departure 
* `delay`: timedelta of departure delay 
* `destination`: name of destination station 
* `arrival`: timestamp of planned arrival 
* `delay_arrival`: timedelta of arrival delay 
* `transfers`: number of legs minus one
* `duration`: timedelta from departure to arrival
* `canceled`: Boolean, `true` if any leg is canceled else `false`
* `ontime`: Boolean, `true` if zero departure delay else `false`
* `products`: comma-separated list of line names
* `legs`: list of legs with more detailed information

Each connection can consist of multiple legs (different trains with transfers in between).
A leg contains the following data:
* `origin`: name of origin station
* `departure`: timestamp of planned departure
* `platform`: departure platform
* `delay`: timedelta of departure delay
* `destination`: name of destination station 
* `arrival`: timestamp of planned arrival 
* `platform_arrival`: arrival platform 
* `delay_arrival`: timedelta of arrival delay
* `mode`: transport mode such as `train`
* `name`: name of transport line such as `RE123`
* `canceled`: Boolean, if this leg is canceled
* `distance`: walking distance if any (only walking legs)
* `remarks`: list of strings
* `stopovers`: list of station names

## Usage examples of attribute data in templates

Generate an output as in the old `db` integration, e.g., `11:11 + 11`:
```python
{%- set departure = state_attr('sensor.koln_hbf_to_frankfurt_main_hbf', 'departure') | as_local %}
{%- set delay = state_attr('sensor.koln_hbf_to_frankfurt_main_hbf', 'delay') | as_timedelta %}
{{- departure.strftime('%H:%M') }}
{%- if delay -%}
  {{- ' + ' ~ (delay.total_seconds() // 60) | int -}}
{%- endif -%}
```

While the main entity state will show as relative time (e.g. `in 12 minutes`) in your dashboard automatically, you might want to show other departures as relative time, too:
```python
{% set departure = states.sensor.kobenhavn_h_to_malmo_c.attributes.connections[0].departure
                 + states.sensor.kobenhavn_h_to_malmo_c.attributes.connections[0].delay
                   | as_timedelta %}

{% if departure > now() %}
  in {{ time_until(departure) }}
{% else %}
  too late
{% endif %}
```

Only retrieve the planned departure `datetime` objects of all non-canceled connections:
```python
{{ state_attr('sensor.koln_hbf_to_frankfurt_main_hbf', 'connections')
   | rejectattr('canceled')
   | map(attribute='departure')
   | list }}
```


