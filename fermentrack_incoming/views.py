from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import render_to_response, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from . import forms

import json, datetime, pytz, os, logging, pprint, decimal

from fermentrack_incoming.models import UpstreamFermentrackInstallation, BrewPiDevice, GravitySensor
import fermentrack_push_target.settings as settings

logger = logging.getLogger(__name__)


# Siteroot is a lazy way of determining where to direct the user when they go to http://devicename.local/
def siteroot(request):
    # For this demo, the "root" page just lists the upstream Fermentrack installations that we know about.

    fermentrack_installations = UpstreamFermentrackInstallation.objects.all()

    return render(request, template_name="siteroot.html",
                  context={'fermentrack_installations': fermentrack_installations})


def add_fermentrack_install(request):
    # add_fermentrack_install allows the user to create an object representing an upstream installation of Fermentrack
    # which will subsequently push data to this script. The upstream installation identifies itself by an "API key"
    # which should only be known to the upstream installation & this script.

    if request.POST:
        # If the call to this view was made as a result of a form being submitted, then let's attempt to load & validate
        # the form data.
        form = forms.FermentrackInstallationForm(request.POST)
        if form.is_valid():
            # Since the form was valid, we'll create the new UpstreamFermentrackInstallation & display a message
            new_install = UpstreamFermentrackInstallation(
                name=form.cleaned_data['name'],
                api_key=form.cleaned_data['api_key'],
            )

            new_install.save()

            messages.success(request, u'Installation {} Added.<br>Data will appear as it is pushed from Fermentrack with the appropriate API key'.format(new_install))
            return redirect("siteroot")
        else:
            # If the submitted form wasn't valid, then we'll just re-display the form to the user
            return render(request, template_name='add_fermentrack_installation.html', context={'form': form})
    else:
        # If there wasn't 'POST' data provided, then just display a blank form for him/her to fill out
        form = forms.FermentrackInstallationForm()
        return render(request, template_name='add_fermentrack_installation.html', context={'form': form})


@csrf_exempt
def process_incoming_data(request):
    if request.body is None:
        logger.error("No data in incoming request body")
        return JsonResponse({'status': 'failed', 'message': "No data in request body"}, safe=False,
                            json_dumps_params={'indent': 4})

    # Regardless of whether the data is properly formed or not, let's write it to a file so that it can be used for
    # debugging purposes.
    with open(os.path.join(settings.BASE_DIR, settings.DATA_ROOT, 'incoming_data_raw.log'), 'w') as logFile:
        pprint.pprint(request.body.decode('utf-8'), logFile)

    # Assuming we received the data, load it to a dict - and then write that dict out using pprint. By writing out
    # both the raw & parsed data, we can determine if there's an issue with the format of the data that was provided
    incoming_data = json.loads(request.body.decode('utf-8'))
    with open(os.path.join(settings.BASE_DIR, "log", 'incoming_data_parsed.log'), 'w') as logFile:
        pprint.pprint(incoming_data, logFile)

    try:
        if 'api_key' in incoming_data:
            fermentrack_obj = UpstreamFermentrackInstallation.objects.get(api_key=incoming_data['api_key'])
        else:
            logger.error(u"Malformed Incoming Data - No API key provided!")
            return JsonResponse({'status': 'failed', 'message': "Malformed JSON - No api_key provided!"},
                                safe=False, json_dumps_params={'indent': 4})
    except ObjectDoesNotExist:
        logger.error(u"Unable to find UpstreamFermentrackInstallation with API key {}".format(incoming_data['api_key']))
        return JsonResponse({'status': 'failed', 'message': "Unable to load device with that API key"}, safe=False,
                            json_dumps_params={'indent': 4})

    # At this point, we've successfully loaded the data that we were sent to a dict & loaded the appropriate
    # UpstreamFermentrackInstallation object. Let's start iterating through the devices we were sent & actually log the
    # data

    # First, parse through the BrewPiDevice objects
    device_no = 0
    for remote_brewpi_info in incoming_data['brewpi_devices']:
        with open(os.path.join(settings.BASE_DIR, "log", 'brewpi_device_{}.log'.format(device_no)), 'w') as logFile:
            pprint.pprint(remote_brewpi_info, logFile)

        # Either load (or create) the appropriate "BrewPiDevice" object
        brewpi_device, created = BrewPiDevice.objects.get_or_create(remote_id=remote_brewpi_info['internal_id'],
                                                                    fermentrack_install=fermentrack_obj)
        # There should be some debate as to which of these fields are required, vs which can be defaulted to a value.
        # For testing, I'm defaulting everything, but in an actual implementation there should be a requirement that
        # at least the minimum set of fields required be provided.
        brewpi_device.name = remote_brewpi_info.get('name', "")
        brewpi_device.latest_temp_format = remote_brewpi_info.get('temp_format', "")
        brewpi_device.latest_fridge_temp = decimal.Decimal(remote_brewpi_info.get('fridge_temp', 0.0))
        brewpi_device.latest_room_temp = decimal.Decimal(remote_brewpi_info.get('room_temp', 0.0))
        brewpi_device.latest_beer_temp = decimal.Decimal(remote_brewpi_info.get('beer_temp', 0.0))
        brewpi_device.latest_control_mode = remote_brewpi_info.get('control_mode', "u")
        # TODO - Properly handle when we aren't provided gravity data (i.e. no sensor is attached)
        # brewpi_device.latest_gravity = decimal.Decimal(remote_brewpi_info.get('gravity', 0.0))

        # Both save the object to the database, as well as the data to the CSV
        brewpi_device.save()
        brewpi_device.save_latest_to_csv()

    # Now that we've handled the BrewPiDevices, let's handle the gravity sensors
    for remote_gravity_info in incoming_data['gravity_sensors']:
        # Either load (or create) the appropriate GravitySensor object
        sensor, created = GravitySensor.objects.get_or_create(remote_id=remote_gravity_info['internal_id'],
                                                              fermentrack_install=fermentrack_obj)

        if created:
            # If we just created the sensor, go ahead and set the sensor type
            sensor.sensor_type = remote_gravity_info['sensor_type']
            sensor.save()

        sensor.name = remote_gravity_info.get('name', "")
        sensor.latest_gravity = decimal.Decimal(remote_gravity_info.get('gravity', 0.0))
        sensor.latest_temp = decimal.Decimal(remote_gravity_info.get('temp', 0.0))
        sensor.latest_temp_format = remote_gravity_info.get('temp_format', "")

        sensor.save()
        sensor.save_latest_to_csv()

    return JsonResponse({'status': 'success', 'message': "Data processed successfully"}, safe=False,
                        json_dumps_params={'indent': 4})
