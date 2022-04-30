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
    url(r'^tankmans/$', views.tankman_rankings, name='tankmans'),
    url(r'^squads/$', views.squad_rankings, name='squads'),
    url(r'^sorties/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_sorties, name='pilot_sorties'),
    url(r'^tankman_sorties/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.tankman_sorties, name='tankman_sorties'),
    url(r'^vlifes/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_vlifes, name='pilot_vlifes'),
    url(r'^awards/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_awards, name='pilot_awards'),
    url(r'^killboard/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot_killboard, name='pilot_killboard'),
    url(r'^tankman_vlifes/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.tankman_vlifes, name='tankman_vlifes'),
    url(r'^tankman_awards/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.tankman_awards, name='tankman_awards'),
    url(r'^tankman_killboard/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.tankman_killboard, name='tankman_killboard'),
    url(r'^missions/$', views.missions_list, name='missions_list'),

    url(r'^squad/(?P<squad_id>\d+)/(?P<squad_tag>\S+)/$', views.squad, name='squad'),
    url(r'^pilots/(?P<squad_id>\d+)/(?P<squad_tag>\S+)/$', views.squad_pilots, name='squad_pilots'),
    url(r'^tankmans/(?P<squad_id>\d+)/(?P<squad_tag>\S+)/$', views.squad_tankmans, name='squad_tankmans'),

    url(r'^pilot/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.pilot, name='pilot'),
    url(r'^sortie/(?P<sortie_id>\d+)/$', views.pilot_sortie, name='pilot_sortie'),
    url(r'^sortie/log/(?P<sortie_id>\d+)/$', views.pilot_sortie_log, name='pilot_sortie_log'),
    url(r'^mission/(?P<mission_id>\d+)/$', views.mission, name='mission'),
    url(r'^vlife/(?P<vlife_id>\d+)/$', views.pilot_vlife, name='pilot_vlife'),
    url(r'^tankman/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.tankman, name='tankman'),
    url(r'^tankman_sortie/(?P<sortie_id>\d+)/$', views.tankman_sortie, name='tankman_sortie'),
    url(r'^tankman_sortie/log/(?P<sortie_id>\d+)/$', views.tankman_sortie_log, name='tankman_sortie_log'),
    url(r'^tankman_vlife/(?P<vlife_id>\d+)/$', views.tankman_vlife, name='tankman_vlife'),

    url(r'^overall/$', views.overall, name='overall'),

    url(r'^online/$', views.online, name='online'),
    url(r'^$', views.main, name='main'),

    # нужно чтобы работали url без имени
    url(r'^pilot/(?P<profile_id>\d+)/$', views.pilot),
    url(r'^sorties/(?P<profile_id>\d+)/$', views.pilot_sorties),
    url(r'^vlifes/(?P<profile_id>\d+)/$', views.pilot_vlifes),
    url(r'^tankman/(?P<profile_id>\d+)/$', views.tankman),
    url(r'^tankman_sorties/(?P<profile_id>\d+)/$', views.tankman_sorties),
    url(r'^tankman_vlifes/(?P<profile_id>\d+)/$', views.tankman_vlifes),

    url(r'^ironman/$', views.ironman_stats, name='ironman'),

    url(r'^gunners/$', views.gunners, name='gunners'),
    url(r'^gunner/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.gunner, name='gunner'),
    url(r'^gunner_sortie/(?P<sortie_id>\d+)/$', views.gunner_sortie, name='gunner_sortie'),
    url(r'^gunner_sortie/log/(?P<sortie_id>\d+)/$', views.gunner_sortie_log, name='gunner_sortie_log'),
    url(r'^gunner_sorties/(?P<profile_id>\d+)/$', views.gunner_sorties, name='gunner_sorties'),
    url(r'^gunner_sorties/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.gunner_sorties, name='gunner_sorties'),
    url(r'^gunner_vlife/(?P<vlife_id>\d+)/$', views.gunner_vlife, name='gunner_vlife'),
    url(r'^gunner_vlifes/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.gunner_vlifes, name='gunner_vlifes'),
    url(r'^gunner_awards/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.gunner_awards, name='gunner_awards'),
    url(r'^gunner_killboard/(?P<profile_id>\d+)/(?P<nickname>\S+)/$', views.gunner_killboard, name='gunner_killboard'),
]
