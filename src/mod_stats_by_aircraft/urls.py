"""
URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.views.generic import RedirectView

from . import views

app_name = 'stats'
urlpatterns = [
    url(r'^pilots/$', views.pilot_rankings, name='pilots'),
    url(r'^squads/$', views.squad_rankings, name='squads'),
    url(r'^sorties/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_sorties, name='pilot_sorties'),
    url(r'^vlifes/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_vlifes, name='pilot_vlifes'),
    url(r'^awards/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_awards, name='pilot_awards'),
    url(r'^killboard/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_killboard, name='pilot_killboard'),

    url(r'^missions/$', views.missions_list, name='missions_list'),

    url(r'^squad/(?P<squad_id>\d+)/(?P<squad_tag>\S+)/$', views.squad, name='squad'),
    url(r'^pilots/(?P<squad_id>\d+)/(?P<squad_tag>\S+)/$', views.squad_pilots, name='squad_pilots'),

    url(r'^pilot/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot, name='pilot'),
    url(r'^sortie/(?P<sortie_id>\d+)/$', views.pilot_sortie, name='pilot_sortie'),
    url(r'^sortie/log/(?P<sortie_id>\d+)/$', views.pilot_sortie_log, name='pilot_sortie_log'),
    url(r'^mission/(?P<mission_id>\d+)/$', views.mission, name='mission'),
    url(r'^vlife/(?P<vlife_id>\d+)/$', views.pilot_vlife, name='pilot_vlife'),

    url(r'^overall/$', views.overall, name='overall'),

    url(r'^all_aircraft/$', views.all_aircraft, name='all_aircraft'),
    url(r'^all_aircraft/(?P<airfilter>\S+)/$', views.all_aircraft, name='all_aircraft'),
    url(r'^aircraft/(?P<aircraft_id>\d+)/(?P<airfilter>\S+)/$', views.aircraft, name='aircraft'),
    url(r'^aircraft_killboard/(?P<aircraft_id>\d+)/(?P<airfilter>\S+)/$', views.aircraft_killboard,
        name='aircraft_killboard'),
    url(r'^aircraft_pilot_rankings/(?P<aircraft_id>\d+)/(?P<airfilter>\S+)/$', views.aircraft_pilot_rankings,
        name='aircraft_pilot_rankings'),

    url(r'^aircraft_overview/(?P<profile_id>\d+)/(?P<nickname>\S+)/(?P<airfilter>\S+)/$', views.pilot_aircraft_overview,
        name='pilot_aircraft_overview'),
    url(r'^pilot_aircraft/(?P<aircraft_id>\d+)/(?P<airfilter>\S+)/(?P<profile_id>\d+)/(?P<nickname>\S+)/$',
        views.pilot_aircraft, name='pilot_aircraft'),
    url(r'^pilot_aircraft_killboard/(?P<aircraft_id>\d+)/(?P<airfilter>\S+)/(?P<profile_id>\d+)/(?P<nickname>\S+)/$',
        views.pilot_aircraft_killboard, name='pilot_aircraft_killboard'),

    url(r'^online/$', views.online, name='online'),
    url(r'^$', views.main, name='main'),

    # нужно чтобы работали url без имени
    url(r'^pilot/(?P<profile_id>\d+)/$', views.pilot),
    url(r'^sorties/(?P<profile_id>\d+)/$', views.pilot_sorties),
    url(r'^vlifes/(?P<profile_id>\d+)/$', views.pilot_vlifes),
]

if hasattr(views, 'ironman_stats'):  # For compatibility with mod_rating_by_type.
    urlpatterns.append(url(r'^ironman/$', views.ironman_stats, name='ironman'))
