from django.contrib import admin

from .models import UpstreamFermentrackInstallation, BrewPiDevice


@admin.register(BrewPiDevice)
class brewPiDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'fermentrack_install')


@admin.register(UpstreamFermentrackInstallation)
class upstreamFermentrackInstallationAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_key')
