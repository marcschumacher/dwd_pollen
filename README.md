# DWD pollen sensor for Home Assistant

[Home Assistant](https://www.home-assistant.io) component to retrieve Pollen data from the DWD (Deutscher Wetterdienst, 
Germany)


## Installation

1. Either checkout this repository using `git clone git@github.com:marcschumacher/dwd_pollen.git` or download a specifc 
   version from the [release page](https://github.com/marcschumacher/dwd_pollen/releases).
2. Copy the created folder `dwd_pollen` to your configuration folder under `<config>/custom_components/`.
3. Install the required dependencies using pip3. `cd` to the `dwd_pollen` folder and execute the following command:
   ```
   pip3 install -r requirements.txt
   ```
4. Now you are done. Proceed with configuring the component.


## Configuration

To be able to use this component, add the following configuration to your `configuration.yaml`:
```
sensor:
  - platform: dwd_pollen
    partregion_ids:
      - 41
      - 42
    include_pollen:
      - birke
      - erle
    include_days:
      - today
```

Here is a description of the values possible:

Parameter      | Default values | Possible values                                                                                                                                  | Description                                                | 
---------------|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
partregion_ids | no default     | [API description](https://opendata.dwd.de/climate_environment/health/alerts/Beschreibung_pollen_s31fg.pdf) (search for partregion_id in the PDF) | Region for which the date shall be retrieved.              |
include_pollen | all possible   | `birke`, `graeser`, `esche`, `erle`, `hasel`, `beifuss`, `ambrosia`, `roggen`                                                                    | List of pollens to retrieve and provide information about. |
include_days   | all possible   | `today`, `tomorrow`, `dayafter_tomorrow`                                                                                                         | Days to include                                            |


## Sensors

Per default every 15 minutes new values are retrieved from the DWD.

Two groups of sensors are created: value sensor that contain the actual values and statistical sensors which return the 
average, maximum and minimum values calculated over all specified pollen types.

### Value sensors

The value sensors have the following format: `sensor.dwd_pollen_<partregion_id>_<day>_<pollen type>`, e.g. 
`sensor.dwd_pollen_41_today_ambrosia`.

The value of this sensor is an integer between `0-6`. Basically the values are normalized from the input values 
delivered by DWD to make it easier to calculate with it. The following table describes which values are what:

DWD | Sensor | Meaning (in German)
----|--------|-------------------------------
0   | 0      | keine Belastung
0-1 | 1      | keine bis geringe Belastung
1   | 2      | geringe Belastung
1-2 | 3      | geringe bis mittlere Belastung
2   | 4      | mittlere Belastung
2-3 | 5      | mittlere bis hohe Belastung
3   | 6      | hohe Belastung

The following attributes are provided (default attributes excluded):

Attribute           | Example                     | Description 
--------------------|-----------------------------|-------------------------------------------------------------------------
attribution         | Data provided by DWD        | Data provider (currently fixed value)
last_updated        | 2019-05-16T11:00:00         | Time when the provided information was updated by the DWD
region_name         | Nordrhein-Westfalen         | Region name
partregion_name     | Rhein.-Westfäl. Tiefland    | Subregion name
original_value      | 0-1                         | Original value retrieved from DWD (see table above)
description         | keine bis geringe Belastung | Human readable text (in German) describing the severity of the pollution 

### Statistical sensors

Statistical sensors have the following format: `sensor.dwd_pollen_<partregion id>_<day>_<stat type>`, e.g. 
`sensor.dwd_pollen_41_today_avg`.

Statistics are always calculated using the values for a specific day for the specified pollen types. Following types 
are supported:

Type | Description
-----|------------
min  | Minimum
max  | Maximum
avg  | Average

Be aware that the average value might not be an integer, but a floating value.

The following attributes are provided (default attributes excluded):

Attribute           | Example                     | Description 
--------------------|-----------------------------|-------------------------------------------------------------------------
attribution         | Data provided by DWD        | Data provider (currently fixed value)
last_updated        | 2019-05-16T11:00:00         | Time when the provided information was updated by the DWD
region_name         | Nordrhein-Westfalen         | Region name
partregion_name     | Rhein.-Westfäl. Tiefland    | Subregion name
description         | keine bis geringe Belastung | Human readable text (in German) describing the severity of the pollution 
