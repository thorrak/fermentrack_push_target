from __future__ import unicode_literals

from django.db import models
from django.utils import timezone

import os.path, csv, logging
import datetime, pytz
from fermentrack_push_target import settings

logger = logging.getLogger(__name__)


class UpstreamFermentrackInstallation(models.Model):
    class Meta:
        verbose_name = "Upstream Fermentrack Installation"
        verbose_name_plural = "Upstream Fermentrack Installations"

    name = models.CharField(max_length=48, help_text="Unique name for this data source", unique=True)
    api_key = models.CharField(max_length=256, help_text="API key required to be provided by data source (optional)")
    last_checked_in = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.name


class BrewPiDevice(models.Model):
    # In truth, the only thing that you need for this model is the ID of the device and the linked Fermentrack
    # installation. Everything else we are provided. (Even name, as it can change)
    remote_id = models.IntegerField()
    fermentrack_install = models.ForeignKey(to=UpstreamFermentrackInstallation, on_delete=models.CASCADE)

    name = models.CharField(max_length=48, help_text="Name for this device", default="", blank=True)

    # How the rest of the data is handled should depend on how you want your app to work. For this app, we're going to
    # save the latest data point to the model as well as log it to a CSV.
    TEMP_FORMAT_CHOICES = (('C', 'Celsius'), ('F', 'Fahrenheit'))
    CONTROL_MODE_CHOICES = (
        ('u', 'Unknown'),  # This is used internally if we don't have a mode provided
        ('o', 'Off'),
        ('b', 'Beer Constant'),
        ('f', 'Fridge Constant'),
        ('p', 'Beer Profile')
    )

    latest_temp_format = models.CharField(max_length=1, choices=TEMP_FORMAT_CHOICES, default='C',
                                          help_text="Temperature units")
    latest_beer_temp = models.DecimalField(max_digits=13, decimal_places=10, null=True,
                                           help_text="Latest temperature from the beer sensor")
    latest_fridge_temp = models.DecimalField(max_digits=13, decimal_places=10, null=True,
                                             help_text="Latest temperature from the fridge sensor")
    latest_room_temp = models.DecimalField(max_digits=13, decimal_places=10, null=True,
                                           help_text="Latest temperature from the room sensor")
    latest_control_mode = models.CharField(max_length=1, choices=CONTROL_MODE_CHOICES, default='u',
                                           help_text="Current temperature control mode")
    latest_gravity = models.DecimalField(max_digits=4, decimal_places=3, null=True,
                                         help_text="Current specific gravity (if applicable)")

    def __str__(self):
        return self.name

    def csv_filename(self) -> str:
        # Return the formatted filename for the CSV file we'll be logging to
        return self.fermentrack_install.name + " - BrewPi " + self.remote_id + ".csv"

    def _csv_column_headers(self) -> list:
        # This returns a simple list of the columns in the order they appear in the CSV file
        headers = ['log_time', 'beer_temp', 'fridge_temp', 'room_temp', 'temp_format', 'control_mode', 'gravity']
        return headers

    def _csv_data(self) -> list:
        # Whereas csv_column_headers() returns a list of the column headers, csv_data_list returns a list containing
        # the data we actually want logged to the CSV.
        utc_tz = pytz.timezone("UTC")
        log_time = datetime.datetime.now(utc_tz).strftime('%Y/%m/%d %H:%M:%SZ')

        csv_data = [
            log_time,
            self.latest_beer_temp,
            self.latest_fridge_temp,
            self.latest_room_temp,
            self.latest_temp_format,
            self.latest_control_mode,
            self.latest_gravity,
        ]
        return csv_data

    def save_latest_to_csv(self):
        # After the object has the "latest_" fields updated, let's save them all to a file.

        file_path = os.path.join(settings.BASE_DIR, settings.DATA_ROOT, self.csv_filename())

        # First, check if the CSV file exists. If it doesn't, create it & add the column headers.
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(self._csv_column_headers())

        with open(file_path, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._csv_data())


class GravitySensor(models.Model):
    remote_id = models.IntegerField()
    fermentrack_install = models.ForeignKey(to=UpstreamFermentrackInstallation, on_delete=models.CASCADE)

    name = models.CharField(max_length=48, help_text="Name for this device", default="", blank=True)

    # How the rest of the data is handled should depend on how you want your app to work. For this app, we're going to
    # save the latest data point to the model as well as log it to a CSV.
    SENSOR_TILT = 'tilt'
    SENSOR_MANUAL = 'manual'
    SENSOR_ISPINDEL = 'ispindel'
    SENSOR_TYPE_CHOICES = (
        (SENSOR_TILT, 'Tilt Hydrometer'),
        (SENSOR_ISPINDEL, 'iSpindel'),
        (SENSOR_MANUAL, 'Manual'),
    )

    TEMP_FORMAT_CHOICES = (('C', 'Celsius'), ('F', 'Fahrenheit'))

    sensor_type = models.CharField(max_length=10, default=SENSOR_MANUAL, choices=SENSOR_TYPE_CHOICES,
                                   help_text="Type of gravity sensor used")
    latest_gravity = models.DecimalField(max_digits=4, decimal_places=3, null=True,
                                         help_text="Current specific gravity")
    latest_temp = models.DecimalField(max_digits=13, decimal_places=10, null=True,
                                      help_text="Latest temperature from the sensor")
    latest_temp_format = models.CharField(max_length=1, choices=TEMP_FORMAT_CHOICES, default='C',
                                          help_text="Temperature units")

    def __str__(self):
        return self.name

    def csv_filename(self) -> str:
        # Return the formatted filename for the CSV file we'll be logging to
        return self.fermentrack_install.name + " - Gravity " + self.remote_id + ".csv"

    def _csv_column_headers(self) -> list:
        # This returns a simple list of the columns in the order they appear in the CSV file
        headers = ['log_time', 'gravity', 'temp', 'temp_format']
        return headers

    def _csv_data(self) -> list:
        # Whereas csv_column_headers() returns a list of the column headers, csv_data_list returns a list containing
        # the data we actually want logged to the CSV.
        utc_tz = pytz.timezone("UTC")
        log_time = datetime.datetime.now(utc_tz).strftime('%Y/%m/%d %H:%M:%SZ')

        csv_data = [
            log_time,
            self.latest_gravity,
            self.latest_temp,
            self.latest_temp_format,
        ]
        return csv_data

    def save_latest_to_csv(self):
        # After the object has the "latest_" fields updated, let's save them all to a file.

        file_path = os.path.join(settings.BASE_DIR, settings.DATA_ROOT, self.csv_filename())

        # First, check if the CSV file exists. If it doesn't, create it & add the column headers.
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                writer = csv.writer(f)
                writer.writerow(self._csv_column_headers())

        with open(file_path, 'a') as f:
            writer = csv.writer(f)
            writer.writerow(self._csv_data())