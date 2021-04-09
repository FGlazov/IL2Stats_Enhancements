from django.urls import reverse


# To be patched into class Player inside stats/models.py of main project.
def get_aircraft_overview_url(self):
    url = '{url}?tour={tour_id}'.format(
        url=reverse('stats:pilot_aircraft_overview', args=[self.profile_id, self.nickname, 'NO_FILTER']),
        tour_id=self.tour_id)
    return url